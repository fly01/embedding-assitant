<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type { AssistantApi } from "../api";
import type {
  ComposerCapabilities,
  ComposerToolbarPlacement,
} from "../composer";
import type { DictationAdapter } from "../dictation";
import type { AssistantLabels } from "../labels";
import type { AssistantStore } from "../store";
import AttachmentTray from "./AttachmentTray.vue";
import LiveDictationControl from "./LiveDictationControl.vue";
import VoiceRecorder from "./VoiceRecorder.vue";

const props = defineProps<{
  api: AssistantApi;
  store: AssistantStore;
  dictationAdapter?: DictationAdapter;
  capabilities: ComposerCapabilities;
  toolbarPlacement: ComposerToolbarPlacement;
  labels: AssistantLabels;
}>();
const text = ref("");
const mode = ref<"text" | "voice_message" | "live_dictation">("text");
const dictationBase = ref("");
const fileInput = ref<HTMLInputElement>();
const cameraInput = ref<HTMLInputElement>();
const voiceInput = ref<HTMLInputElement>();
const liveDictationEnabled = computed(
  () =>
    props.capabilities.liveDictation &&
    props.dictationAdapter?.available === true,
);

watch(liveDictationEnabled, (available) => {
  if (!available && mode.value === "live_dictation") mode.value = "text";
});

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

function selectMode(nextMode: "text" | "voice_message" | "live_dictation") {
  mode.value = nextMode;
  if (nextMode === "live_dictation") beginDictation();
}
</script>

<template>
  <form
    class="composer"
    :data-toolbar-placement="toolbarPlacement"
    @submit.prevent="submit"
    @dragover.prevent
    @drop.prevent="dropFiles"
  >
    <AttachmentTray
      :api="api"
      :attachments="store.state.draftAttachments"
      :labels="labels"
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
    <div v-if="mode !== 'text'" class="composer-mode-panel">
      <template v-if="mode === 'voice_message'">
        <VoiceRecorder
          :start-label="labels.recordVoice"
          :stop-label="labels.stopVoice"
          @recorded="addVoice"
        />
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
        v-else-if="mode === 'live_dictation' && dictationAdapter"
        :adapter="dictationAdapter"
        :start-label="labels.startDictation"
        :stop-label="labels.stopDictation"
        :embedded-label="labels.embeddedDictation"
        :api-label="labels.apiDictation"
        @partial="dictationPartial"
        @final="dictationFinal"
      />
    </div>
    <nav class="composer-tools" :aria-label="labels.inputTools">
      <button
        v-if="capabilities.attachments"
        class="composer-tool"
        type="button"
        :aria-label="labels.attachFiles"
        :title="`${labels.attachFiles} · ${labels.fileLimit}`"
        @click="fileInput?.click()"
      >
        <span aria-hidden="true">＋</span>
      </button>
      <input
        v-if="capabilities.attachments"
        ref="fileInput"
        class="visually-hidden"
        type="file"
        multiple
        @change="selectFiles"
      />
      <button
        v-if="capabilities.camera"
        class="composer-tool"
        type="button"
        :aria-label="labels.takePhoto"
        :title="labels.takePhoto"
        @click="cameraInput?.click()"
      >
        <span aria-hidden="true">▣</span>
      </button>
      <input
        v-if="capabilities.camera"
        ref="cameraInput"
        class="visually-hidden"
        type="file"
        accept="image/*"
        capture="environment"
        @change="selectFiles"
      />
      <button
        class="composer-tool"
        :class="{ active: mode === 'text' }"
        type="button"
        :aria-label="labels.textMode"
        :aria-pressed="mode === 'text'"
        :title="labels.textMode"
        @click="selectMode('text')"
      >
        <span aria-hidden="true">T</span>
      </button>
      <button
        v-if="capabilities.voiceMessage"
        class="composer-tool"
        :class="{ active: mode === 'voice_message' }"
        type="button"
        :aria-label="labels.voiceMessageMode"
        :aria-pressed="mode === 'voice_message'"
        :title="labels.voiceMessageMode"
        @click="selectMode('voice_message')"
      >
        <span aria-hidden="true">●</span>
      </button>
      <button
        v-if="liveDictationEnabled"
        class="composer-tool"
        :class="{ active: mode === 'live_dictation' }"
        type="button"
        :aria-label="labels.liveDictationMode"
        :aria-pressed="mode === 'live_dictation'"
        :title="labels.liveDictationMode"
        @click="selectMode('live_dictation')"
      >
        <span aria-hidden="true">≈</span>
      </button>
      <button
        class="composer-tool send-button"
        type="submit"
        :aria-label="store.state.streaming ? labels.running : labels.send"
        :title="store.state.streaming ? labels.running : labels.send"
        :disabled="store.state.streaming || !text.trim()"
      >
        <span aria-hidden="true">↑</span>
      </button>
    </nav>
  </form>
</template>
