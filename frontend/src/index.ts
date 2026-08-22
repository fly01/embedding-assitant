export { AssistantApi, ApiError } from "./api";
export {
  DEFAULT_COMPOSER_CAPABILITIES,
  type ComposerCapabilities,
  type ComposerToolbarPlacement,
  type ComposerVoiceToolMode,
} from "./composer";
export { DemoDictationAdapter, type DictationAdapter } from "./dictation";
export { DEFAULT_ASSISTANT_LABELS, type AssistantLabels } from "./labels";
export type { AssistantShellLayout } from "./shell";
export { createAssistantStore, type AssistantStore } from "./store";
export * from "./types";

export { default as ActionCard } from "./components/ActionCard.vue";
export { default as AssistantShell } from "./components/AssistantShell.vue";
export { default as AttachmentGroup } from "./components/AttachmentGroup.vue";
export { default as AttachmentLightbox } from "./components/AttachmentLightbox.vue";
export { default as AttachmentTray } from "./components/AttachmentTray.vue";
export { default as Composer } from "./components/Composer.vue";
export { default as ConversationThread } from "./components/ConversationThread.vue";
export { default as HoldToTalkButton } from "./components/HoldToTalkButton.vue";
export { default as LiveDictationControl } from "./components/LiveDictationControl.vue";
export { default as PrivacyCenter } from "./components/PrivacyCenter.vue";
export { default as PrivacyJobStatus } from "./components/PrivacyJobStatus.vue";
export { default as ThinkingDisclosure } from "./components/ThinkingDisclosure.vue";
export { default as ToolActivity } from "./components/ToolActivity.vue";
export { default as VoiceRecorder } from "./components/VoiceRecorder.vue";

import "./styles.css";
