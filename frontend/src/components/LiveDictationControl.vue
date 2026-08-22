<script setup lang="ts">
import { ref } from "vue";
import type { DictationAdapter } from "../dictation";

const props = defineProps<{ adapter: DictationAdapter }>();
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
      adapter.location === "device"
        ? "On-device"
        : "Server · audio leaves device"
    }}</small>
    <button
      v-if="!listening"
      type="button"
      aria-label="Start live dictation"
      @click="start"
    >
      Dictate
    </button>
    <button
      v-else
      type="button"
      class="recording"
      aria-label="Stop live dictation"
      @click="stop"
    >
      Stop dictation
    </button>
  </span>
</template>
