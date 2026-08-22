import type {
  AssistantEvent,
  Attachment,
  ContextProfile,
  Conversation,
  DisclosureLevel,
  ExecutionMode,
  HostRecord,
  MemoryRecord,
  Message,
  PendingAction,
  PrivacyJob,
  PrivacyResource,
  Transcript,
} from "./types";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code: string,
  ) {
    super(message);
  }
}

export class AssistantApi {
  constructor(
    readonly baseUrl: string,
    readonly actorId: string,
    readonly scopeKey: string,
  ) {}

  async listConversations(): Promise<Conversation[]> {
    return this.request("/v1/assistant/conversations");
  }

  async createConversation(title: string): Promise<Conversation> {
    return this.request("/v1/assistant/conversations", {
      method: "POST",
      body: JSON.stringify({ title }),
    });
  }

  async updateConversation(
    id: string,
    patch: { title?: string; status?: "active" | "archived" },
  ): Promise<Conversation> {
    return this.request(`/v1/assistant/conversations/${id}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    });
  }

  async listMessages(conversationId: string): Promise<Message[]> {
    return this.request(
      `/v1/assistant/conversations/${conversationId}/messages?limit=100`,
    );
  }

  async startRun(
    conversationId: string,
    input: {
      text: string;
      attachment_ids: string[];
      context_profile: ContextProfile;
      execution_mode: ExecutionMode;
      disclosure_level: DisclosureLevel;
    },
  ): Promise<{ run_id: string; input_message_id: string; latest_seq: number }> {
    return this.request(`/v1/assistant/conversations/${conversationId}/runs`, {
      method: "POST",
      body: JSON.stringify(input),
    });
  }

  async streamRun(
    runId: string,
    onEvent: (event: AssistantEvent) => void,
  ): Promise<void> {
    const response = await fetch(
      `${this.baseUrl}/v1/assistant/runs/${runId}/events?after_seq=0`,
      {
        headers: this.authHeaders(),
      },
    );
    if (!response.ok || !response.body) {
      throw await this.error(response);
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const frames = buffer.split("\n\n");
      buffer = frames.pop() ?? "";
      for (const frame of frames) {
        const data = frame
          .split("\n")
          .find((line) => line.startsWith("data: "));
        if (data) onEvent(JSON.parse(data.slice(6)) as AssistantEvent);
      }
    }
  }

  async cancelRun(runId: string): Promise<void> {
    await this.request(`/v1/assistant/runs/${runId}/cancel`, {
      method: "POST",
    });
  }

  async uploadAttachment(
    conversationId: string,
    file: File,
    source = "picker",
  ): Promise<Attachment> {
    const body = new FormData();
    body.append("file", file);
    body.append("conversation_id", conversationId);
    body.append("source", source);
    return this.request(
      "/v1/assistant/attachments",
      { method: "POST", body },
      false,
    );
  }

  async getAttachment(attachmentId: string): Promise<Attachment> {
    return this.request(`/v1/assistant/attachments/${attachmentId}`);
  }

  async attachmentObjectUrl(
    attachmentId: string,
    variant: "thumbnail" | "preview" | "original",
  ): Promise<string> {
    const response = await fetch(
      `${this.baseUrl}/v1/assistant/attachments/${attachmentId}/${variant}`,
      {
        headers: this.authHeaders(),
      },
    );
    if (!response.ok) throw await this.error(response);
    return URL.createObjectURL(await response.blob());
  }

  async transcribe(attachmentId: string): Promise<Transcript> {
    return this.request(
      `/v1/assistant/attachments/${attachmentId}/transcriptions`,
      { method: "POST" },
    );
  }

  async retryAttachment(attachmentId: string): Promise<Attachment> {
    return this.request(
      `/v1/assistant/attachments/${attachmentId}/retry-processing`,
      { method: "POST" },
    );
  }

  async listActions(conversationId: string): Promise<PendingAction[]> {
    return this.request(
      `/v1/assistant/conversations/${conversationId}/actions`,
    );
  }

  async editAction(
    actionId: string,
    payload: Record<string, unknown>,
  ): Promise<PendingAction> {
    return this.request(`/v1/assistant/actions/${actionId}`, {
      method: "PATCH",
      body: JSON.stringify({ payload }),
    });
  }

  async confirmAction(actionId: string): Promise<PendingAction> {
    return this.request(`/v1/assistant/actions/${actionId}/confirm`, {
      method: "POST",
    });
  }

  async cancelAction(actionId: string): Promise<PendingAction> {
    return this.request(`/v1/assistant/actions/${actionId}/cancel`, {
      method: "POST",
    });
  }

  async undoAction(actionId: string): Promise<PendingAction> {
    return this.request(`/v1/assistant/actions/${actionId}/undo`, {
      method: "POST",
    });
  }

  async listHostRecords(): Promise<HostRecord[]> {
    return this.request("/v1/assistant/host/records");
  }

  async listMemory(conversationId?: string): Promise<MemoryRecord[]> {
    const query = conversationId
      ? `?conversation_id=${encodeURIComponent(conversationId)}`
      : "";
    return this.request(`/v1/assistant/memory${query}`);
  }

  async createMemory(input: {
    conversation_id?: string;
    scope: "conversation" | "app" | "user";
    content: string;
  }): Promise<MemoryRecord> {
    return this.request("/v1/assistant/memory", {
      method: "POST",
      body: JSON.stringify(input),
    });
  }

  async deleteMemory(id: string): Promise<void> {
    await this.request(`/v1/assistant/memory/${id}`, { method: "DELETE" });
  }

  async privacyResources(): Promise<PrivacyResource[]> {
    return this.request("/v1/assistant/privacy/resources");
  }

  async exportPrivacy(categories: string[]): Promise<PrivacyJob> {
    return this.request("/v1/assistant/privacy/exports", {
      method: "POST",
      body: JSON.stringify({ categories }),
    });
  }

  async previewDeletion(
    categories: string[],
    conversationId?: string,
  ): Promise<PrivacyJob> {
    return this.request("/v1/assistant/privacy/deletions/preview", {
      method: "POST",
      body: JSON.stringify({ categories, conversation_id: conversationId }),
    });
  }

  async confirmDeletion(jobId: string): Promise<PrivacyJob> {
    return this.request("/v1/assistant/privacy/deletions", {
      method: "POST",
      body: JSON.stringify({ job_id: jobId }),
    });
  }

  private async request<T>(
    path: string,
    init: RequestInit = {},
    jsonBody = true,
  ): Promise<T> {
    const headers = new Headers(init.headers);
    for (const [name, value] of Object.entries(this.authHeaders()))
      headers.set(name, value);
    if (jsonBody && init.body) headers.set("Content-Type", "application/json");
    const response = await fetch(`${this.baseUrl}${path}`, {
      ...init,
      headers,
    });
    if (!response.ok) throw await this.error(response);
    if (response.status === 204) return undefined as T;
    return response.json() as Promise<T>;
  }

  private authHeaders(): Record<string, string> {
    return { "X-Actor-ID": this.actorId, "X-Scope-Key": this.scopeKey };
  }

  private async error(response: Response): Promise<ApiError> {
    const payload = (await response.json()) as {
      message: string;
      code: string;
    };
    return new ApiError(payload.message, response.status, payload.code);
  }
}
