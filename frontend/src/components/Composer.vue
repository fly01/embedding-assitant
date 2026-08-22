<script setup lang="ts">
import { ArrowUp, Camera, Image, Plus } from "@lucide/vue";
import { computed, ref } from "vue";
import type { AssistantApi } from "../api";
import type {
  ComposerCapabilities,
  ComposerToolbarPlacement,
  ComposerVoiceToolMode,
} from "../composer";
import type { DictationAdapter } from "../dictation";
import type { AssistantLabels } from "../labels";
import type { AssistantStore } from "../store";
import AttachmentTray from "./AttachmentTray.vue";
import HoldToTalkButton from "./HoldToTalkButton.vue";

const props = defineProps<{
  api: AssistantApi;
  store: AssistantStore;
  dictationAdapter?: DictationAdapter;
  capabilities: ComposerCapabilities;
  toolbarPlacement: ComposerToolbarPlacement;
  voiceToolMode: ComposerVoiceToolMode;
  labels: AssistantLabels;
}>();
const text = ref("");
const dictationBase = ref("");
const fileInput = ref<HTMLInputElement>();
const cameraInput = ref<HTMLInputElement>();
const attachmentMenuOpen = ref(false);
const liveDictationEnabled = computed(
  () =>
    props.capabilities.liveDictation &&
    props.dictationAdapter?.available === true,
);
const voiceToolMode = computed<"voice_message" | "live_dictation" | null>(
  () => {
    if (props.voiceToolMode === "live_dictation")
      return liveDictationEnabled.value ? "live_dictation" : null;
    if (props.voiceToolMode === "voice_message")
      return props.capabilities.voiceMessage ? "voice_message" : null;
    if (liveDictationEnabled.value) return "live_dictation";
    if (props.capabilities.voiceMessage) return "voice_message";
    return null;
  },
);

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
  attachmentMenuOpen.value = false;
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
}

function dictationPartial(partial: string): void {
  text.value = `${dictationBase.value}${partial}`;
}

function dictationFinal(finalText: string): void {
  text.value = `${dictationBase.value}${finalText}`;
}

function beginDictation(): void {
  dictationBase.value = text.value;
}

function voiceError(message: string): void {
  props.store.state.error = message;
}

function openAttachmentPicker(kind: "files" | "camera"): void {
  attachmentMenuOpen.value = false;
  if (kind === "files") fileInput.value?.click();
  else cameraInput.value?.click();
}
</script>

<template>
  <form
    class="composer"
    :data-toolbar-placement="toolbarPlacement"
    @submit.prevent="submit"
    @dragover.prevent
    @drop.prevent="dropFiles"
    @keydown.esc="attachmentMenuOpen = false"
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
    <div
      v-if="attachmentMenuOpen"
      id="composer-attachment-menu"
      class="attachment-menu"
      role="menu"
      :aria-label="labels.attachmentMenu"
    >
      <button
        v-if="capabilities.attachments"
        type="button"
        role="menuitem"
        @click="openAttachmentPicker('files')"
      >
        <Image :size="18" aria-hidden="true" />
        <span>{{ labels.chooseAttachment }}</span>
      </button>
      <button
        v-if="capabilities.camera"
        type="button"
        role="menuitem"
        @click="openAttachmentPicker('camera')"
      >
        <Camera :size="18" aria-hidden="true" />
        <span>{{ labels.takePhoto }}</span>
      </button>
    </div>
    <nav class="composer-tools" :aria-label="labels.inputTools">
      <button
        v-if="capabilities.attachments || capabilities.camera"
        class="composer-tool"
        type="button"
        :aria-label="labels.attachFiles"
        :title="labels.attachFiles"
        :aria-expanded="attachmentMenuOpen"
        aria-controls="composer-attachment-menu"
        @click="attachmentMenuOpen = !attachmentMenuOpen"
      >
        <Plus :size="21" :stroke-width="2.25" aria-hidden="true" />
      </button>
      <input
        v-if="capabilities.attachments"
        ref="fileInput"
        class="visually-hidden"
        type="file"
        multiple
        @change="selectFiles"
      />
      <input
        v-if="capabilities.camera"
        ref="cameraInput"
        class="visually-hidden"
        type="file"
        accept="image/*"
        capture="environment"
        @change="selectFiles"
      />
      <HoldToTalkButton
        v-if="voiceToolMode"
        :mode="voiceToolMode"
        :adapter="dictationAdapter"
        :labels="labels"
        @start="beginDictation"
        @recorded="addVoice"
        @partial="dictationPartial"
        @final="dictationFinal"
        @error="voiceError"
      />
      <button
        class="composer-tool send-button"
        type="submit"
        :aria-label="store.state.streaming ? labels.running : labels.send"
        :title="store.state.streaming ? labels.running : labels.send"
        :disabled="store.state.streaming || !text.trim()"
      >
        <ArrowUp :size="21" :stroke-width="2.5" aria-hidden="true" />
      </button>
    </nav>
  </form>
</template>
