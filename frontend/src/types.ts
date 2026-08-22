export type ConversationMode = "single" | "multiple";
export type ContextProfile = "lite" | "balanced" | "durable";
export type DisclosureLevel =
  "hidden" | "status" | "contextual" | "activity" | "developer" | "raw_trace";
export type ExecutionMode =
  "read_only" | "confirm_each" | "auto_apply_allowlist";

export interface Conversation {
  schema_version: "0.1";
  id: string;
  actor_id: string;
  scope_key: string;
  title: string;
  status: "active" | "archived";
  created_at: string;
  updated_at: string;
}

export interface ContentPart {
  type: string;
  order: number;
  text?: string | null;
  attachment_id?: string | null;
  data: Record<string, unknown>;
}

export interface Message {
  schema_version: "0.1";
  id: string;
  conversation_id: string;
  role: "user" | "assistant" | "tool";
  sequence: number;
  content: ContentPart[];
  created_at: string;
  visible_at?: string | null;
  completed_at?: string | null;
  edited_at?: string | null;
}

export interface AssistantEvent {
  schema_version: "0.1";
  event_id: string;
  scope: {
    kind: "run" | "conversation" | "attachment" | "privacy_job" | "composer";
    id: string;
  };
  seq: number;
  conversation_id?: string | null;
  run_id?: string | null;
  type: string;
  created_at: string;
  payload: Record<string, any>;
}

export interface Attachment {
  schema_version: "0.1";
  id: string;
  conversation_id?: string | null;
  owner_scope: string;
  kind:
    | "image"
    | "document"
    | "spreadsheet"
    | "text"
    | "audio"
    | "archive"
    | "unknown";
  name: string;
  mime_type: string;
  size_bytes: number;
  source: "picker" | "camera" | "paste" | "drag_drop" | "voice";
  upload_status: "local" | "uploading" | "uploaded" | "failed";
  processing_status:
    | "none"
    | "queued"
    | "processing"
    | "ready"
    | "partial"
    | "failed"
    | "unsupported"
    | "blocked";
  retention_policy: string;
  permission_scope: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export type ActionState =
  | "proposed"
  | "policy_evaluating"
  | "blocked"
  | "awaiting_confirmation"
  | "editing"
  | "auto_applying"
  | "applying"
  | "applied"
  | "failed"
  | "retrying"
  | "cancelled"
  | "expired"
  | "blocked_plugin_disabled"
  | "archived"
  | "undoing"
  | "undone"
  | "undo_failed";

export interface PendingAction {
  schema_version: "0.1";
  id: string;
  conversation_id: string;
  run_id?: string | null;
  action_type: string;
  payload: Record<string, any>;
  state: ActionState;
  execution_mode: ExecutionMode;
  idempotency_key: string;
  policy_decision?: Record<string, any> | null;
  result?: Record<string, any> | null;
  plugin_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface Transcript {
  schema_version: "0.1";
  id: string;
  attachment_id: string;
  text: string;
  language: string;
  adapter: string;
  revision: number;
  is_user_correction: boolean;
  created_at: string;
}

export interface PrivacyResource {
  category: string;
  count: number;
  owner: "framework" | "host";
  retention: string;
  exportable: boolean;
  deletable: boolean;
}

export interface PrivacyJob {
  schema_version: "0.1";
  id: string;
  kind: "export" | "deletion";
  status:
    | "requested"
    | "previewing"
    | "awaiting_confirmation"
    | "running"
    | "completed"
    | "partial"
    | "failed"
    | "cancelled"
    | "retrying";
  scope: { categories: string[]; conversation_id?: string | null };
  preview: Record<string, any>;
  results: Array<Record<string, any>>;
  created_at: string;
  updated_at: string;
}

export interface MemoryRecord {
  schema_version: "0.1";
  id: string;
  actor_id: string;
  conversation_id?: string | null;
  scope: "conversation" | "app" | "user";
  content: string;
  provenance: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface HostRecord {
  id: string;
  title: string;
  amount: number;
  occurred_at: string;
  version: number;
}

export interface ToolActivityItem {
  name: string;
  status: "requested" | "running" | "completed" | "failed";
  result?: Record<string, unknown>;
  message?: string;
}

export interface Citation {
  title: string;
  source_url?: string | null;
  document_id: string;
}
