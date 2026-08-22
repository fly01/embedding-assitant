export type ComposerToolbarPlacement = "below" | "side";
export type ComposerVoiceToolMode = "auto" | "voice_message" | "live_dictation";

export interface ComposerCapabilities {
  attachments: boolean;
  camera: boolean;
  voiceMessage: boolean;
  liveDictation: boolean;
}

export const DEFAULT_COMPOSER_CAPABILITIES: ComposerCapabilities = {
  attachments: true,
  camera: true,
  voiceMessage: true,
  liveDictation: true,
};
