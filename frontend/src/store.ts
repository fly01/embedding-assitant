import { computed, reactive } from "vue";
import { AssistantApi } from "./api";
import type {
  AssistantEvent,
  Attachment,
  Citation,
  ContextProfile,
  DisclosureLevel,
  ExecutionMode,
  Message,
  PendingAction,
  ToolActivityItem,
} from "./types";

export function createAssistantStore(api: AssistantApi) {
  const state = reactive({
    conversationId: "",
    messages: [] as Message[],
    actions: [] as PendingAction[],
    draftAttachments: [] as Attachment[],
    tools: [] as ToolActivityItem[],
    citations: [] as Citation[],
    thinking: "",
    reasoningSummary: "",
    rawTrace: "",
    developerEvents: [] as AssistantEvent[],
    streaming: false,
    currentRunId: "",
    error: "",
    disclosureLevel: "status" as DisclosureLevel,
    contextProfile: "lite" as ContextProfile,
    executionMode: "confirm_each" as ExecutionMode,
  });

  const activeActions = computed(
    () => new Map(state.actions.map((action) => [action.id, action])),
  );
  let lastRequest: {
    text: string;
    attachmentIds: string[];
    contextProfile: ContextProfile;
    executionMode: ExecutionMode;
    disclosureLevel: DisclosureLevel;
  } | null = null;

  async function loadConversation(conversationId: string): Promise<void> {
    lastRequest = null;
    state.conversationId = conversationId;
    state.error = "";
    state.messages = await api.listMessages(conversationId);
    state.actions = await api.listActions(conversationId);
    state.draftAttachments = [];
    state.tools = [];
    state.citations = [];
    state.thinking = "";
    state.reasoningSummary = "";
    state.rawTrace = "";
    state.developerEvents = [];
  }

  async function send(text: string): Promise<void> {
    const request = {
      text,
      attachmentIds: state.draftAttachments.map((attachment) => attachment.id),
      contextProfile: state.contextProfile,
      executionMode: state.executionMode,
      disclosureLevel: state.disclosureLevel,
    };
    lastRequest = request;
    await execute(request);
  }

  async function execute(
    request: NonNullable<typeof lastRequest>,
  ): Promise<void> {
    state.streaming = true;
    state.error = "";
    state.tools = [];
    state.citations = [];
    state.thinking = "";
    state.reasoningSummary = "";
    state.rawTrace = "";
    state.developerEvents = [];
    try {
      const created = await api.startRun(state.conversationId, {
        text: request.text,
        attachment_ids: request.attachmentIds,
        context_profile: request.contextProfile,
        execution_mode: request.executionMode,
        disclosure_level: request.disclosureLevel,
      });
      state.currentRunId = created.run_id;
      state.draftAttachments = [];
      state.messages = await api.listMessages(state.conversationId);
      await api.streamRun(created.run_id, applyEvent);
      state.messages = await api.listMessages(state.conversationId);
      state.actions = await api.listActions(state.conversationId);
    } catch (error) {
      state.error = error instanceof Error ? error.message : String(error);
    } finally {
      state.streaming = false;
      state.currentRunId = "";
    }
  }

  async function stop(): Promise<void> {
    if (!state.currentRunId) throw new Error("No Run is active");
    await api.cancelRun(state.currentRunId);
  }

  async function regenerate(): Promise<void> {
    if (!lastRequest)
      throw new Error("No user request is available to regenerate");
    await execute({ ...lastRequest, executionMode: "confirm_each" });
  }

  function applyEvent(event: AssistantEvent): void {
    if (["developer", "raw_trace"].includes(state.disclosureLevel))
      state.developerEvents.push(event);
    if (event.type === "message.created")
      upsertMessage(event.payload.message as Message);
    if (event.type === "content.delta")
      appendText(event.payload.message_id, event.payload.text);
    if (event.type === "message.completed")
      upsertMessage(event.payload.message as Message);
    if (event.type === "thinking.status") {
      const context = Array.isArray(event.payload.context)
        ? ` · ${event.payload.context.join(", ")}`
        : "";
      state.thinking = `${event.payload.stage}${context}`;
    }
    if (event.type === "reasoning.summary.delta")
      state.reasoningSummary += event.payload.text;
    if (event.type === "reasoning.trace.delta")
      state.rawTrace += event.payload.text;
    if (event.type === "reasoning.trace.unavailable")
      state.rawTrace = "Provider trace is unavailable.";
    if (event.type === "run.failed")
      state.error = String(event.payload.message ?? "Assistant Run failed");
    if (["run.completed", "run.failed", "run.interrupted"].includes(event.type))
      state.thinking = "";
    if (event.type === "tool.requested")
      upsertTool(event.payload.name, "requested");
    if (event.type === "tool.started")
      upsertTool(event.payload.name, "running");
    if (event.type === "tool.completed")
      upsertTool(event.payload.name, "completed", event.payload.result);
    if (event.type === "tool.failed")
      upsertTool(
        event.payload.name,
        "failed",
        undefined,
        event.payload.message,
      );
    if (event.type === "citation.added")
      state.citations.push(event.payload as Citation);
    if (event.type.startsWith("action."))
      upsertAction(event.payload.action as PendingAction);
  }

  async function addAttachments(files: FileList | File[]): Promise<void> {
    const selected = Array.from(files);
    if (state.draftAttachments.length + selected.length > 8) {
      state.error = "A message can contain at most eight attachments.";
      return;
    }
    for (const file of selected) {
      state.draftAttachments.push(
        await api.uploadAttachment(state.conversationId, file),
      );
    }
  }

  function removeAttachment(id: string): void {
    state.draftAttachments = state.draftAttachments.filter(
      (attachment) => attachment.id !== id,
    );
  }

  function moveAttachment(index: number, direction: -1 | 1): void {
    const target = index + direction;
    if (target < 0 || target >= state.draftAttachments.length) return;
    const attachments = [...state.draftAttachments];
    [attachments[index], attachments[target]] = [
      attachments[target],
      attachments[index],
    ];
    state.draftAttachments = attachments;
  }

  async function retryAttachment(id: string): Promise<void> {
    const index = state.draftAttachments.findIndex(
      (attachment) => attachment.id === id,
    );
    if (index === -1) throw new Error(`Unknown Draft Attachment ${id}`);
    state.draftAttachments[index] = await api.retryAttachment(id);
  }

  async function addVoiceMessage(file: File): Promise<string> {
    const attachment = await api.uploadAttachment(
      state.conversationId,
      file,
      "voice",
    );
    const transcript = await api.transcribe(attachment.id);
    state.draftAttachments.push(attachment);
    return transcript.text;
  }

  async function confirmAction(id: string): Promise<void> {
    upsertAction(await api.confirmAction(id));
  }

  async function cancelAction(id: string): Promise<void> {
    upsertAction(await api.cancelAction(id));
  }

  async function editAction(
    id: string,
    payload: Record<string, unknown>,
  ): Promise<void> {
    upsertAction(await api.editAction(id, payload));
  }

  async function undoAction(id: string): Promise<void> {
    upsertAction(await api.undoAction(id));
  }

  function upsertMessage(message: Message): void {
    const index = state.messages.findIndex((item) => item.id === message.id);
    if (index === -1) state.messages.push(message);
    else state.messages[index] = message;
    state.messages.sort((a, b) => a.sequence - b.sequence);
  }

  function appendText(messageId: string, text: string): void {
    const message = state.messages.find((item) => item.id === messageId);
    if (!message)
      throw new Error(`Protocol violation: unknown message ${messageId}`);
    const part = message.content.find((item) => item.type === "markdown");
    if (!part)
      throw new Error(
        `Protocol violation: message ${messageId} has no Markdown part`,
      );
    part.text = `${part.text ?? ""}${text}`;
  }

  function upsertAction(action: PendingAction): void {
    const index = state.actions.findIndex((item) => item.id === action.id);
    if (index === -1) state.actions.push(action);
    else state.actions[index] = action;
  }

  function upsertTool(
    name: string,
    status: ToolActivityItem["status"],
    result?: Record<string, unknown>,
    message?: string,
  ): void {
    const index = state.tools.findIndex((tool) => tool.name === name);
    const tool = { name, status, result, message };
    if (index === -1) state.tools.push(tool);
    else state.tools[index] = tool;
  }

  return {
    state,
    activeActions,
    loadConversation,
    send,
    stop,
    regenerate,
    addAttachments,
    removeAttachment,
    moveAttachment,
    retryAttachment,
    addVoiceMessage,
    confirmAction,
    cancelAction,
    editAction,
    undoAction,
  };
}

export type AssistantStore = ReturnType<typeof createAssistantStore>;
