export interface DictationAdapter {
  readonly available: boolean;
  readonly provider: "embedded_model" | "api";
  readonly location: "device" | "server";
  readonly retention: "ephemeral";
  start(onPartial: (text: string) => void): Promise<void>;
  stop(): Promise<string>;
}

export class DemoDictationAdapter implements DictationAdapter {
  readonly available = true;
  readonly provider = "embedded_model";
  readonly location = "device";
  readonly retention = "ephemeral";
  private readonly text = "Plan a calm weekend trip";

  async start(onPartial: (text: string) => void): Promise<void> {
    onPartial(this.text.slice(0, 11));
    await new Promise((resolve) => window.setTimeout(resolve, 80));
    onPartial(this.text);
  }

  async stop(): Promise<string> {
    return this.text;
  }
}
