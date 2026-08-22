export interface AssistantLabels {
  emptyThread: string;
  messageInput: string;
  messagePlaceholder: string;
  attachFiles: string;
  attachmentMenu: string;
  chooseAttachment: string;
  inputTools: string;
  fileLimit: string;
  takePhoto: string;
  inputMode: string;
  textMode: string;
  voiceMessageMode: string;
  liveDictationMode: string;
  uploadAudio: string;
  recordVoice: string;
  stopVoice: string;
  holdToTalk: string;
  releaseToStop: string;
  startDictation: string;
  stopDictation: string;
  embeddedDictation: string;
  apiDictation: string;
  selectedAttachments: string;
  previewAttachment: string;
  removeAttachment: string;
  moveAttachmentEarlier: string;
  moveAttachmentLater: string;
  retryAttachment: string;
  send: string;
  running: string;
  stop: string;
  regenerate: string;
}

export const DEFAULT_ASSISTANT_LABELS: AssistantLabels = {
  emptyThread: "Ask a question, attach a file, or propose a Host record.",
  messageInput: "Message",
  messagePlaceholder: "Ask the assistant…",
  attachFiles: "Attach files",
  attachmentMenu: "Attachment options",
  chooseAttachment: "Choose image or file",
  inputTools: "Input tools",
  fileLimit: "8 files · 50 MiB total",
  takePhoto: "Camera",
  inputMode: "Input mode",
  textMode: "Text",
  voiceMessageMode: "Voice message",
  liveDictationMode: "Live dictation",
  uploadAudio: "Upload audio",
  recordVoice: "Record voice message",
  stopVoice: "Stop recording",
  holdToTalk: "Hold to talk",
  releaseToStop: "Release to stop",
  startDictation: "Start live dictation",
  stopDictation: "Stop live dictation",
  embeddedDictation: "On-device model",
  apiDictation: "Server API · audio leaves device",
  selectedAttachments: "{count} selected attachments",
  previewAttachment: "Preview {name}",
  removeAttachment: "Remove {name}",
  moveAttachmentEarlier: "Move {name} earlier",
  moveAttachmentLater: "Move {name} later",
  retryAttachment: "Retry {name}",
  send: "Send",
  running: "Running…",
  stop: "Stop",
  regenerate: "Regenerate",
};
