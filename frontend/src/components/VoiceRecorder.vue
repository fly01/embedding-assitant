<script setup lang="ts">
import { ref } from "vue";

const emit = defineEmits<{ recorded: [file: File] }>();
const recording = ref(false);
let recorder: MediaRecorder;
let stream: MediaStream;
let chunks: Blob[] = [];

async function start(): Promise<void> {
  stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  recorder = new MediaRecorder(stream);
  chunks = [];
  recorder.addEventListener("dataavailable", (event) =>
    chunks.push(event.data),
  );
  recorder.start();
  recording.value = true;
}

async function stop(): Promise<void> {
  const stopped = new Promise<void>((resolve) =>
    recorder.addEventListener("stop", () => resolve(), { once: true }),
  );
  recorder.stop();
  await stopped;
  stream.getTracks().forEach((track) => track.stop());
  const blob = new Blob(chunks, { type: recorder.mimeType || "audio/webm" });
  emit(
    "recorded",
    new File([blob], `voice-${Date.now()}.webm`, { type: blob.type }),
  );
  recording.value = false;
}
</script>

<template>
  <button
    v-if="!recording"
    type="button"
    aria-label="Start voice recording"
    @click="start"
  >
    ● Record
  </button>
  <button
    v-else
    type="button"
    class="recording"
    aria-label="Stop voice recording"
    @click="stop"
  >
    ■ Stop
  </button>
</template>
