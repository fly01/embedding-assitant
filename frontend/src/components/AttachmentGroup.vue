<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import { ApiError, type AssistantApi } from "../api";
import type { Attachment } from "../types";
import AttachmentLightbox from "./AttachmentLightbox.vue";

const props = defineProps<{ api: AssistantApi; attachmentIds: string[] }>();
const attachments = ref<Attachment[]>([]);
const urls = ref<Record<string, string>>({});
const unavailable = ref<string[]>([]);
const lightboxIndex = ref<number | null>(null);
let lightboxTrigger: HTMLElement | null = null;

onMounted(async () => {
  for (const id of props.attachmentIds) {
    try {
      attachments.value.push(await props.api.getAttachment(id));
    } catch (error) {
      if (error instanceof ApiError && error.status === 404)
        unavailable.value.push(id);
      else throw error;
    }
  }
  for (const attachment of attachments.value) {
    urls.value[attachment.id] = await props.api.attachmentObjectUrl(
      attachment.id,
      "thumbnail",
    );
  }
});

onBeforeUnmount(() =>
  Object.values(urls.value).forEach((url) => URL.revokeObjectURL(url)),
);

function imageIndex(attachment: Attachment): number {
  return attachments.value
    .filter((item) => item.kind === "image")
    .findIndex((item) => item.id === attachment.id);
}

function openLightbox(index: number, event: MouseEvent): void {
  lightboxTrigger = event.currentTarget as HTMLElement;
  lightboxIndex.value = index;
}

function closeLightbox(): void {
  lightboxIndex.value = null;
  lightboxTrigger?.focus();
}
</script>

<template>
  <div class="attachment-group" :class="`count-${attachments.length}`">
    <div
      v-for="id in unavailable"
      :key="id"
      class="file-card unavailable"
      role="status"
    >
      <span class="file-icon">!</span>
      <span
        ><strong>Attachment unavailable</strong><small>{{ id }}</small></span
      >
    </div>
    <template v-for="attachment in attachments" :key="attachment.id">
      <button
        v-if="attachment.kind === 'image'"
        class="attachment-image"
        :aria-label="`Open ${attachment.name}`"
        @click="openLightbox(imageIndex(attachment), $event)"
      >
        <img :src="urls[attachment.id]" :alt="attachment.name" />
      </button>
      <audio
        v-else-if="attachment.kind === 'audio'"
        controls
        :src="urls[attachment.id]"
      >
        {{ attachment.name }}
      </audio>
      <a
        v-else
        class="file-card"
        :href="urls[attachment.id]"
        :download="attachment.name"
        :aria-label="`Download ${attachment.name}`"
      >
        <span class="file-icon">▤</span>
        <span>
          <strong>{{ attachment.name }}</strong>
          <small
            >{{ attachment.kind }} ·
            {{ Math.ceil(attachment.size_bytes / 1024) }} KB ·
            {{ attachment.processing_status }}</small
          >
        </span>
      </a>
    </template>
  </div>
  <AttachmentLightbox
    v-if="lightboxIndex !== null"
    :urls="
      attachments
        .filter((item) => item.kind === 'image')
        .map((item) => urls[item.id])
    "
    :names="
      attachments
        .filter((item) => item.kind === 'image')
        .map((item) => item.name)
    "
    :start-index="lightboxIndex"
    @close="closeLightbox"
  />
</template>
