# Framed Assistant MVP Specification

## Status

- Version: `0.1.0-draft`
- Status: draft implementation baseline
- Last updated: 2026-08-22
- Scope: minimum viable public framework specification intended for open-source release
- Intended audience: framework maintainers, Host integration authors, application developers, plugin authors, UI contributors, and reviewers

This document defines the public MVP contract for Framed Assistant. It describes observable behavior, stable interfaces, module boundaries, conformance requirements, and release criteria. It does not prescribe private deployment details or a domain-specific data model.

## Abstract

Framed Assistant is a framework for embedding a consistent, high-quality AI assistant into an existing application. It provides a shared conversation runtime, typed event protocol, host-controlled tools and actions, progressive capability packages, a Headless frontend SDK, and a production-ready default UI.

The framework owns assistant behavior and protocol consistency. The Host application retains authority over identity, private data, permissions, business validation, transactions, and committed writes. Declarative integrations, generated adapters, and plugins extend declared capabilities but cannot bypass that boundary.

## Normative language

The terms **MUST**, **MUST NOT**, **REQUIRED**, **SHOULD**, **SHOULD NOT**, and **MAY** are normative requirements.

- **MUST** and **MUST NOT** define conformance requirements.
- **SHOULD** and **SHOULD NOT** define recommended behavior; deviations require a documented reason.
- **MAY** defines optional behavior.

Examples are informative unless explicitly marked normative.

## Goals

The MVP MUST:

1. Let a host application embed a text assistant with minimal integration code.
2. Provide one event protocol, state model, error model, permission model, and audit model across applications.
3. Provide both a polished default interface and an unstyled Headless interaction layer.
4. Support progressive adoption of image, two-mode voice input, file, tool, retrieval, memory, and policy-controlled Action execution.
5. Let hosts add domain tools, context providers, actions, and renderers through a declarative Integration Manifest, a generated integration, or an optional custom plugin without modifying the core runtime.
6. Keep business data access and final writes under host-application control.
7. Preserve original conversation records when optional context summarization is enabled.
8. Allow modules to be implemented and tested independently against shared fixtures.
9. Support configurable single- or multi-conversation topology and configurable context profiles without creating separate runtimes.
10. Allow a standard CRUD-style application to integrate without hand-writing a Domain Plugin.
11. Provide one Privacy Center for inventory, export, deletion, retention visibility, and derived-data invalidation across all assistant-managed data.
12. Provide one Attachment System for draft composition, private storage, processing, message rendering, preview, retry, provenance, and explicit promotion into Host business resources.
13. Provide configurable Host Data Write Tools for reviewed schema-bound CRUD operations; keep them disabled by default and prohibit arbitrary SQL or unscoped database access.

## Non-goals

The MVP does not include:

- an online third-party plugin marketplace;
- arbitrary plugin code downloaded at runtime;
- production-runtime scanning that automatically discovers and activates undeclared Host APIs or write operations;
- arbitrary SQL, arbitrary table/column access, or model-authored query predicates against a Host database;
- browser automation as a general-purpose assistant capability;
- arbitrary code execution;
- payments, transfers, or irreversible financial operations;
- autonomous background agents that operate without an active user request;
- multi-agent orchestration;
- one shared business schema across unrelated host applications;
- guaranteed access to hidden reasoning that a model provider does not return;
- official UI kits for every frontend framework.

## Terminology

| Term | Definition |
| --- | --- |
| Core | The protocol and runtime behavior shared by every host. |
| Host application | The product embedding Framed Assistant. It owns identity, data, authorization, validation, and committed writes. |
| Host Adapter | The bounded interface through which the framework requests identity, context, authorization, media access, and action execution. |
| Conversation | An ordered, persistent set of messages within one host-defined scope. |
| Run | One execution initiated by a user message, including model output, tool calls, events, and completion state. |
| Tool | A typed capability callable by the runtime. A tool cannot directly exceed its declared permissions or side-effect class. |
| Action | Typed representation of a Host-side business change. It is applied only after Host execution policy selects user confirmation or a pre-approved auto-apply path. |
| Executable Action | Action carrying an immutable positive policy decision that authorizes either a user-confirmed or reviewed automatic Host application. |
| Execution mode | Host and scope policy selecting `read_only`, `confirm_each`, or `auto_apply_allowlist` behavior for business Actions. |
| Auto-apply policy | Reviewed allowlist and bounded risk rules that permit eligible Actions to skip per-operation user confirmation while retaining validation, transaction, idempotency, audit, and result visibility. |
| Host Data Write Tool | Manifest-generated schema-bound create, update, upsert, delete, link, or unlink capability that always produces a typed Action and executes only through the Host data adapter. |
| Host data adapter | Host-owned transactional boundary that maps approved data tools to scoped repositories or APIs without exposing raw database credentials, SQL, tables, or unrestricted queries to the model. |
| Capability package | An officially maintained, versioned package enabled according to its documented default and Host policy; the required safety baseline cannot be disabled. |
| Host Integration Manifest | Declarative application configuration for context sources, tools, Actions, permissions, generic renderers, and adapter mappings. |
| Integration Generator | Development/build-time tool that analyzes public application contracts and produces a reviewable Host Integration Manifest plus scaffolding. |
| Plugin | Optional release-time-installed executable extension for capabilities that cannot be expressed safely through configuration or generated adapters. |
| Headless SDK | Frontend state and behavior without visual styling. |
| Context summary | Rebuildable derived text used to fit conversation history into a model context window. |
| Memory | Persistent, scoped information intentionally retained for future runs under explicit policy. |
| Reasoning summary | Provider-supplied or separately generated user-readable explanation of key reasoning steps. |
| Provider reasoning trace | Raw reasoning content explicitly returned by a model provider. It does not include hidden internal state that the provider does not expose. |
| Disclosure level | Host-bounded setting controlling how much status, activity, developer data, or provider reasoning trace is visible. |
| Conversation mode | Host configuration selecting one active Conversation per scope (`single`) or multiple user-manageable Conversations (`multiple`). |
| Context profile | Named policy preset controlling which sources the Context Compiler may use and how it allocates the model token budget. |
| Context segment | Internal, user-invisible group of complete turn groups used as a compaction and retrieval boundary. |
| Working Ledger | Rebuildable structured state for active goals, constraints, corrections, decisions, open threads, and entity or Action references. |
| Context View | Immutable, per-Run compilation of model input blocks selected under one token budget and permission snapshot. |
| Context Manifest | Developer-facing explanation of which blocks entered a Context View, why they were selected, their token cost, and what was excluded. |
| Voice message | Persisted playable audio Message that is transcribed by a backend batch-ASR adapter before its transcript enters the assistant Run. |
| Live dictation | Streaming or incremental ASR that fills an editable Composer draft; audio is not sent as a playable Message. |
| Message time divider | Derived UI label inserted before a message group when the first visible message, local-date boundary, or configured inactivity threshold requires a new time anchor. |
| Privacy Resource | Registered assistant-managed data category with owner, scope, retention, export, deletion, and derived-artifact metadata. |
| Privacy Job | Idempotent, resumable export or deletion workflow with preview, confirmation, progress, partial-result, and completion state. |
| Attachment Asset | Stable private image, file, or audio resource with variants, ownership, permissions, retention, and independent upload/processing state. |
| Draft Attachment | Composer-local ordered reference to a selected Attachment Asset or pending local file, including validation, optimization, upload, retry, and removal state. |
| Message Attachment Part | Immutable ordered Message content part that references a stable Attachment Asset and declares whether it is required, optional, or display-only model input. |
| Attachment Processing Result | Versioned derived OCR, extraction, vision, transcription, or structured parsing output with provenance and warnings. |
| Attachment Promotion | Explicit confirmed operation that copies or links a chat Attachment Asset into a Host-owned business resource. |

## Architecture

```text
Host application
  identity · authorization · business data · transactions · media · refresh
                         │
                         ▼
Host Adapter ── Framed Assistant protocol ── Headless SDK ── Default UI
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
       Runtime      Tool/Action      Plugin host
          │          governance          │
          └──────────────┬───────────────┘
                         ▼
              Official capability packages
```

### Authority boundary

- The framework MUST NOT query a host database directly.
- An integration or plugin MUST NOT receive undeclared data access.
- A model MUST NOT commit a business write.
- Every business change MUST become a typed Action before execution policy is evaluated.
- The Host MUST authorize every protected read, external request, and proposed write.
- The Host MUST validate permissions and Action payloads again immediately before either confirmed or automatic application.
- The host MUST execute committed writes transactionally or return a structured failure.

### Progressive adoption

A host MAY adopt the framework in stages:

1. text conversation with the default assistant shell, minimal Host Adapter, and enabled Essentials baseline;
2. additional bounded Host context and deterministic read-only tools;
3. image, voice, and file input;
4. configurable reasoning disclosure and visible tool activity;
5. Context Management or Knowledge & Retrieval;
6. Action Workspace, execution mode, and declarative, generated, or custom domain integration;
7. explicit Memory where appropriate.

Every stage MUST remain independently deployable.

### Conversation topology and context profiles

Single- and multi-conversation modes use the same `Conversation`, Runtime, event, and storage contracts. The Host supplies a scope key; `single` permits at most one active Conversation in that scope, while `multiple` permits creation, switching, renaming, archiving, and deletion.

Conversation topology and context strategy are independent settings:

```yaml
conversation_mode: single | multiple
context_profile: lite | balanced | durable
cross_conversation:
  memory: disabled | explicit | policy
  history_retrieval: disabled | on_demand
```

Cross-conversation Memory and cross-conversation history retrieval are separate capabilities. Memory contains policy-approved durable information; history retrieval searches source Conversation records on demand.

All profiles use one Context Compiler and one `ContextView` contract:

- `lite`: authoritative Host facts, current input, pending Action state, and a bounded recent raw window. This baseline is available without M8.
- `balanced`: `lite` plus a Working Ledger, rolling/segment summaries, relevant historical retrieval, and a Context Manifest. This profile requires M8.
- `durable`: `balanced` plus immutable Context Segments, structured supersession and correction tracking, hybrid raw retrieval, derived-artifact invalidation, rebuild, and complete provenance. This profile requires M8 and is recommended for long-lived single-conversation assistants.

Profiles are policy presets, not separate implementations. Switching profiles MUST preserve the raw Conversation. An upgrade to a richer profile builds derived artifacts before atomic activation; a downgrade stops using richer artifacts without deleting source history.

### Host integration levels

Every host provides a minimal Host Adapter boundary, but a custom Domain Plugin is optional. The framework supports four integration levels:

| Level | Integration form | Capabilities |
| --- | --- | --- |
| `Level 0` | direct embed | Default chat, UI, Essentials, explicit page context, and no domain tools or writes. |
| `Level 1` | declarative Host Integration Manifest | Configured context sources, OpenAPI/JSON-Schema tools, generic renderers, and reviewed Action mappings without custom plugin code. |
| `Level 2` | generated integration | Development-time analysis of OpenAPI, schemas, routes, types, and permission metadata produces a reviewable Manifest, adapters, fixtures, and unresolved-risk report. |
| `Level 3` | custom Domain Plugin | Executable extension for complex validation, multi-step transactions, custom retrieval, specialized renderers, third-party services, or compensating operations. |

The minimal Host Adapter always owns actor identity, Conversation scope, authentication, authorization, final Action application, and data refresh. Generic SDK adapters MAY implement this boundary from approved configuration.

The Integration Generator runs only during development or build workflows. It MAY propose read tools and write-proposal Actions, but it MUST NOT activate write operations automatically before human review. Unresolved permissions, idempotency, transaction, cascading-delete, privacy, confirmation, or undo semantics fail closed and require human review.

### Action execution modes

```yaml
assistant:
  execution_mode: read_only | confirm_each | auto_apply_allowlist
```

- `read_only`: protected reads may run under policy; business writes are not proposed or applied.
- `confirm_each`: every eligible business Action enters `awaiting_confirmation`. This is the framework default.
- `auto_apply_allowlist`: reviewed low-risk Action types may skip per-operation user confirmation and proceed through policy evaluation to Host application.

Automatic application never means direct model database access. The Action remains typed, versioned, authorized, schema-validated, idempotent, transactional, audited, visible in history, and subject to Privacy Center. Auto-apply policy is configured per Host, scope, actor, and Action type and includes impact/rate limits, confidence or ambiguity gates, and a compensation or undo declaration where applicable.

An Action is auto-apply eligible only when its Integration Manifest or Plugin Manifest is approved, its type is explicitly allowlisted, the actor remains authorized, payload and current target version validate, risk and impact are within configured bounds, an idempotency key exists, and Host transaction semantics are known. A policy miss falls back to `awaiting_confirmation` or `blocked`; it does not execute optimistically.

Payments, transfers, and other `dangerous` capabilities are unavailable in the MVP and MUST remain blocked even if a user offers confirmation. Supported Actions for delete, external communication, private-data sharing, account or permission change, bulk mutation, irreversible operation, attachment Promotion, ambiguous targets, low-confidence OCR/ASR, and operations without an approved compensation policy require confirmation regardless of execution mode. Privacy deletion uses the separate Privacy Job destructive-confirmation flow.

### Core entities

| Entity | Purpose | Required relationships |
| --- | --- | --- |
| `Conversation` | Host-scoped conversation container | actor, host scope, protocol version |
| `Message` | Immutable user, assistant, or tool content | conversation, role, sequence, content parts, created/visible/completed/edited timing |
| `Run` | Execution lifecycle for one user turn | input message, event sequence, status, usage |
| `AttachmentAsset` | Controlled image, audio, or file resource | owner, kind, MIME, bytes, variants, storage, permission, retention |
| `DraftAttachment` | Composer-local pending attachment | local/stable ID, order, validation, optimization, upload, retry/removal |
| `MessageAttachmentPart` | Immutable attachment content in one Message | attachment ID, part order, required/optional/display-only model use |
| `AttachmentProcessingResult` | Derived parser/model output | attachment, processor/version, status, provenance, warnings |
| `ToolInvocation` | Typed tool request and result | run, tool version, permission decision, audit reference |
| `PendingAction` | Uncommitted host-side change proposal | schema version, payload, state, idempotency key |
| `ActionPolicyDecision` | Immutable execution-policy result | mode, rule/version, risk, bounds, reason, confirmation or auto-apply outcome |
| `ContextSegment` | Internal compaction and retrieval unit | complete turn groups, source range, closure reason |
| `SummarySegment` | Rebuildable context summary | source message range, summary version, validity state |
| `WorkingLedger` | Rebuildable current task state | goals, constraints, corrections, open threads, references |
| `ContextView` | Immutable per-Run model input | profile, permission snapshot, ordered context blocks |
| `ContextManifest` | Context selection evidence | block sources, priorities, token cost, exclusions |
| `MemoryRecord` | Explicit long-term information | provenance, scope, visibility, revision history |
| `AuditEvent` | Security and debugging evidence | actor, operation, decision, redaction metadata |
| `HostIntegrationState` | Active declarative/generated integration | Manifest version, review status, unresolved risks, adapter bindings |
| `PluginState` | Installed plugin activation state | plugin version, contract range, configuration, migration state |
| `PrivacyResource` | User-visible assistant data category | owner, scope, retention, processor, export/delete capabilities |
| `PrivacyJob` | Export or deletion workflow | request scope, preview, confirmation, status, item results, audit reference |

`Message` records are authoritative conversation history. Summaries, search indexes, and frontend caches are derived data.

## Protocol

### Source of truth

M0 JSON Schemas are the canonical cross-language contract. Generated TypeScript types, Python models, OpenAPI documents, and fixtures MUST conform to those schemas.

Every public payload MUST include a schema version. Breaking changes require a new protocol version.

### Event envelope

```ts
interface AssistantEvent<TPayload = unknown> {
  schema_version: "0.1";
  event_id: string;
  scope: {
    kind: "run" | "conversation" | "attachment" | "privacy_job" | "composer";
    id: string;
  };
  seq: number;
  conversation_id?: string;
  run_id?: string;
  type:
    | "run.started"
    | "message.created"
    | "content.delta"
    | "message.completed"
    | "thinking.status"
    | "reasoning.summary.delta"
    | "reasoning.trace.delta"
    | "reasoning.trace.completed"
    | "reasoning.trace.unavailable"
    | "transcription.started"
    | "transcription.delta"
    | "transcription.completed"
    | "transcription.failed"
    | "privacy.job.updated"
    | "attachment.updated"
    | "attachment.upload.updated"
    | "attachment.processing.updated"
    | "attachment.promotion.updated"
    | "tool.requested"
    | "tool.started"
    | "tool.completed"
    | "tool.failed"
    | "action.proposed"
    | "action.policy_evaluated"
    | "action.auto_applying"
    | "action.updated"
    | "action.applied"
    | "action.failed"
    | "citation.added"
    | "run.completed"
    | "run.interrupted"
    | "run.reconciled"
    | "run.failed";
  created_at: string;
  payload: TPayload;
}
```

Normative event behavior:

- `scope.id` MUST identify the Run, Conversation, Attachment, Privacy Job, or Composer session whose stream owns the event.
- `seq` MUST increase monotonically within that scope.
- Run-scoped events MUST include `conversation_id` and `run_id`. Attachment-, Privacy-Job-, and Composer-scoped events MUST NOT invent a `run_id`; they MAY include `conversation_id` only when one already exists.
- `event_id` MUST be stable so clients can deduplicate replayed events.
- Clients MUST ignore unknown event types safely and record a diagnostic.
- A sequence gap MUST trigger reconciliation rather than silent state mutation.
- A completed run MUST contain visible assistant text, a tool result, or an action proposal.
- An empty or prematurely closed stream MUST NOT be presented as a successful answer.
- `thinking.status` MAY contain stage labels, contextual progress, or elapsed time.
- Every model adapter MUST declare `reasoning_visibility` as `none`, `summary`, or `trace`.
- When the configured disclosure level is `raw_trace`, the client MAY display the complete provider reasoning trace exactly as returned by an adapter that declares `trace` support.
- The framework MUST NOT synthesize a raw trace when the provider does not return one; it MUST emit `reasoning.trace.unavailable` instead.
- `raw_trace` MUST be disabled by default and requires explicit Host policy plus viewer authorization.

### Message content parts

The MVP MUST support typed message parts for:

- plain text;
- Markdown text;
- image attachments;
- file attachments;
- playable audio voice messages;
- editable voice transcripts;
- versioned backend transcripts attached to sent voice messages;
- tool activity;
- citations;
- action cards;
- recoverable errors;
- thinking status;
- reasoning summaries;
- provider reasoning traces when enabled.

A renderer that does not recognize a content type MUST use a safe generic representation rather than fail the entire conversation.

### Message ordering and time dividers

Message order is determined by a stable server `sequence`, never by a timestamp. Timing fields are stored as UTC instants: `created_at`, optional `visible_at`, optional `completed_at`, optional `edited_at`, and optional `sender_timezone`. User messages display from `created_at`; assistant messages use `visible_at ?? created_at`.

Time dividers are derived UI, not stored Messages. The default divider policy is:

```yaml
message_time_divider:
  inactivity_threshold_seconds: 300
  show_for_first_visible_message: true
  always_show_on_local_date_change: true
  timezone: viewer
```

A divider appears before the first visible message, when adjacent visible messages cross a local-date boundary, or when their display times are at least the configured inactivity threshold apart. Continuous messages inside the threshold do not repeat a time label. The threshold is Host-configurable; the default is five minutes.

Divider formats are localized by age: today `HH:mm`, yesterday `Yesterday HH:mm`, the recent week `weekday HH:mm`, earlier in the current year `month day HH:mm`, and older years `year month day HH:mm`. The Host MAY select viewer, Conversation, or Host timezone; business-domain times remain separate from chat display time.

History pagination MUST recompute dividers after pages merge and preserve the reading anchor. Tool, transcription, Action, or plugin-state updates change content in place and MUST NOT reorder the parent Message or create a new chat timestamp. Exact timestamps remain available through message details and accessibility labels.

### Reference HTTP transport

The protocol is transport-neutral. The reference server exposes:

- `POST /v1/assistant/conversations`
- `GET /v1/assistant/conversations`
- `GET /v1/assistant/conversations/{conversation_id}`
- `PATCH /v1/assistant/conversations/{conversation_id}`
- `GET /v1/assistant/conversations/{conversation_id}/messages?before=<message_id>&limit=<n>`
- `POST /v1/assistant/conversations/{conversation_id}/runs`
- `GET /v1/assistant/runs/{run_id}/events?after_seq=<seq>`
- `POST /v1/assistant/runs/{run_id}/cancel`
- `POST /v1/assistant/attachments`
- `GET /v1/assistant/attachments/{attachment_id}`
- `GET /v1/assistant/attachments/{attachment_id}/thumbnail`
- `GET /v1/assistant/attachments/{attachment_id}/preview`
- `GET /v1/assistant/attachments/{attachment_id}/original`
- `POST /v1/assistant/attachments/{attachment_id}/retry-processing`
- `PATCH /v1/assistant/actions/{action_id}`
- `POST /v1/assistant/actions/{action_id}/confirm`
- `POST /v1/assistant/actions/{action_id}/cancel`
- `POST /v1/assistant/actions/{action_id}/undo`
- `GET /v1/assistant/capabilities`
- `GET /v1/assistant/privacy/resources`
- `POST /v1/assistant/privacy/exports`
- `POST /v1/assistant/privacy/deletions/preview`
- `POST /v1/assistant/privacy/deletions`
- `GET /v1/assistant/privacy/jobs/{job_id}`

The reference implementation uses Server-Sent Events for run events. A run request MUST persist the user message before model execution and return `run_id` plus the latest sequence number. Clients resume with `after_seq`.

In `multiple` mode, the collection endpoint lists authorized Conversations and the patch endpoint handles rename and archive state. Conversation deletion uses the scoped Privacy deletion preview and job flow rather than bypassing it with a direct transport delete.

### Error model

Public errors MUST include a stable code, user-safe message, retryability, and correlation identifier. The minimum categories are:

- validation;
- authentication;
- permission denied;
- capability disabled;
- provider unavailable;
- rate or cost limit;
- tool timeout or failure;
- action conflict;
- stream interrupted;
- plugin incompatibility;
- attachment rejected.

Secrets, credentials, raw private attachments, and unredacted model context MUST NOT appear in public errors.

## Module specifications

All modules except M0 build against M0 contracts. Every module MUST provide its own fake, fixture, or stub so another team can integrate without waiting for its implementation.

| Module | Direct build dependency | Independent development substitute |
| --- | --- | --- |
| M0 Contracts | none | golden fixtures |
| M1 Runtime | M0 | Mock model and fake tool registry |
| M2 Host Integration Bridge | M0 | Fake Host Adapter |
| M3 Tool Runtime | M0 | scripted tools and fake policy decisions |
| M4 Integration and Plugin System | M0 | sample Integration Manifests, plugin manifests, and renderer stubs |
| M5 Headless SDK | M0 | event replay server |
| M6 Default UI | M0, M5 | story fixtures |
| M7 Multimodal Input | M0, M5 | fake upload, ASR, OCR, and vision adapters |
| M8 Context Management | M0 | fake message store and Mock summarizer |
| M9 Knowledge & Retrieval | M0, M3 | mock search, URL, and document adapters |
| M10 Memory | M0 | fake memory store and authorization decisions |
| M11 Action Workspace | M0, M2, M12 contracts | fake action executor |
| M12 Safety & Governance | M0 | policy fixtures and fake audit sink |
| M13 Developer Toolkit | M0 | saved event fixtures |
| M14 Reference Integrations | M0-M13 public APIs | three domain-neutral example fixtures |

### M0. Shared Contracts and Conformance Kit

**Purpose:** define the stable public language used by every other module.

**Responsibilities:**

- JSON Schemas for entities, events, errors, tools, actions, permissions, plugins, context summaries, memory, and audit;
- generated TypeScript and Python types;
- OpenAPI and event-stream documentation;
- valid and invalid golden fixtures;
- schema validators and a conformance command.

**Acceptance:** scoped event replay reconstructs Conversation/Message/time, Attachment/Voice, Reasoning, Tool/Citation, Action/Policy, Context/Memory, and Privacy state; invalid fixtures fail with actionable diagnostics; module IDs and public fields are versioned.

### M1. Assistant Runtime and Model Adapters

**Purpose:** execute one assistant run consistently across hosts.

**Responsibilities:** conversation and run lifecycle, message persistence, Context View compilation through the configured profile, model invocation, event emission, cancellation, retry, regeneration, reconciliation, and usage recording. MVP adapters are OpenAI-compatible and Mock.

**Acceptance:** user input is persisted before provider access; the runtime invokes capabilities only through M3; interrupted streams reconcile from persisted events; non-idempotent operations are never replayed automatically; adapters report reasoning visibility accurately; raw trace events are emitted only when both provider support and Host policy allow them.

### M2. Host Integration Bridge

**Purpose:** keep identity, application context, protected data, and committed writes under Host control while supporting both generic configuration-driven adapters and custom implementations.

**Required Host Adapter operations:**

```ts
interface AssistantHostAdapter {
  getActor(): Promise<ActorContext>;
  getConversationScope(): Promise<ConversationScope>;
  getPageContext(scope: PageContextScope): Promise<PageContext>;
  getDataToolCapabilities?(): Promise<HostDataToolCatalog>;
  authorize(request: PermissionRequest): Promise<PermissionDecision>;
  applyAction(action: ExecutableAction): Promise<ActionApplyResult>;
  refreshData?(result: ActionApplyResult): Promise<void>;
}
```

`ExecutableAction` can be created only after a positive immutable `ActionPolicyDecision` records either explicit user confirmation or reviewed `auto_apply_allowlist` authorization. The model cannot construct this boundary type directly.

**Acceptance:** missing capabilities are reported as disabled; the Host supplies a stable Conversation scope; denied permissions produce structured results; page context has a field allowlist and size budget; any Host data capability catalog is constrained by the approved Integration Manifest and current actor scope; Action application and refresh are explicit, testable callbacks; a `Level 1` application can implement the boundary through an approved Host Integration Manifest without custom Domain Plugin code.

### M3. Tool Runtime and Essentials Pack

**Purpose:** register, discover, validate, authorize, execute, and audit typed tools.

```ts
interface ToolManifest {
  name: string;
  version: string;
  input_schema: object;
  output_schema: object;
  side_effect: "none" | "read" | "write-proposal" | "external-read" | "dangerous";
  risk: "low" | "medium" | "high";
  permissions: string[];
  timeout_ms: number;
  retry: { max_attempts: number };
  confirmation: "none" | "policy" | "explicit" | "typed" | "host-only";
  auto_apply_eligible?: boolean;
  idempotency: "not-applicable" | "run-scoped" | "host-required";
  ui_renderer_key?: string;
  redaction: RedactionPolicy;
}
```

Host Data Write Tools are an optional M3 capability family and are disabled by default:

```yaml
host_data_tools:
  enabled: false
  raw_sql: false

  operations:
    create: false
    update: false
    upsert: false
    delete: false
    link: false
    unlink: false

  entities:
    food_log:
      source: host_repository
      writable_fields: [occurred_at, meal_type, description, calories]
      row_scope: current_actor
      optimistic_lock: version
      execution_mode: confirm_each
```

Enabling the family does not enable every operation. The Host explicitly allowlists entities, operations, writable fields, actor/tenant row scope, concurrency field, validation schema, limits, and execution mode. The generated model-facing tools are domain-shaped names such as `host_data.food_log.create`; the model never receives a generic SQL executor, table browser, unrestricted filter, connection string, or database credential.

Every write-tool call first creates a typed Action containing the validated entity, operation, payload, target/version, permission scope, idempotency key, and provenance. M11 then applies `read_only`, `confirm_each`, or `auto_apply_allowlist`. Create, update, upsert, link, and unlink MAY be reviewed for low-risk automatic application. Delete, bulk mutation, unrestricted relationship changes, and operations without optimistic concurrency or compensation require confirmation or remain disabled.

The Host data adapter maps an approved Action to a parameterized repository/API operation and owns final authorization, validation, transaction, conflict detection, and result serialization. Tool visibility is recalculated per actor and Host scope; disabled or unauthorized tools are omitted from the model tool manifest rather than exposed and rejected later.

Essentials includes date/time/time-zone operations, a calculator, unit conversion, number and currency formatting, text cleanup, and bounded host page context. Currency exchange requires a caller-supplied rate; live rates belong to retrieval or a host plugin.

**Acceptance:** invalid input never executes; invalid output becomes a typed tool failure; automatic retry is limited to deterministic or read-only operations; default tools do not write business data or access the network. Host Data Write Tools are absent from model manifests by default; enabling one entity/operation exposes only its reviewed schema and scope; every call becomes an Action; raw SQL and undeclared fields/rows remain impossible; conflicts and policy misses do not mutate Host data.

### M4. Integration and Plugin System

**Purpose:** register declarative or generated Host integrations and optional executable Domain Plugins without modifying core modules.

Custom Domain Plugins are optional and are installed at release time through the Host build or package manager. Installed plugins MAY be enabled or disabled at runtime through Host configuration. The MVP MUST NOT download or execute arbitrary remote plugin code.

**Responsibilities:** Integration Manifest and Plugin Manifest validation, protocol compatibility, dependency checks, review state, unresolved-risk gates, permission declarations, configuration schema, Privacy Resource plus export/delete/invalidation handler registration, generic and custom renderer registration, migration preflight, enable/disable state, and fail-closed activation.

**Acceptance:** draft or unresolved Integration Manifests do not activate write mappings; integrations or plugins that persist undeclared data or lack required export/delete/invalidation handlers do not activate; incompatible plugins do not activate; disabled plugins expose no new tools or Actions; a renderer failure uses a safe generic renderer; upgrade preflight leaves the previously deployed version active on failure; historical content remains readable without an active custom renderer.

### M5. Frontend Headless SDK

**Purpose:** provide reusable frontend behavior without imposing a visual design.

**Responsibilities:** conversation state, event replay, sequence-based ordering, derived time dividers, pagination, drafts, ordered Draft Attachments, per-attachment validation/optimization/upload/processing state, gallery focus, attachment retry/removal, voice-mode state, disclosure level, thinking status, reasoning summaries, provider trace state, tool activity, citations, Action state, cancellation, retry, and reconnection.

**Acceptance:** the package renders no UI; all state is serializable; reducers handle duplicate events and interrupted streams; an application can replace every visible component while preserving behavior.

### M6. Default Frontend UI Components

**Purpose:** provide an opinionated interface that is ready to ship and remains themeable.

Required components include `AssistantShell`, `ConversationThread`, `ConversationSwitcher`, `ConversationManager`, `MessageTimeDivider`, `UserMessage`, `AssistantMessage`, `StreamingMarkdown`, `ThinkingDisclosure`, `ToolActivity`, `Composer`, `AttachmentTray`, `AttachmentGrid`, `AttachmentFileCard`, `AttachmentProcessingStatus`, `AttachmentLightbox`, `VoiceMessageBubble`, `LiveDictationControl`, `TranscriptionStatus`, `ActionCard`, `AutoAppliedResultCard`, `ExecutionModeSettings`, `HostDataToolSettings`, `CitationList`, `PrivacyCenter`, `PrivacyJobStatus`, `ErrorBanner`, `StopButton`, `RegenerateButton`, and plugin renderer slots.

**Acceptance:** panel, drawer, inline, and full-page modes work at mobile and desktop widths; `multiple` mode exposes authorized create, switch, rename, archive, and Privacy-Job deletion paths; keyboard and screen-reader paths cover every operation; the five-minute default time-grouping rule survives pagination without moving the reading anchor; Attachment Tray location, multi-selection, stable order, per-item retry, message grouping, gallery navigation, and unavailable-source states remain consistent across surfaces; both voice modes expose distinct states and privacy expectations; Privacy Center inventory, preview, export, deletion, partial failure, and retention-limit states are accessible; internal tool identifiers remain hidden below developer level; all six disclosure levels render distinctly; `raw_trace` shows the full provider-supplied trace when available and an explicit unavailable state otherwise.

### M7. Multimodal Input Pack

**Purpose:** standardize image, voice, and file input across hosts.

**Responsibilities:** Attachment Asset creation, image/file selection, camera, paste and drag/drop, Draft Attachment Tray, append/replace policy, ordering, validation, optimization, private upload, processing, retry, message rendering, gallery preview, provenance, explicit Host promotion, voice permission, waveform, timer, cancel, batch and streaming transcription, editable dictation drafts, playable voice-message audio, transcript status, and attachment lifecycle. OCR, vision, document extraction, structured parsing, batch ASR, streaming ASR, and on-device ASR are adapter interfaces rather than fixed providers.

Minimum Attachment Asset state is:

```ts
interface AttachmentAsset {
  id: string;
  owner_scope: string;
  kind: "image" | "document" | "spreadsheet" | "text" | "audio" | "archive" | "unknown";
  name: string;
  mime_type: string;
  size_bytes: number;
  source: "picker" | "camera" | "paste" | "drag_drop" | "voice";
  original_ref: string;
  preview_ref?: string;
  thumbnail_ref?: string;
  upload_status: "local" | "uploading" | "uploaded" | "failed";
  processing_status: "none" | "queued" | "processing" | "ready" | "partial" | "failed" | "unsupported" | "blocked";
  retention_policy: string;
  permission_scope: string;
  host_resource_refs?: string[];
}
```

Default attachment configuration is:

```yaml
attachments:
  tray_position: inside_composer_above_text
  selection_mode: append
  max_count: 8
  max_total_bytes: 52428800
  allow_reorder: true

  send_gate:
    validation_required: true
    optimization_required: true
    upload_required: true

  run_gate:
    required_attachment_failure: ask_user
    optional_attachment_failure: continue_with_warning

  image_grid:
    max_visible: 8
    viewer_scope: message

  privacy:
    storage: private
    public_urls: forbidden
```

Hosts and processor capabilities define accepted MIME types and per-file limits. Reopening the picker appends by default. Limits, selection mode, and reorder support are configurable, but the UI MUST disclose non-default behavior before it replaces, rejects, or truncates a selection. Backend processing MUST NOT silently ignore attachments beyond its own lower limit.

Draft lifecycle is:

```text
selected -> validating -> optimizing -> ready_to_upload -> uploading -> uploaded
uploaded -> processing -> ready | partial | failed | unsupported | blocked
```

Validation, optimization, upload, processing, and model availability are independent states. The Composer Tray remains inside the Composer above the text field, hides when empty, preserves stable selection order, exposes per-item progress/error/retry/removal, and shares the same state with an expanded Composer.

Every sent attachment belongs to one parent Message and shares that Message's ordering, time group, delivery state, retry surface, and privacy scope. Text and attachments MAY use separate visual blocks but MUST NOT become unrelated timeline Messages. User messages default to ordered attachments above text; assistant-generated artifacts default below explanatory text, with explicit `ContentPart.order` remaining authoritative.

Images use thumbnails in the Message list and open a unified `AttachmentLightbox`. One image uses a large constrained thumbnail; two use two columns; three or four use a 2x2 grid; five to eight use a compact three-column grid with a `+N` overflow tile when needed. Every visible image is actionable when authorized. Unavailable original, expired permission, deleted source, or preview failure produces a labelled tombstone or retry state rather than a dead tap. The Lightbox opens at the selected image, navigates the Message image group, supports zoom, keyboard and touch navigation, restores focus on close, and loads Preview or Original only on demand. Download/share/original access follows Host permission.

Non-image files use a consistent card showing name, kind, size, page/count metadata where available, upload status, processing status, warnings, and the permitted action: preview, download, retry, or an explicit unsupported/unavailable reason. Parser capability is distinct from file kind and declares `direct_model_input`, `ocr`, `text_extract`, `structured_parse`, `transcription`, or `unsupported`.

A sent Message may appear before processing completes, but its assistant Run waits for every `model_use: required` Attachment Processing Result. Required failure pauses the Run and offers retry, remove-and-continue, or cancel. Optional failure continues only with a visible warning. The system MUST NOT fabricate extracted content, hide a failed item, or rerun successful upload/processing work when only the model Run failed.

OCR, captions, extracted text, structured tables, embeddings, summaries, thumbnails, and previews are versioned derived artifacts with source Attachment IDs and processor provenance. Historical playback uses stable Attachment IDs and authorized Thumbnail/Preview/Original endpoints; persisted history and caches MUST NOT depend on `blob:` URLs, data URLs, or array indexes.

Chat Attachments are not Host business media by default. A domain Action that saves an attachment as a receipt, record photo, gallery item, or other Host resource MUST show source Attachment references, selected promotion targets, and excluded evidence before confirmation. Confirmation creates an explicit `host_resource_ref` by copy or link according to Host policy. Action fields derived from attachments identify source file, page/region, processor/version, and uncertainty. Privacy Center shows chat and promoted resources separately and previews cross-resource deletion impact.

Voice input configuration is:

```yaml
voice_input:
  modes: [voice_message, live_dictation]
  default_mode: live_dictation
  allow_user_switch: true
```

`voice_message` records and sends a playable audio Message. The audio uploads through private Host-authorized storage, the Message becomes visible with duration and playback state, and a backend batch-ASR adapter produces a derived transcript before the assistant Run consumes text. The original audio is authoritative user content and follows Host retention and deletion policy; the transcript stores its source audio ID, language, adapter/version, confidence when available, status, and revision. A user correction creates a new transcript revision without erasing the automatic transcript. A correction made after an assistant response requires an explicit regenerate operation and MUST NOT replay prior non-idempotent work. Transcription failure leaves the audio Message readable and retryable and MUST NOT fabricate text or silently start the assistant Run.

`live_dictation` streams partial ASR into the Composer and continuously replaces only the current dictation suffix. It MAY use an on-device model or an explicitly disclosed server streaming fallback. Stopping leaves editable text and never sends automatically. On-device failure MUST be disclosed before any server upload. Live-dictation audio is ephemeral by default and is not stored as a Message.

An ASR adapter declares `batch`, `streaming`, or both; execution location `device` or `server`; accepted formats; languages; partial-result support; and retention behavior. If both modes are enabled, the Host provides an explicit mode switch or distinct gestures and persists the user preference only when permitted.

**Acceptance:** selecting multiple attachments uses one Tray above the text field, appends by default, preserves/reorders stable order, enforces the visible limit before send, and supports per-item removal/retry; image/file upload failure preserves the text draft and Draft Attachments; sent text plus attachments remain one Message; every authorized image opens the Lightbox and every unavailable source explains why; upload, processing, and Run failures remain distinguishable; required processing failure pauses for user choice; historical replay uses stable private Attachment IDs; Attachment Promotion requires a confirmed Action with visible source references. Voice-message upload and transcription have independent retry states; voice messages remain playable when transcription fails; the assistant consumes only a completed or user-corrected transcript; live dictation preserves partial text on recoverable failure; neither mode silently changes execution location; frontend and backend enforce the same audio type, duration, size, and privacy policy.

### M8. Context Management Pack

**Purpose:** compile a bounded, inspectable Context View for every Run while keeping long-lived Conversations usable and traceable.

**Responsibilities:** profile selection, token budgeting, complete-turn grouping, Context Segments, a Working Ledger, immutable Segment Summaries, relevant historical retrieval, provenance, supersession, invalidation, rebuild, and Context Manifest generation.

The Context Compiler assembles sources in policy order. System and safety contracts, current user input, authoritative Host facts, and current Action state are non-droppable. Recent raw turns and the Working Ledger have higher priority than retrieved history and old summaries. Lower-relevance summaries are removed first when the input budget is exhausted, and output/tool budgets are reserved before input assembly.

A Context Segment MUST close only at a complete turn-group boundary. A turn group includes its user message, assistant tool requests, tool results, assistant response, Action proposal, user decision, and Host result. Topic changes, task completion, terminal Action state, long idle intervals, completed attachment processing, and token soft limits MAY close a Segment.

The package MUST NOT delete or rewrite original messages. Compression changes model input only. A summary and Working Ledger are derived data, not long-term Memory and not sources of business truth. Structured Host data and the Action Store remain authoritative.

Every derived artifact MUST include source ranges, schema and generator versions, validity state, and provenance references. Corrections and supersession records take priority over older summary claims. Attachment deletion, permission revocation, Memory deletion, Action-state changes, or source revision MUST invalidate or redact affected summaries, ledger entries, and indexes.

Asynchronous compaction MUST use source revisions and compare-and-swap activation. A stale compaction result cannot become active. `raw_trace` events are never Context sources and are excluded from summaries, the Working Ledger, and retrieval indexes, even when separate trace retention is enabled.

**Acceptance:** `lite`, `balanced`, and `durable` produce the same Context View schema; over-budget Conversations follow the active profile; failed summarization falls back to the `lite` source set with an explicit diagnostic; every summary can be rebuilt from original messages; Context Manifests explain selection, exclusion, token cost, truncation, and permission filtering; profile upgrades and downgrades preserve the raw Conversation and activate atomically.

### M9. Knowledge & Retrieval Pack

**Purpose:** provide governed access to external and application knowledge.

**Responsibilities:** web search adapters, URL reading, document extraction, host knowledge-base adapters, citations, freshness metadata, trust labels, call budgets, and source policies.

**Acceptance:** the package is disabled by default; externally derived claims include citations; private host data is not inserted into an external query without a separate permission and redaction; empty results, timeouts, and budget limits produce structured outcomes.

### M10. Memory Pack

**Purpose:** retain explicit, scoped information for future runs.

**Responsibilities:** create, view, edit, delete, export, provenance, visibility, scope, and revision history for Memory records.

**Acceptance:** model guesses, cancelled actions, and unverified facts are not retained; deleted records no longer enter context; retrieval is filtered by host authorization and scope; users can inspect what is remembered.

### M11. Action Workspace Pack

**Purpose:** standardize read-only, user-confirmed, and pre-approved automatic business changes while preserving Host authority.

```text
proposed -> policy_evaluating
policy_evaluating -> blocked | awaiting_confirmation | auto_applying
blocked -> policy_evaluating                         (explicit reauthorization or policy/target refresh)
awaiting_confirmation <-> editing
awaiting_confirmation -> applying -> applied
auto_applying -> applied
editing -> cancelled
awaiting_confirmation -> cancelled | expired
proposed | policy_evaluating | awaiting_confirmation | editing | failed | retrying -> blocked_plugin_disabled
applying | auto_applying -> failed
failed -> retrying -> policy_evaluating
applied -> undoing -> undone | undo_failed
blocked_plugin_disabled -> policy_evaluating      (compatible re-enable + revalidation)
blocked_plugin_disabled -> cancelled | archived   (manual resolution)
```

**Responsibilities:** typed proposals, execution-mode and allowlist policy evaluation, immutable policy decisions, schema-driven editing, Attachment source provenance and Promotion preview, confirmation, bounded automatic application, cancellation, plugin-disable blocking, conflict handling, idempotent application, result visibility, partial results, retry, archival, and optional undo.

**Acceptance:** the model can propose but cannot bypass execution policy or apply directly; `read_only` rejects write proposals, `confirm_each` always reaches `awaiting_confirmation`, and `auto_apply_allowlist` reaches `auto_applying` only after a positive reviewed policy decision. Both confirmed and automatic application recheck authorization, target version, bounds, and validation immediately before an idempotent Host transaction. Policy misses fall back to confirmation or blocked state. Auto-applied result cards remain visible and expose edit/undo only when supported. An Action derived from attachments preserves stable `source_attachment_refs`, page/region or processor provenance where applicable, and separately lists any `promoted_attachment_refs` before mandatory confirmation. Disabling a contributing plugin moves every non-terminal Pending Action that has not begun applying to `blocked_plugin_disabled` without cancelling or executing it. Compatible re-enable requires revalidation before returning to policy evaluation; permanent removal allows manual cancellation or archival. Applied history remains readable, and an Action already in `applying` or `auto_applying` records its eventual Host result rather than being silently interrupted.

### M12. Safety & Governance

**Purpose:** enforce the minimum security and observability baseline.

**Responsibilities:** permission classes, data scopes, execution modes, auto-apply allowlists, risk/confidence/impact/rate limits, forced-confirmation categories, sensitive-data redaction, timeouts, maximum tool calls, audit events, integration/plugin permission checks, Privacy Resource registry, export orchestration, deletion preview and confirmation, derived-artifact invalidation, retention visibility, and Privacy Job recovery.

**Acceptance:** minimum permission enforcement, typed Action routing, forced-confirmation boundaries, redaction, Privacy Center, and audit contracts cannot be disabled; `auto_apply_allowlist` cannot expand itself or override Manifest review; advanced quotas are configurable; every assistant-managed data category is registered or fails conformance; export and deletion jobs are scoped, idempotent, resumable, and report partial results; audit records preserve debugging metadata without storing credentials, raw private attachments, or unredacted context.

### M13. Developer Toolkit

**Purpose:** let contributors integrate, debug, and test without a live model or production data.

**Responsibilities:** Mock model server, stream inspector, context-profile simulator, Context Manifest/token inspector, tool playground, Host Data Tool catalog/transaction/conflict simulator, permission viewer, Privacy Resource/job simulator, Integration Generator, Manifest review report, generated adapter/fixture scaffolding, replay runner, plugin compatibility validator, fixed evaluation corpus, and failure simulation.

**Acceptance:** CI runs without external credentials; sanitized replay fixtures reproduce failed scoped streams without private payloads; the Integration Generator never activates writes and reports unresolved security or transaction semantics; inspectors and failure simulation cover model/Host/processor/search/ASR/data-transaction services, disconnect, timeout, malformed events, tool or parser failure, permission denial, stale versions, policy misses, renderer/plugin failure, attachment failure, and partial Privacy deletion.

### M14. Reference Integrations and Migration Proof

**Purpose:** prove that the public contracts are not tailored to one domain.

The repository SHOULD include domain-neutral examples for wellness logging, itinerary planning, and household finance. The examples collectively cover direct embed, declarative Manifest, generated integration, custom plugin paths, confirmed Actions, and reviewed allowlisted automatic Actions. One real or representative Host MUST integrate the Host Adapter, default UI, and at least one confirmed Action.

**Acceptance:** all examples use the same event, tool, Action, and renderer contracts; at least one confirmed and one reviewed allowlisted automatic business Action work without custom plugin code; no domain field is added to core schemas; renderer failure falls back safely; permission changes prevent confirmation or automatic application; the example suite runs with Mock model and Fake Host Adapter fixtures.

## Official capability packages

“Official” means maintained, tested, versioned, and compatible with the core. It does not mean enabled automatically.

| Package | Default state | MVP contents |
| --- | --- | --- |
| Essentials | enabled | date/time, calculator, unit conversion, formatting, text cleanup, bounded page context; no Host Data Write Tools |
| Multimodal Input | disabled | unified Attachment Tray/Asset/lifecycle, private upload and processing, Message renderers, Lightbox, explicit Host Promotion, persisted `voice_message` batch transcription, and editable `live_dictation` streaming transcription |
| Context Management | disabled | `balanced` and `durable` profiles, segmentation, ledger, summaries, retrieval, invalidation, rebuild, and Context Manifest; core always provides `lite` |
| Knowledge & Retrieval | disabled | web, URL, document, host knowledge, citations |
| Memory | disabled | explicit scoped Memory with user controls |
| Action Workspace | disabled | policy and execution layer for optional Host Data Write Tools and integration/plugin business Actions: `read_only`, default `confirm_each`, and bounded `auto_apply_allowlist` with typed Actions, policy evidence, idempotent Host application, results, and optional undo |
| Safety & Governance | minimum baseline required | permission enforcement, write blocking, redaction, Privacy Center inventory/export/deletion, derived-data invalidation, and audit; advanced limits are configurable |
| Developer Toolkit | development only | Mock services, inspectors, replay, validation, evaluation, and failure simulation |

## Host integration manifest and plugin lifecycle

### Host Integration Manifest

A `Level 1` integration is declarative. A `Level 2` Integration Generator produces the same format with `review_status: draft` and an unresolved-risk report.

```yaml
schema_version: "0.1"
application:
  id: org.example.sample-app
  conversation_mode: single
  context_profile: durable

context_sources:
  - id: current_record
    source: page_state
    fields: [record_id, selected_date]

host_data_tools:
  enabled: true
  operations: [create, update]
  entities:
    record:
      writable_fields: [title, amount, occurred_at]
      row_scope: current_actor
      optimistic_lock: version

tools:
  - id: list_records
    source: openapi
    operation_id: listRecords
    permission: sample.records.read
    side_effect: read

actions:
  - id: create_record
    source: openapi
    operation_id: createRecord
    permission: sample.records.write-proposal
    renderer: schema-form
    execution:
      risk: low
      default: confirm_each
      auto_apply_eligible: true
      idempotency: required
      compensation: delete_created_record

review_status: approved
```

The Manifest contains approved mappings, not arbitrary executable business code. Read tools and generic schema renderers MAY activate after validation. Host Data Write Tools remain disabled unless the Manifest explicitly enables an entity, operation, writable-field allowlist, row scope, concurrency strategy, and execution mode. Every write-proposal mapping requires explicit review of authorization, validation, idempotency, transaction, confirmation, privacy, and optional undo semantics. `auto_apply_eligible` is a separate reviewed declaration; it never follows automatically from discovering a POST, PATCH, DELETE, table, or repository operation.

### Custom Plugin Manifest

The minimum `Level 3` custom plugin manifest contains:

```json
{
  "schema_version": "0.1",
  "id": "org.example.sample-plugin",
  "name": "Sample Plugin",
  "version": "0.1.0",
  "protocol_range": ">=0.1.0 <0.2.0",
  "capabilities": ["sample.read", "sample.propose"],
  "permissions": ["host.sample.read", "host.sample.write-proposal"],
  "tools": ["sample.lookup", "sample.propose-update"],
  "actions": ["sample.update"],
  "renderers": ["sample.result", "sample.action"],
  "privacy_resources": ["sample.private-cache"],
  "configuration_schema": "schemas/sample-config.json",
  "migrations": []
}
```

### Lifecycle requirements

An Integration Manifest follows author/generate, review, validate, enable, revise, and disable states. A generated Manifest cannot leave `draft` until all blocking risks are resolved.

Custom Plugin lifecycle requirements:

1. Install through the Host build or package manager.
2. Register the manifest.
3. Validate protocol compatibility, dependencies, configuration, and permissions.
4. Run migration preflight when required.
5. Enable through Host configuration.
6. Disable without leaving callable tools or active renderers.
7. Upgrade only after compatibility and migration checks pass.
8. Roll back through the Host release system if deployment fails.

Plugins MUST fail closed. A missing permission, incompatible protocol range, invalid schema, or failed migration prevents activation.

When a plugin is disabled, every non-terminal Pending Action contributed by that plugin that has not begun applying enters `blocked_plugin_disabled`. The framework MUST NOT cancel or execute it automatically. Compatible re-enable triggers permission, payload, schema, version, and execution-policy revalidation before the Action returns to `policy_evaluating`. Permanent removal allows manual cancellation or archival. Applied Actions remain readable through stored data and a generic renderer.

## Frontend UX and accessibility

The default UI MUST follow the design contract in [DESIGN.md](../DESIGN.md).

### Reasoning disclosure levels

| Level | Visible information |
| --- | --- |
| `hidden` | No reasoning or activity disclosure surface. |
| `status` | Short stage labels such as “Analyzing attachment”. |
| `contextual` | The authorized attachment, entity, or scope being analyzed. |
| `activity` | User-facing tool names, completion summaries, citations, and elapsed time. |
| `developer` | Redacted tool inputs and outputs, event sequence, context composition, token use, model metadata, and correlation IDs. |
| `raw_trace` | The complete provider reasoning trace exactly as returned by a trace-capable model adapter. |

The Host sets the maximum permitted level; an authorized viewer MAY select any level at or below that maximum. The default level is `status`. `raw_trace` is opt-in, visually marked as sensitive provider output, and unavailable when the adapter declares `none` or `summary` reasoning visibility.

Minimum behavior:

- preserve user drafts across recoverable failures;
- keep one `AttachmentTray` inside the Composer above the text field, append repeated selections by default, show the configured limit before selection/send, preserve stable order, and expose per-item progress, retry, removal, and reorder controls;
- distinguish history loading, sending, streaming, tool execution, upload, transcription, and action application;
- auto-follow streaming only while the user remains at the bottom;
- preserve the reading anchor when older history is prepended;
- derive localized time dividers with a five-minute default inactivity threshold, recomputing them after pagination without changing Message order;
- keep `voice_message` playback/transcription states separate from `live_dictation` recording, partial-text, and editable-draft states;
- render sent attachments inside their parent Message with one delivery/time/retry/privacy group; use `AttachmentGrid`, file cards, and an authorized Lightbox consistently; dead taps and silent attachment failure are non-conformant;
- show attachment-derived Action provenance and Promotion targets before confirmation;
- honor the configured disclosure level without inventing unavailable reasoning data;
- show user-facing tool outcomes rather than internal function names;
- make proposed actions editable before confirmation;
- expose the active execution mode in settings and mark every Action result as confirmed, automatically applied, blocked, or read-only; an auto-applied result remains visible with policy reason and edit/undo only when supported;
- downgrade an ineligible automatic Action to `awaiting_confirmation` or `blocked` with an explanation rather than treating it as an execution error;
- render `blocked_plugin_disabled` Actions as readable but non-confirmable, with compatible re-enable, manual cancel, and archival guidance;
- provide a unified Privacy Center with category inventory, retention owner, export, deletion preview, destructive confirmation, progress, partial-result, retry, and unresolved-processor states;
- provide accessible error, retry, cancellation, and permission-denied states;
- meet WCAG 2.2 AA for the default web kit;
- support reduced motion and 44 px minimum touch targets;
- support mobile widths from 360 px and embedded panels from 320 px.

## Context, memory, and data authority

The framework distinguishes four information classes:

| Class | Authority | Retention rule |
| --- | --- | --- |
| Structured host data | host application | controlled by the host business and retention policy |
| Context View | per-Run compiled input | immutable for its Run; reproducible from its Manifest where sources remain authorized |
| Context summary | derived cache | rebuildable; never replaces or deletes original messages |
| Memory | explicit persistent information | scoped, inspectable, editable, deletable, and authorized |

Cancelled actions and unverified model statements MUST NOT become Memory. Context summaries MUST NOT be used to repair or override structured host facts.

## Privacy Center and data lifecycle

Privacy Center is part of the mandatory Safety & Governance baseline. It presents one authorized inventory across core modules, official packages, Host Integration Manifests, and optional plugins.

Minimum resource categories are:

| Category | Examples | Default control |
| --- | --- | --- |
| Conversations and Messages | user text, assistant output, message timing | view, export, delete by authorized scope |
| Attachments | images, files, persisted voice-message audio | preview metadata, export, delete/revoke |
| Transcripts | automatic and user-corrected voice-message revisions | view provenance, export, delete with source policy |
| Memory | explicit preferences and durable constraints | view, edit, export, delete |
| Reasoning traces | persisted `raw_trace`, when separately enabled | sensitive warning, export, delete |
| Context artifacts | Context Views where retained, Manifests, summaries, Working Ledger, retrieval indexes | inspect metadata; rebuild or invalidate rather than treat as source truth |
| Pending Actions | proposed, blocked, cancelled, archived, or failed Actions | view, cancel/archive where allowed; deletion follows audit policy |
| Integration/plugin data | declared extension-owned storage | export/delete through registered handlers |
| Audit and applied Host records | minimum security trail and committed business objects | disclose retention and owner; redirect Host-owned deletion to Host controls |

Privacy Job lifecycle is:

```text
requested -> previewing -> awaiting_confirmation -> running
running -> completed | partial | failed | cancelled
partial | failed -> retrying -> running
```

An export MUST contain a machine-readable manifest describing categories, scopes, source IDs, schema versions, omitted resources, and retention restrictions. A deletion preview MUST identify direct sources, affected derived artifacts, Host-owned records, externally processed data, legal/security retention, and irreversible effects before confirmation.

Deletion is source-aware. Removing a Message, attachment, transcript, Memory record, or retained trace MUST remove or invalidate dependent summaries, Working Ledger entries, retrieval indexes, Context Manifests, caches, and generic renderer data. Deletion and invalidation are idempotent and resumable. Search and authorization filtering occur before results are returned, so deleted or revoked data cannot re-enter a Context View during cleanup.

Privacy Center does not silently delete committed Host business records. Applied Actions link to the Host-owned object and its deletion controls. Audit records MAY retain a minimal tombstone when required for security, abuse prevention, or law; the UI and export disclose the reason, fields retained, owner, and retention period.

Every integration or plugin that persists data MUST register its Privacy Resources and handlers before activation. Disablement or package removal cannot orphan user data: export and deletion handlers remain available through a stable Host boundary or migration package until the declared retention period ends.

Privacy Jobs are scoped to the authenticated actor and Host scope, require destructive confirmation for deletion, emit `privacy.job.updated`, preserve item-level results, and never report full success when any registered processor is unresolved. External processors are reported individually; the framework cannot claim their deletion completed without processor confirmation.

## Security and privacy

### Permission classes

- `none`: deterministic computation without protected data;
- `read`: host or page data access;
- `write-proposal`: creation of an uncommitted Action;
- `external-read`: outbound access to a third-party source;
- `dangerous`: high-risk capability, unavailable in the MVP.

### Required controls

- Protected tools MUST declare permissions and data scope.
- Host Data Write Tools MUST be disabled and absent from model manifests by default. Enabling requires reviewed entity/operation/field/row-scope/concurrency/execution policy; arbitrary SQL, schema browsing, credentials, unrestricted predicates, and undeclared database access are forbidden.
- The Host data adapter owns parameterized repository/API execution, authorization, transaction, conflict detection, and result serialization. Tool visibility is computed before model invocation for the current actor and scope.
- External calls MUST declare what data leaves the host boundary.
- Sensitive fields MUST be redacted from logs and developer fixtures.
- Provider credentials MUST remain server-side.
- Attachment access MUST be private and host-authorized.
- Attachment limits and processor capabilities MUST be disclosed before selection or send; no layer may silently truncate, drop, or reinterpret selected files.
- Persisted Messages use stable Attachment IDs and private authorized variants; public asset URLs, `blob:` URLs, data URLs, and array indexes are not durable history references.
- Attachment-derived facts and Action fields retain processor/version plus source Attachment/page/region provenance. Promotion into a Host business resource requires explicit Action confirmation.
- Every Action execution mode MUST revalidate authorization, payload integrity, current target version, policy bounds, and idempotency immediately before Host application.
- `auto_apply_allowlist` is deny-by-default and cannot be selected by the model. Only approved Manifest policy may allow a low-risk bounded Action type. Policy decisions record rule/version, actor/scope, risk, confidence, bounds, reason, and outcome.
- Payment, transfer, and other `dangerous` capabilities remain unavailable and blocked in the MVP. Supported Actions for delete, external communication, private-data sharing, account/permission change, bulk or irreversible mutation, Attachment Promotion, ambiguous targets, low-confidence OCR/ASR, and operations without approved compensation require confirmation regardless of execution mode. Privacy deletion uses the separate Privacy Job destructive-confirmation flow.
- Every committed Action MUST have an idempotency key and audit record.
- Partial failure MUST identify successful, failed, and retryable items.
- Live-dictation audio is ephemeral by default and is not retained as a Message. Voice-message audio is persisted as private user content under explicit Host retention and deletion policy.
- `raw_trace` requires explicit Host policy and viewer authorization and is always excluded from normal logs, Memory, Context Summary, the Working Ledger, and retrieval indexes. Separate Host trace retention makes it eligible only for authorized display, export, and deletion.
- Raw-trace exports MUST be labelled as sensitive provider reasoning content.
- Generated Host Integration Manifests remain `draft` until a reviewer resolves permission, privacy, idempotency, transaction, confirmation, cascading-delete, and undo risks. Runtime discovery MUST NOT activate undeclared Host operations.
- Privacy Resource inventory and jobs require actor plus Host-scope authorization. Exports use private authenticated delivery; deletion cannot report completion until every registered processor reports a terminal result or is explicitly disclosed as unresolved.

## Versioning and compatibility

- Core packages and official capability packages use Semantic Versioning.
- The event protocol has its own schema version.
- A plugin declares a supported protocol range.
- Additive optional fields MAY be introduced in a compatible minor release.
- Removing a field, changing its meaning, or changing required state transitions requires a new protocol major version.
- Clients MUST tolerate unknown event types and optional fields.
- Stored Actions, Action Policy Decisions, summaries, Host Integration Manifests, execution policies, and plugin configuration MUST retain the schema version used to create them.
- Migration code MUST be deterministic, testable, and reversible through release rollback or explicit compensating migration.

## Parallel implementation plan

### Wave 0 — Contract foundation

Parallel work is limited to M0, repository/package skeleton, code generation, CI, and fixture infrastructure.

M0 freezes the minimum `0.1` contracts for Conversation/Run/Message and ordering/time, events/errors, Attachment/processing/voice, Tool and Host Data Tool catalog, Host Adapter, Integration/Plugin manifests, Action/Policy Decision/execution modes, Context/Profile/Manifest, Memory, Citation, Privacy Resource/Job, permissions, audit, and versioning. It also publishes generated TypeScript/Python types, OpenAPI/event documentation, valid/invalid golden fixtures, a replay server, schema validators, and compatibility-change policy.

**Exit gate:** C0 protocol/schema conformance passes; every downstream lane can compile and run against generated types plus fakes; breaking fields or state transitions require compatibility review.

### Wave 1 — Platform kernel

The following lanes run in parallel against M0:

| Lane | Modules | Deliverables |
| --- | --- | --- |
| Runtime | M1 | Conversation/Run lifecycle, persistence, provider adapters, ordered/resumable events, cancellation/reconciliation, usage |
| Host boundary | M2 | Actor/scope/page context, permission decisions, Host Data Tool catalog, transactional Action application, refresh |
| Tool runtime | M3 | Registry, validation, visibility, Host Data Write Tool generator, timeout/retry, typed-Action routing |
| Integration/plugin | M4 | Manifest validation, review gates, capability/renderer/privacy registration, enable/disable, migration preflight |
| Headless state | M5 | Replay reducers for Conversation, Message, time, Attachment, Voice, Reasoning, Tool, Action, Privacy, Context |
| Safety/governance | M12 | Permissions, execution policy, forced confirmation, redaction, audit, quotas, Privacy registry/jobs |
| Developer tooling | M13 | Mock model/Host/processors, fixtures, inspectors, Integration Generator, Data Tool simulator, replay/failure injection |

**Exit gate:** C1–C4 and C7a pass independently; M13 Mock/replay/schema-drift tooling passes its Wave 1 C8 subset without live provider credentials or a real Host. Every lane publishes public fakes/fixtures and imports no other lane’s storage or UI internals.

### Wave 2 — Experience and capability packages

The following lanes run in parallel on Wave 1 public contracts or fakes:

| Lane | Modules | Deliverables |
| --- | --- | --- |
| Default experience | M6 | Shell/Conversation management/Thread/Composer, message time, Attachment UI/Lightbox, Voice UI, Reasoning, Tool/Citation, Action modes, Privacy Center, accessibility/responsive states |
| Multimodal | M7 | Attachment Asset lifecycle, private variants, processors, Run gates, Promotion, voice_message/live_dictation adapters |
| Context | M8 | `lite`/`balanced`/`durable`, segmentation, ledger, summaries, retrieval, invalidation, rebuild, Context Manifest |
| Knowledge | M9 | Search/URL/document/Host knowledge adapters, citations, freshness/trust, external permission and budgets |
| Memory | M10 | Explicit scoped Memory CRUD/export/provenance/authorization |
| Action workspace | M11 | `read_only`/`confirm_each`/`auto_apply_allowlist`, policy decisions, confirmed/automatic application, conflict, partial result, undo, plugin blocking |

**Exit gate:** C5, C6, C7b, and full C8 pass using mocks; component accessibility and mobile/desktop visual fixtures pass; no capability requires a live model, external search provider, database, or production user to prove its state contract.

### Wave 3 — Reference integration and cross-module proof

M14 integrates one representative real Host plus domain-neutral wellness, itinerary, and household-finance fixtures. Collectively they prove all four Host integration levels, single/multiple Conversation modes, all three Context Profiles, both voice modes, Attachment processing/Promotion, Host Data Write Tools default-off and scoped enablement, confirmed/automatic Action paths, Reasoning Disclosure, retrieval citations, Memory, plugin disablement, Privacy export/deletion, interruption recovery, idempotency, and domain portability.

**Exit gate:** C9 end-to-end/portability suite passes; at least one real Host removes a duplicated assistant path and uses framework public modules rather than a parallel demo.

### Release gate

Release requires every MVP acceptance criterion plus protocol/migration compatibility, dependency/license, performance, security/Host Data Tool, privacy/data-lifecycle, accessibility, responsive/visual, recovery/observability, and public-documentation reviews. Release evidence records versions, fixtures, test reports, known gaps, and rollback instructions.

### Parallel work rules

- M0 changes require compatibility review and regenerated fixtures/types before downstream adoption.
- Every module publishes a fake, fixture, stub, or simulator that matches the public contract.
- Modules depend on public contracts, not another module’s database, cache, framework-specific component state, or private helper.
- Domain-specific schemas and exceptions remain in Host Integration Manifests or optional Domain Plugins, never in Core contracts.
- Cross-cutting Safety/Privacy/Accessibility requirements are verified inside each owning lane and again in cross-module suites; they are not deferred to release week.
- A Wave advances only when its Exit Gate passes. Calendar completion or merged code does not substitute for evidence.

## Conformance

Conformance is evidence-based and modular. Passing one module suite permits a claim for that module only; claiming Framed Assistant MVP conformance requires C0–C9 plus all MVP acceptance criteria. Every report identifies package/protocol/schema versions, fixture revision, configuration/profile, passed/failed/skipped cases, known gaps, and reproducible artifacts.

### C0. Protocol and schema conformance

- validate every public schema with valid, boundary, unknown-optional-field, and invalid fixtures;
- generate TypeScript/Python/OpenAPI artifacts reproducibly and detect drift from canonical JSON Schemas;
- replay every event type, event scope, and content part, including unknown events, duplicate IDs, per-scope sequence gaps, version mismatch, and generic-renderer fallback;
- verify stored-object schema versions and deterministic forward/rollback or compensating migrations;
- verify Attachment, Voice, Reasoning, Action Policy, Host Data Tool, Context, Memory, Privacy, Integration, Plugin, Error, and Audit contracts before Wave 0 exit.

### C1. Runtime and provider conformance

- persist user input before provider invocation and prove empty/premature streams cannot complete successfully;
- cover Run lifecycle, cancellation, stop/regenerate, timeout, provider error mapping, usage, interruption, resume by `after_seq`, and reconciliation;
- verify non-idempotent work is never replayed automatically and provider reasoning capability is reported accurately;
- run OpenAI-compatible and Mock adapters against the same scripted text/tool/reasoning/error fixtures;
- verify Conversation `single`/`multiple` topology uses the same Runtime and storage contracts.

### C2. Host boundary, Tool, and Host Data Tool conformance

- exercise Host Adapter allow/deny/timeout/conflict/refresh and actor/tenant/Conversation-scope isolation;
- validate Tool input/output, permission, visibility, cancellation, timeout, safe retry, redaction, and audit behavior;
- prove Host Data Write Tools are absent by default and enabling one entity/operation exposes only reviewed fields, validation, row scope, concurrency, limits, and execution mode;
- verify create, update, upsert, delete, link, and unlink independently remain default-off and retain their operation-specific scope, concurrency, forced-confirmation, and compensation requirements when enabled;
- reject raw SQL, schema/table browsing, credentials, unrestricted predicates, undeclared fields, and out-of-scope rows;
- route every write call through a typed Action and parameterized Host transaction; stale versions produce conflict without last-write-wins mutation.

### C3. Host Integration and Plugin conformance

- cover direct embed, declarative Manifest, generated Manifest review, and custom Domain Plugin paths;
- verify Integration Generator read scaffolding, write-proposal and auto-apply eligibility review gates, unresolved-risk reporting, and zero activation before review;
- validate Manifest schema versions, plugin protocol ranges, dependencies, configuration, capability/permission declarations, Privacy Resources, migrations, renderer registration, and fail-closed activation;
- disable integrations/plugins without leaving callable tools or orphaning export/delete handlers; historical rendering remains available through generic fallback;
- verify `blocked_plugin_disabled` Actions, compatible re-enable revalidation, permanent removal cancellation/archival, and applied-history readability.

### C4. Headless state conformance

- replay every event into serializable reducers for Conversation, Message/time, Attachment, Voice, Reasoning, Tool/Citation, Action/Policy, Context, and Privacy;
- cover per-scope duplicates, out-of-order/gap detection, optimistic/local IDs, persisted reconciliation, cache restore, and unknown states;
- preserve draft text/attachments, reading anchors, bottom-follow ownership, item order, retry state, and per-Message grouping through failure and pagination;
- verify state has no visual-framework or Host-business dependency and can run entirely against C0 fixtures.

### C5. Default UI and Multimodal conformance

- expose independently runnable fixture groups for Shell/Conversation management/Thread/Composer, chronology, Attachment, Voice, Reasoning/Tool/Citation, Action modes, Privacy Center, accessibility, responsive, and recovery behavior rather than one monolithic visual suite;
- component, keyboard, focus, screen-reader, reduced-motion, contrast, 320/360 px, desktop, safe-area, and visual-regression fixtures;
- five-minute message-time grouping, cross-date/timezone labels, pagination recomputation, exact-time detail, and in-place status updates;
- Attachment Asset/Draft/Message-Part lifecycle, Tray placement/append/limit/reorder, per-item states/retry, one-Message grouping, grids, file cards, Lightbox, tombstones, private variants, Run gates, provenance, Promotion, and privacy invalidation;
- voice-message and live-dictation modes across batch/streaming and device/server ASR, transcript revision, privacy, failure, and fallback disclosure;
- six Reasoning Disclosure levels, Tool/Citation UI, confirmed/automatic/blocked Action cards, Host Data Tool settings, Privacy Center, and recovery states.

### C6. Context, Retrieval, and Memory conformance

- `lite`/`balanced`/`durable` compilation, profile switching, atomic activation, Token budgets, Context Manifest, and raw-history preservation;
- complete-turn segmentation, summary trigger, correction/supersession, async compaction race, compare-and-swap, invalidation, permission filtering, provenance, fallback, and rebuild;
- hybrid historical retrieval, source-span recall, citations, freshness/trust, external-data permission/redaction, empty results, timeout, and call budgets;
- Memory create/view/edit/delete/export, conversation/app/user scopes, provenance, authorization, and exclusion of guesses/cancelled Actions;
- ensure Attachment deletion, permission revocation, Memory deletion, and Action changes correctly affect derived context while `raw_trace` remains excluded regardless of separate retention policy.

### C7. Action, Safety, and Privacy conformance

#### C7a. Safety and Privacy baseline — Wave 1

- enforce permission/scope decisions, redaction, quotas, maximum tool calls, audit, and sensitive raw-trace/attachment handling without M11;
- prove execution policy is deny-by-default, cannot be model-selected or self-expanded, routes every supported Host business-mutation proposal toward confirmation or a reviewed allowlist decision, and blocks unsupported or `dangerous` proposals;
- prove payment, transfer, and other `dangerous` capabilities remain blocked even when confirmation is offered; test every supported forced-confirmation category independently: delete, external communication, private sharing, account/permission change, bulk/irreversible mutation, Attachment Promotion, ambiguity, low-confidence OCR/ASR, and missing compensation; test Privacy deletion through its separate destructive-confirmation contract;
- register Privacy Resources and validate scoped inventory, private export envelope, deletion preview/confirmation contract, Host-owned handoff metadata, retention disclosure, and unresolved-processor truthfulness using fake jobs;
- publish M12 policy, audit, Privacy, and failure-injection fakes required by Wave 2.

#### C7b. Action Workspace integration — Wave 2

- cover `read_only`, default `confirm_each`, and `auto_apply_allowlist` state paths, immutable policy evidence, allowlist denial, fallback, reauthorization, bounds, target version, idempotency, transaction, result visibility, partial failure, retry, and undo;
- integrate full Privacy Jobs: derived cascade, partial/retry, plugin removal, external-processor confirmation, audit tombstone, and UI-visible terminal outcomes;
- inject permission, target-version, policy, plugin, and data changes between proposal, policy evaluation, confirmation/auto-apply, and Host commit;
- verify confirmed and automatic Actions use the same Host transaction boundary and differ only in approved confirmation policy;
- verify plugin disablement, `blocked_plugin_disabled`, compatible re-enable revalidation, permanent archival/cancellation, and in-flight final-result recording.

### C8. Developer tooling and observability conformance

- run Mock model/Host/processor/search/ASR/data-transaction services without external credentials;
- validate stream, Context/Token, Tool, Permission, Data Tool, Privacy, Integration Generator, compatibility, and replay inspectors against golden fixtures;
- simulate disconnect, malformed event, timeout, provider/tool/parser/renderer/plugin failure, permission denial, stale version, policy miss, partial deletion, and recovery;
- produce sanitized replay bundles that preserve correlation, timing, policy, and provenance without secrets or private payloads;
- fail CI when schemas, generated types, required fixtures, public docs, or conformance reports drift.

### C9. End-to-end and portability conformance

- run one representative real Host plus wellness, itinerary, and household-finance fixtures through the same public contracts;
- prove Level 0–3 integration, single/multiple Conversation, all Context Profiles, both Voice modes, Attachment/Promotion, Retrieval/Memory, Host Data Write Tools, confirmed/automatic Actions, Reasoning, plugin disablement, and Privacy Center;
- cover cold start, long history, offline/interruption recovery, permission change, optimistic conflict, duplicate request, partial result, deletion, migration, and rollback;
- confirm no domain field enters Core schemas and at least one real Host replaces a duplicated assistant path rather than running a side demo;
- capture release-ready performance, security, privacy, accessibility, visual, migration, and observability evidence.

### Cross-module scenarios

| Scenario | Modules | Required outcome |
| --- | --- | --- |
| Text conversation | M0, M1, M5, M6 | persisted input, streamed output, completed run |
| Read-only tool | M0, M1, M3, M6, M12 | visible lifecycle, authorized execution, validated output |
| Multi-attachment composition | M0, M5, M6, M7 | three images and one file append in one Tray above text, preserve order, support removal/reorder, and send as one Message |
| Attachment processing failure | M1, M5, M6, M7, M12 | draft/upload is not lost, upload/parse/Run failures remain distinct, required failure pauses for retry/remove-and-continue/cancel |
| Attachment history and gallery | M0, M5, M6, M7, M12 | stable private IDs survive pagination, thumbnails open the authorized Message gallery, unavailable sources show labelled tombstones |
| Attachment-derived Action | M0, M7, M11, M12 | source file/page/region provenance and Promotion targets are visible before confirmation; Host resource is created only after confirmation |
| Voice message | M0, M1, M5, M6, M7, M12 | private playable audio persists, batch transcript completes before assistant consumption, failure remains retryable |
| Live dictation | M5, M6, M7, M12 | on-device or disclosed server streaming fills an editable draft, never auto-sends, and retains no audio Message |
| Message time grouping | M0, M5, M6 | sequence order remains stable, continuous messages share one time anchor, five-minute/date boundaries create localized dividers, pagination recomputes without jump |
| Long single Conversation | M1, M8, M13 | selected profile compiles a bounded Context View, original history remains unchanged, Manifest explains inclusion and exclusion |
| Multiple Conversation continuity | M1, M5, M8, M10, M12 | switching Conversations isolates local context; authorized cross-conversation Memory and on-demand history retrieval return provenance without leaking other scopes |
| Reasoning disclosure lifecycle | M0, M1, M5, M6, M12 | provider none/summary/trace capability, Host/viewer level, raw_trace unavailable or visible state, Privacy export/delete, and Context/Memory exclusion stay consistent |
| Read-only execution mode | M2, M3, M11, M12 | write proposal is rejected or converted to non-executable guidance; no Host mutation occurs |
| Disabled Host Data Write Tools | M2, M3, M4, M12 | model manifest contains no database write capability and no Host mutation path is reachable |
| Enabled schema-bound create/update | M2, M3, M4, M11, M12 | only reviewed entity/operation/fields/scope are visible, call becomes typed Action, Host transaction applies under execution policy |
| Host data conflict | M2, M3, M11, M12 | stale target version blocks mutation, reports conflict, and offers refresh/rebase rather than last-write-wins |
| Confirmed write | M0, M2, M11, M12 | proposal, confirmation, host application, idempotency, audit |
| Allowlisted automatic write | M0, M2, M4, M11, M12 | approved low-risk Action records policy evidence, revalidates, applies idempotently, shows result, and exposes undo when declared |
| Auto-apply policy miss | M2, M4, M11, M12 | ambiguous, over-limit, low-confidence, unauthorized, or non-allowlisted Action falls back to confirmation or blocked without optimistic mutation |
| Disabled plugin | M3, M4, M6, M12 | no callable tool, fail-closed permission state, safe renderer behavior, actionable diagnostic |
| Disabled plugin with Pending Action | M4, M11, M12 | Action becomes `blocked_plugin_disabled`, never auto-cancels or executes, and requires revalidation after compatible re-enable |
| Config-only application | M0, M2, M3, M4, M13 | approved Manifest supplies a read tool plus confirmed or allowlisted automatic Action without custom plugin code |
| External retrieval | M6, M9, M12 | citation, freshness, permission, and budget enforcement |
| Deleted Memory | M8, M10, M13 | record no longer enters context; audit remains |
| Unified privacy deletion | M0, M4, M6, M8, M10, M12, M13 | source data and registered derivatives are removed or invalidated, Host-owned records are handed off, partial processors remain visible and retryable |
| Version migration and rollback | M0, M1, M4, M8, M11, M12, M13 | protocol/plugin/Manifest/stored Action/Context/PrivacyJob fixtures migrate deterministically, remain readable, and recover through rollback or compensating migration |
| Domain portability | M0, M4, M11, M14 | three examples introduce no domain fields into core |

## MVP acceptance criteria

The MVP is complete when:

- [ ] M0 schemas are frozen at `0.1` and the conformance command passes.
- [ ] M1-M14 satisfy their module acceptance requirements.
- [ ] A representative host embeds the default UI through a real Host Adapter.
- [ ] Text, multi-image/file Attachment Tray, private upload/processing/retry, one-Message rendering, image Lightbox, file cards, explicit Attachment Promotion, persisted voice-message with backend transcript, and live editable dictation flows work.
- [ ] Streaming Markdown, all six disclosure levels, tool activity, citations, and Action cards render through public contracts.
- [ ] A `Level 1` Host Integration Manifest contributes a tool plus confirmed and allowlisted automatic Actions without custom plugin code.
- [ ] Host Data Write Tools are absent by default; an approved Manifest can enable scoped create/update/upsert/delete/link/unlink tools without exposing raw SQL or unrestricted database access.
- [ ] A `Level 2` generated Manifest reports unresolved risks and cannot activate writes before review.
- [ ] A sample `Level 3` Domain Plugin contributes a custom renderer or business handler without modifying core.
- [ ] Every Host business mutation passes through Action Workspace and Host execution policy; `confirm_each` is the default, and only reviewed low-risk allowlisted Actions can use automatic application. Privacy deletion passes through the separate mandatory Privacy Job confirmation and policy flow.
- [ ] Context Management proves summary rebuild and unchanged original history.
- [ ] The same Runtime supports `single` and `multiple` Conversation modes, and Context Management supports `lite`, `balanced`, and `durable` profiles through one compiler contract.
- [ ] Stream interruption, upload failure, permission denial, provider failure, renderer failure, and partial Action failure have tested recovery paths.
- [ ] Official packages can be enabled or disabled according to their policy.
- [ ] Privacy Center inventories all registered assistant data, exports it with a manifest, previews deletion impact, and completes or truthfully reports partial deletion with derived-data invalidation.
- [ ] CI runs conformance and end-to-end Mock scenarios without external credentials.
- [ ] Direct-embed, Integration Manifest, Integration Generator, custom-plugin, UI, Privacy Center, testing, security, and migration documentation is published.

## Deferred work

The following work is intentionally deferred beyond the MVP:

- additional official UI kits for React, SwiftUI, and other frameworks beyond the MVP Vue 3 reference client;
- vector database and embedding-provider standardization;
- signed plugin distribution and remote update infrastructure;
- cross-application Memory federation;
- multi-agent orchestration;
- autonomous background tasks and proactive notifications;
- organization-wide approval workflows for high-risk capabilities.
