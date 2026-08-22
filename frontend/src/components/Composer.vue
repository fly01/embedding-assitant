<script setup lang="ts">
import { ref } from "vue";
import type { DictationAdapter } from "../dictation";
import type { AssistantLabels } from "../labels";
import type { AssistantStore } from "../store";
import AttachmentTray from "./AttachmentTray.vue";
import LiveDictationControl from "./LiveDictationControl.vue";
import VoiceRecorder from "./VoiceRecorder.vue";

const props = defineProps<{
  store: AssistantStore;
  dictationAdapter: DictationAdapter;
  labels: AssistantLabels;
}>();
const text = ref("");
const mode = ref<"text" | "voice_message" | "live_dictation">("text");
const dictationBase = ref("");
const fileInput = ref<HTMLInputElement>();
const cameraInput = ref<HTMLInputElement>();
const voiceInput = ref<HTMLInputElement>();

async function submit(): Promise<void> {
  const value = text.value.trim();
  if (!value || props.store.state.streaming) return;
  text.value = "";
  await props.store.send(value);
}

async function selectFiles(event: Event): Promise<void> {
  const input = event.currentTarget as HTMLInputElement;
  if (input.files) await props.store.addAttachments(input.files);
  input.value = "";
}

async function dropFiles(event: DragEvent): Promise<void> {
  if (event.dataTransfer?.files.length)
    await props.store.addAttachments(event.dataTransfer.files);
}

async function pasteFiles(event: ClipboardEvent): Promise<void> {
  const files = Array.from(event.clipboardData?.files ?? []);
  if (files.length) await props.store.addAttachments(files);
}

async function addVoice(file: File): Promise<void> {
  text.value = await props.store.addVoiceMessage(file);
  mode.value = "text";
}

async function selectVoice(event: Event): Promise<void> {
  const input = event.currentTarget as HTMLInputElement;
  if (input.files?.[0]) await addVoice(input.files[0]);
  input.value = "";
}

function dictationPartial(partial: string): void {
  text.value = `${dictationBase.value}${partial}`;
}

function dictationFinal(finalText: string): void {
  text.value = `${dictationBase.value}${finalText}`;
  mode.value = "text";
}

function beginDictation(): void {
  dictationBase.value = text.value;
}
</script>

<template>
  <form
    class="composer"
    @submit.prevent="submit"
    @dragover.prevent
    @drop.prevent="dropFiles"
  >
    <AttachmentTray
      :attachments="store.state.draftAttachments"
      @remove="store.removeAttachment"
      @move="store.moveAttachment"
      @retry="store.retryAttachment"
    />
    <textarea
      v-model="text"
      rows="2"
      :aria-label="labels.messageInput"
      :placeholder="labels.messagePlaceholder"
      @keydown.enter.exact.prevent="submit"
      @paste="pasteFiles"
    />
    <div class="composer-actions">
      <button
        type="button"
        :aria-label="labels.attachFiles"
        @click="fileInput?.click()"
      >
        ＋
      </button>
      <small>{{ labels.fileLimit }}</small>
      <input
        ref="fileInput"
        class="visually-hidden"
        type="file"
        multiple
        @change="selectFiles"
      />
      <button
        type="button"
        :aria-label="labels.takePhoto"
        @click="cameraInput?.click()"
      >
        Camera
      </button>
      <input
        ref="cameraInput"
        class="visually-hidden"
        type="file"
        accept="image/*"
        capture="environment"
        @change="selectFiles"
      />
      <select
        v-model="mode"
        :aria-label="labels.inputMode"
        @change="mode === 'live_dictation' && beginDictation()"
      >
        <option value="text">{{ labels.textMode }}</option>
        <option value="voice_message">{{ labels.voiceMessageMode }}</option>
        <option value="live_dictation">{{ labels.liveDictationMode }}</option>
      </select>
      <template v-if="mode === 'voice_message'">
        <VoiceRecorder @recorded="addVoice" />
        <button type="button" @click="voiceInput?.click()">
          {{ labels.uploadAudio }}
        </button>
        <input
          ref="voiceInput"
          class="visually-hidden"
          type="file"
          accept="audio/*"
          @change="selectVoice"
        />
      </template>
      <LiveDictationControl
        v-if="mode === 'live_dictation'"
        :adapter="dictationAdapter"
        @partial="dictationPartial"
        @final="dictationFinal"
      />
      <button
        class="send-button"
        type="submit"
        :disabled="store.state.streaming || !text.trim()"
      >
        {{ store.state.streaming ? labels.running : labels.send }}
      </button>
    </div>
  </form>
</template>
