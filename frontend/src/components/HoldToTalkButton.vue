<script setup lang="ts">
import { Mic } from "@lucide/vue";
import { ref } from "vue";
import type { DictationAdapter } from "../dictation";
import type { AssistantLabels } from "../labels";

const props = defineProps<{
  mode: "voice_message" | "live_dictation";
  adapter?: DictationAdapter;
  labels: AssistantLabels;
}>();
const emit = defineEmits<{
  start: [];
  recorded: [file: File];
  partial: [text: string];
  final: [text: string];
  error: [message: string];
}>();
const active = ref(false);
const busy = ref(false);
let recorder: MediaRecorder | null = null;
let stream: MediaStream | null = null;
let chunks: Blob[] = [];
let startPromise: Promise<void> | null = null;

async function startCapture(): Promise<void> {
  try {
    if (props.mode === "live_dictation") {
      if (!props.adapter?.available)
        throw new Error("Live dictation adapter is unavailable");
      await props.adapter.start((text) => emit("partial", text));
      active.value = true;
      return;
    }

    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    recorder = new MediaRecorder(stream);
    chunks = [];
    recorder.addEventListener("dataavailable", (event) =>
      chunks.push(event.data),
    );
    recorder.start();
    active.value = true;
  } catch (error) {
    active.value = false;
    emit("error", error instanceof Error ? error.message : String(error));
  }
}

async function stopCapture(): Promise<void> {
  if (!startPromise) return;
  busy.value = true;
  await startPromise;
  startPromise = null;
  try {
    if (!active.value) return;
    if (props.mode === "live_dictation") {
      emit("final", await props.adapter!.stop());
      return;
    }

    const stopped = new Promise<void>((resolve) =>
      recorder!.addEventListener("stop", () => resolve(), { once: true }),
    );
    recorder!.stop();
    await stopped;
    const blob = new Blob(chunks, {
      type: recorder!.mimeType || "audio/webm",
    });
    emit(
      "recorded",
      new File([blob], "voice-" + Date.now() + ".webm", { type: blob.type }),
    );
  } catch (error) {
    emit("error", error instanceof Error ? error.message : String(error));
  } finally {
    stream?.getTracks().forEach((track) => track.stop());
    stream = null;
    recorder = null;
    chunks = [];
    active.value = false;
    busy.value = false;
  }
}

function begin(event: PointerEvent | KeyboardEvent): void {
  if (startPromise || busy.value) return;
  event.preventDefault();
  if (event instanceof PointerEvent)
    (event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
  emit("start");
  startPromise = startCapture();
}

function end(event: PointerEvent | KeyboardEvent): void {
  event.preventDefault();
  void stopCapture();
}
</script>

<template>
  <button
    class="composer-tool hold-to-talk"
    :class="{ active, busy }"
    type="button"
    :aria-label="active ? labels.releaseToStop : labels.holdToTalk"
    :title="active ? labels.releaseToStop : labels.holdToTalk"
    :disabled="busy"
    @pointerdown="begin"
    @pointerup="end"
    @pointercancel="end"
    @keydown.space="begin"
    @keyup.space="end"
    @keydown.enter="begin"
    @keyup.enter="end"
    @contextmenu.prevent
  >
    <Mic :size="20" :stroke-width="2.25" aria-hidden="true" />
  </button>
</template>
