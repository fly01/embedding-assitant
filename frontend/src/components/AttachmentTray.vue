<script setup lang="ts">
import type { Attachment } from "../types";

defineProps<{ attachments: Attachment[] }>();
const emit = defineEmits<{
  remove: [id: string];
  move: [index: number, direction: -1 | 1];
  retry: [id: string];
}>();
</script>

<template>
  <ol
    v-if="attachments.length"
    class="attachment-tray"
    :aria-label="`${attachments.length} selected attachments`"
  >
    <li v-for="(attachment, index) in attachments" :key="attachment.id">
      <span class="tray-kind">{{
        attachment.kind.slice(0, 1).toUpperCase()
      }}</span>
      <span class="tray-copy">
        <strong>{{ attachment.name }}</strong>
        <small>{{ attachment.processing_status }}</small>
      </span>
      <button
        :disabled="index === 0"
        :aria-label="`Move ${attachment.name} earlier`"
        @click="emit('move', index, -1)"
      >
        ←
      </button>
      <button
        :disabled="index === attachments.length - 1"
        :aria-label="`Move ${attachment.name} later`"
        @click="emit('move', index, 1)"
      >
        →
      </button>
      <button
        v-if="attachment.processing_status === 'failed'"
        @click="emit('retry', attachment.id)"
      >
        Retry
      </button>
      <button
        :aria-label="`Remove ${attachment.name}`"
        @click="emit('remove', attachment.id)"
      >
        ×
      </button>
    </li>
  </ol>
</template>
