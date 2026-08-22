<script setup lang="ts">
import { onMounted, ref } from "vue";

const props = defineProps<{
  urls: string[];
  names: string[];
  startIndex: number;
}>();
const emit = defineEmits<{ close: [] }>();
const index = ref(props.startIndex);
const closeButton = ref<HTMLButtonElement>();

function move(offset: number): void {
  index.value = (index.value + offset + props.urls.length) % props.urls.length;
}

function onKey(event: KeyboardEvent): void {
  if (event.key === "Escape") emit("close");
  if (event.key === "ArrowLeft") move(-1);
  if (event.key === "ArrowRight") move(1);
}

onMounted(() => closeButton.value?.focus());
</script>

<template>
  <div
    class="lightbox"
    role="dialog"
    aria-modal="true"
    aria-label="Attachment preview"
    @keydown="onKey"
  >
    <button
      ref="closeButton"
      class="lightbox-close"
      aria-label="Close preview"
      @click="emit('close')"
    >
      ×
    </button>
    <button
      v-if="urls.length > 1"
      class="lightbox-prev"
      aria-label="Previous image"
      @click="move(-1)"
    >
      ‹
    </button>
    <figure>
      <img :src="urls[index]" :alt="names[index]" />
      <figcaption>
        {{ index + 1 }} / {{ urls.length }} · {{ names[index] }}
      </figcaption>
    </figure>
    <button
      v-if="urls.length > 1"
      class="lightbox-next"
      aria-label="Next image"
      @click="move(1)"
    >
      ›
    </button>
  </div>
</template>
