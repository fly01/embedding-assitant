<script setup lang="ts">
import { ChevronLeft, ChevronRight, File, RotateCw, X } from "@lucide/vue";
import { computed, onBeforeUnmount, ref, watch } from "vue";
import type { AssistantApi } from "../api";
import type { AssistantLabels } from "../labels";
import type { Attachment } from "../types";
import AttachmentLightbox from "./AttachmentLightbox.vue";

const props = defineProps<{
  api: AssistantApi;
  attachments: Attachment[];
  labels: AssistantLabels;
}>();
const emit = defineEmits<{
  remove: [id: string];
  move: [index: number, direction: -1 | 1];
  retry: [id: string];
}>();
const thumbnailUrls = ref<Record<string, string>>({});
const previewUrls = ref<Record<string, string>>({});
const lightboxIndex = ref<number | null>(null);
let lightboxTrigger: HTMLElement | null = null;
const imageAttachments = computed(() =>
  props.attachments.filter((attachment) => attachment.kind === "image"),
);

watch(
  () => props.attachments.map((attachment) => attachment.id),
  async (ids) => {
    for (const [id, url] of Object.entries(thumbnailUrls.value)) {
      if (!ids.includes(id)) {
        URL.revokeObjectURL(url);
        delete thumbnailUrls.value[id];
      }
    }
    for (const attachment of props.attachments) {
      if (attachment.kind === "image" && !thumbnailUrls.value[attachment.id]) {
        thumbnailUrls.value[attachment.id] =
          await props.api.attachmentObjectUrl(attachment.id, "thumbnail");
      }
    }
  },
  { immediate: true },
);

onBeforeUnmount(() => {
  for (const url of [
    ...Object.values(thumbnailUrls.value),
    ...Object.values(previewUrls.value),
  ])
    URL.revokeObjectURL(url);
});

function label(template: string, values: Record<string, string | number>) {
  return Object.entries(values).reduce(
    (text, [key, value]) => text.replace("{" + key + "}", String(value)),
    template,
  );
}

function status(attachment: Attachment): string {
  return attachment.processing_status.replaceAll("_", " ");
}

async function previewUrl(attachment: Attachment): Promise<string> {
  if (!previewUrls.value[attachment.id])
    previewUrls.value[attachment.id] = await props.api.attachmentObjectUrl(
      attachment.id,
      "preview",
    );
  return previewUrls.value[attachment.id];
}

async function openAttachment(
  attachment: Attachment,
  event: MouseEvent,
): Promise<void> {
  if (attachment.kind === "image") {
    lightboxTrigger = event.currentTarget as HTMLElement;
    for (const image of imageAttachments.value) await previewUrl(image);
    lightboxIndex.value = imageAttachments.value.findIndex(
      (image) => image.id === attachment.id,
    );
    return;
  }
  const preview = window.open("", "_blank");
  if (!preview) throw new Error("The browser blocked the attachment preview");
  preview.opener = null;
  preview.location.href = await previewUrl(attachment);
}

function closeLightbox(): void {
  lightboxIndex.value = null;
  lightboxTrigger?.focus();
}
</script>

<template>
  <ol
    v-if="attachments.length"
    class="attachment-tray"
    :aria-label="
      label(labels.selectedAttachments, { count: attachments.length })
    "
  >
    <li
      v-for="(attachment, index) in attachments"
      :key="attachment.id"
      class="tray-item"
      :class="'tray-' + attachment.kind"
    >
      <button
        type="button"
        class="tray-preview"
        :aria-label="label(labels.previewAttachment, { name: attachment.name })"
        @click="openAttachment(attachment, $event)"
      >
        <img
          v-if="attachment.kind === 'image' && thumbnailUrls[attachment.id]"
          :src="thumbnailUrls[attachment.id]"
          :alt="attachment.name"
        />
        <span v-else class="tray-kind" aria-hidden="true">
          <File :size="18" />
        </span>
        <span class="tray-copy">
          <strong>{{ attachment.name }}</strong>
          <small v-if="attachment.kind !== 'image'"
            >{{ Math.max(1, Math.ceil(attachment.size_bytes / 1024)) }} KB ·
            {{ status(attachment) }}</small
          >
        </span>
      </button>
      <span
        class="tray-status"
        :data-status="attachment.processing_status"
        :title="status(attachment)"
        aria-hidden="true"
      ></span>
      <div class="tray-controls">
        <button
          type="button"
          :disabled="index === 0"
          :aria-label="
            label(labels.moveAttachmentEarlier, { name: attachment.name })
          "
          @click="emit('move', index, -1)"
        >
          <ChevronLeft :size="16" aria-hidden="true" />
        </button>
        <button
          type="button"
          :disabled="index === attachments.length - 1"
          :aria-label="
            label(labels.moveAttachmentLater, { name: attachment.name })
          "
          @click="emit('move', index, 1)"
        >
          <ChevronRight :size="16" aria-hidden="true" />
        </button>
        <button
          v-if="attachment.processing_status === 'failed'"
          type="button"
          :aria-label="label(labels.retryAttachment, { name: attachment.name })"
          @click="emit('retry', attachment.id)"
        >
          <RotateCw :size="14" aria-hidden="true" />
        </button>
        <button
          type="button"
          :aria-label="
            label(labels.removeAttachment, { name: attachment.name })
          "
          @click="emit('remove', attachment.id)"
        >
          <X :size="15" aria-hidden="true" />
        </button>
      </div>
    </li>
  </ol>
  <AttachmentLightbox
    v-if="lightboxIndex !== null"
    :urls="imageAttachments.map((attachment) => previewUrls[attachment.id])"
    :names="imageAttachments.map((attachment) => attachment.name)"
    :start-index="lightboxIndex"
    @close="closeLightbox"
  />
</template>
