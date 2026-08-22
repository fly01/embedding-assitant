<script setup lang="ts">
import { ref } from "vue";
import type { DictationAdapter } from "../dictation";

const props = defineProps<{
  adapter: DictationAdapter;
  startLabel: string;
  stopLabel: string;
  embeddedLabel: string;
  apiLabel: string;
}>();
const emit = defineEmits<{ partial: [text: string]; final: [text: string] }>();
const listening = ref(false);

async function start(): Promise<void> {
  listening.value = true;
  await props.adapter.start((text) => emit("partial", text));
}

async function stop(): Promise<void> {
  emit("final", await props.adapter.stop());
  listening.value = false;
}
</script>

<template>
  <span class="dictation-control">
    <small>{{
      adapter.provider === "embedded_model" ? embeddedLabel : apiLabel
    }}</small>
    <button
      v-if="!listening"
      type="button"
      :aria-label="startLabel"
      @click="start"
    >
      {{ startLabel }}
    </button>
    <button
      v-else
      type="button"
      class="recording"
      :aria-label="stopLabel"
      @click="stop"
    >
      {{ stopLabel }}
    </button>
  </span>
</template>
