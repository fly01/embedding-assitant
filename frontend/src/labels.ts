export interface AssistantLabels {
  emptyThread: string;
  messageInput: string;
  messagePlaceholder: string;
  attachFiles: string;
  fileLimit: string;
  takePhoto: string;
  inputMode: string;
  textMode: string;
  voiceMessageMode: string;
  liveDictationMode: string;
  uploadAudio: string;
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
  fileLimit: "8 files · 50 MiB total",
  takePhoto: "Camera",
  inputMode: "Input mode",
  textMode: "Text",
  voiceMessageMode: "Voice message",
  liveDictationMode: "Live dictation",
  uploadAudio: "Upload audio",
  send: "Send",
  running: "Running…",
  stop: "Stop",
  regenerate: "Regenerate",
};
