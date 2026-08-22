<script setup lang="ts">
import { nextTick, onMounted, ref, watch, type Component } from "vue";
import type { AssistantApi } from "../api";
import type { AssistantStore } from "../store";
import { formatMessageTime, messageTime, shouldShowTime } from "../time";
import ActionCard from "./ActionCard.vue";
import AttachmentGroup from "./AttachmentGroup.vue";
import MarkdownContent from "./MarkdownContent.vue";
import MessageTimeDivider from "./MessageTimeDivider.vue";

const props = withDefaults(
  defineProps<{
    api: AssistantApi;
    store: AssistantStore;
    renderers?: Record<string, Component>;
  }>(),
  { renderers: () => ({}) },
);
const viewport = ref<HTMLElement>();
let followBottom = true;

function attachmentIds(message: {
  content: Array<{ type: string; attachment_id?: string | null }>;
}): string[] {
  return message.content
    .filter((part) => part.type === "attachment" && part.attachment_id)
    .map((part) => part.attachment_id as string);
}

function onScroll(): void {
  if (!viewport.value) return;
  followBottom =
    viewport.value.scrollHeight -
      viewport.value.scrollTop -
      viewport.value.clientHeight <
    48;
}

async function openAttachment(id: string): Promise<void> {
  const preview = window.open("", "_blank");
  if (!preview)
    throw new Error("The browser blocked the attachment preview window");
  preview.opener = null;
  preview.location.href = await props.api.attachmentObjectUrl(id, "original");
}

watch(
  () => props.store.state.messages.map((message) => message.content),
  async () => {
    if (!followBottom) return;
    await nextTick();
    viewport.value?.scrollTo({ top: viewport.value.scrollHeight });
  },
  { deep: true },
);

onMounted(onScroll);
</script>

<template>
  <section
    ref="viewport"
    class="conversation-thread"
    aria-label="Conversation"
    @scroll="onScroll"
  >
    <template
      v-for="(message, index) in store.state.messages"
      :key="message.id"
    >
      <MessageTimeDivider
        v-if="shouldShowTime(store.state.messages, index)"
        :label="formatMessageTime(message)"
      />
      <article
        class="message"
        :class="`message-${message.role}`"
        :aria-label="`${message.role} message sent ${messageTime(message).toLocaleString()}`"
      >
        <AttachmentGroup
          v-if="attachmentIds(message).length"
          :api="api"
          :attachment-ids="attachmentIds(message)"
        />
        <template
          v-for="part in [...message.content].sort((a, b) => a.order - b.order)"
          :key="`${message.id}-${part.order}`"
        >
          <MarkdownContent
            v-if="['text', 'markdown'].includes(part.type) && part.text"
            :text="part.text"
          />
          <ActionCard
            v-else-if="
              part.type === 'action' &&
              store.activeActions.value.get(String(part.data.action_id))
            "
            :action="
              store.activeActions.value.get(String(part.data.action_id))!
            "
            @confirm="store.confirmAction"
            @cancel="store.cancelAction"
            @edit="store.editAction"
            @undo="store.undoAction"
            @open-attachment="openAttachment"
          />
          <component
            v-else-if="renderers[part.type]"
            :is="renderers[part.type]"
            :part="part"
          />
          <details v-else-if="part.type !== 'attachment'" class="generic-part">
            <summary>{{ part.type }}</summary>
            <pre>{{ JSON.stringify(part.data, null, 2) }}</pre>
          </details>
        </template>
      </article>
    </template>
    <p v-if="!store.state.messages.length" class="empty-thread">
      Ask a question, attach a file, or propose a Host record.
    </p>
  </section>
</template>
