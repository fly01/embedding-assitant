# Framed Assistant MVP Specification

## Status

- Version: `0.1.0-draft`
- Status: draft implementation baseline
- Last updated: 2026-08-21
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
4. Support progressive adoption of image, two-mode voice input, file, tool, retrieval, memory, and confirmed-action capabilities.
5. Let hosts add domain tools, context providers, actions, and renderers through a declarative Integration Manifest, a generated integration, or an optional custom plugin without modifying the core runtime.
6. Keep business data access and final writes under host-application control.
7. Preserve original conversation records when optional context summarization is enabled.
8. Allow modules to be implemented and tested independently against shared fixtures.
9. Support configurable single- or multi-conversation topology and configurable context profiles without creating separate runtimes.
10. Allow a standard CRUD-style application to integrate without hand-writing a Domain Plugin.

## Non-goals

The MVP does not include:

- an online third-party plugin marketplace;
- arbitrary plugin code downloaded at runtime;
- production-runtime scanning that automatically discovers and activates undeclared Host APIs or write operations;
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
| Action | A typed proposal for a host-side business change. An action is not committed until the user confirms it and the host applies it. |
| Capability package | An officially maintained, versioned package that applications explicitly enable, except for the required safety baseline. |
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
- The host MUST authorize every protected read, external request, and proposed write.
- The host MUST validate permissions and action payloads again at confirmation time.
- The host MUST execute committed writes transactionally or return a structured failure.

### Progressive adoption

A host MAY adopt the framework in stages:

1. text conversation with the default assistant shell;
2. Host Adapter and deterministic Essentials tools;
3. image, voice, and file input;
4. configurable reasoning disclosure and visible tool activity;
5. Context Management or Knowledge & Retrieval;
6. Action Workspace and declarative, generated, or custom domain integration;
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

The Integration Generator runs only during development or build workflows. It MAY propose read tools and write-proposal Actions, but it MUST NOT activate write operations automatically. Unresolved permissions, idempotency, transaction, cascading-delete, privacy, confirmation, or undo semantics fail closed and require human review.

### Core entities

| Entity | Purpose | Required relationships |
| --- | --- | --- |
| `Conversation` | Host-scoped conversation container | actor, host scope, protocol version |
| `Message` | Immutable user, assistant, or tool content | conversation, role, sequence, content parts, created/visible/completed/edited timing |
| `Run` | Execution lifecycle for one user turn | input message, event sequence, status, usage |
| `Attachment` | Controlled image, audio, or file metadata | owner, media type, processing state, private locator |
| `ToolInvocation` | Typed tool request and result | run, tool version, permission decision, audit reference |
| `PendingAction` | Uncommitted host-side change proposal | schema version, payload, state, idempotency key |
| `ContextSegment` | Internal compaction and retrieval unit | complete turn groups, source range, closure reason |
| `SummarySegment` | Rebuildable context summary | source message range, summary version, validity state |
| `WorkingLedger` | Rebuildable current task state | goals, constraints, corrections, open threads, references |
| `ContextView` | Immutable per-Run model input | profile, permission snapshot, ordered context blocks |
| `ContextManifest` | Context selection evidence | block sources, priorities, token cost, exclusions |
| `MemoryRecord` | Explicit long-term information | provenance, scope, visibility, revision history |
| `AuditEvent` | Security and debugging evidence | actor, operation, decision, redaction metadata |
| `HostIntegrationState` | Active declarative/generated integration | Manifest version, review status, unresolved risks, adapter bindings |
| `PluginState` | Installed plugin activation state | plugin version, contract range, configuration, migration state |

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
  seq: number;
  conversation_id: string;
  run_id: string;
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
    | "attachment.updated"
    | "tool.requested"
    | "tool.started"
    | "tool.completed"
    | "tool.failed"
    | "action.proposed"
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

- `seq` MUST increase monotonically within a run.
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
- `GET /v1/assistant/conversations/{conversation_id}`
- `GET /v1/assistant/conversations/{conversation_id}/messages?before=<message_id>&limit=<n>`
- `POST /v1/assistant/conversations/{conversation_id}/runs`
- `GET /v1/assistant/runs/{run_id}/events?after_seq=<seq>`
- `POST /v1/assistant/runs/{run_id}/cancel`
- `POST /v1/assistant/attachments`
- `PATCH /v1/assistant/actions/{action_id}`
- `POST /v1/assistant/actions/{action_id}/confirm`
- `POST /v1/assistant/actions/{action_id}/cancel`
- `POST /v1/assistant/actions/{action_id}/undo`
- `GET /v1/assistant/capabilities`

The reference implementation uses Server-Sent Events for run events. A run request MUST persist the user message before model execution and return `run_id` plus the latest sequence number. Clients resume with `after_seq`.

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

**Acceptance:** event replay reconstructs message, tool, citation, and action state; invalid fixtures fail with actionable diagnostics; module IDs and public fields are versioned.

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
  authorize(request: PermissionRequest): Promise<PermissionDecision>;
  applyAction(action: ConfirmedAction): Promise<ActionApplyResult>;
  refreshData?(result: ActionApplyResult): Promise<void>;
}
```

**Acceptance:** missing capabilities are reported as disabled; the Host supplies a stable Conversation scope; denied permissions produce structured results; page context has a field allowlist and size budget; action application and refresh are explicit, testable callbacks; a `Level 1` application can implement the boundary through an approved Host Integration Manifest without custom Domain Plugin code.

### M3. Tool Runtime and Essentials Pack

**Purpose:** register, discover, validate, authorize, execute, and audit typed tools.

```ts
interface ToolManifest {
  name: string;
  version: string;
  input_schema: object;
  output_schema: object;
  side_effect: "none" | "read" | "write-proposal" | "external-read" | "dangerous";
  permissions: string[];
  timeout_ms: number;
  retry: { max_attempts: number };
  confirmation: "none" | "explicit" | "typed" | "host-only";
  idempotency: "not-applicable" | "run-scoped" | "host-required";
  ui_renderer_key?: string;
  redaction: RedactionPolicy;
}
```

Essentials includes date/time/time-zone operations, a calculator, unit conversion, number and currency formatting, text cleanup, and bounded host page context. Currency exchange requires a caller-supplied rate; live rates belong to retrieval or a host plugin.

**Acceptance:** invalid input never executes; invalid output becomes a typed tool failure; automatic retry is limited to deterministic or read-only operations; default tools do not write business data or access the network.

### M4. Integration and Plugin System

**Purpose:** register declarative or generated Host integrations and optional executable Domain Plugins without modifying core modules.

Custom Domain Plugins are optional and are installed at release time through the Host build or package manager. Installed plugins MAY be enabled or disabled at runtime through Host configuration. The MVP MUST NOT download or execute arbitrary remote plugin code.

**Responsibilities:** Integration Manifest and Plugin Manifest validation, protocol compatibility, dependency checks, review state, unresolved-risk gates, permission declarations, configuration schema, generic and custom renderer registration, migration preflight, enable/disable state, and fail-closed activation.

**Acceptance:** draft or unresolved Integration Manifests do not activate write mappings; incompatible plugins do not activate; disabled plugins expose no new tools or Actions; a renderer failure uses a safe generic renderer; upgrade preflight leaves the previously deployed version active on failure; historical content remains readable without an active custom renderer.

### M5. Frontend Headless SDK

**Purpose:** provide reusable frontend behavior without imposing a visual design.

**Responsibilities:** conversation state, event replay, sequence-based ordering, derived time dividers, pagination, drafts, attachment and voice-mode state, disclosure level, thinking status, reasoning summaries, provider trace state, tool activity, citations, action state, cancellation, retry, and reconnection.

**Acceptance:** the package renders no UI; all state is serializable; reducers handle duplicate events and interrupted streams; an application can replace every visible component while preserving behavior.

### M6. Default Frontend UI Components

**Purpose:** provide an opinionated interface that is ready to ship and remains themeable.

Required components include `AssistantShell`, `ConversationThread`, `MessageTimeDivider`, `UserMessage`, `AssistantMessage`, `StreamingMarkdown`, `ThinkingDisclosure`, `ToolActivity`, `Composer`, `VoiceMessageBubble`, `LiveDictationControl`, `TranscriptionStatus`, `ActionCard`, `CitationList`, `AttachmentPreview`, `ErrorBanner`, `StopButton`, `RegenerateButton`, and plugin renderer slots.

**Acceptance:** panel, drawer, inline, and full-page modes work at mobile and desktop widths; keyboard and screen-reader paths cover every operation; the five-minute default time-grouping rule survives pagination without moving the reading anchor; both voice modes expose distinct states and privacy expectations; internal tool identifiers remain hidden below developer level; all six disclosure levels render distinctly; `raw_trace` shows the full provider-supplied trace when available and an explicit unavailable state otherwise.

### M7. Multimodal Input Pack

**Purpose:** standardize image, voice, and file input across hosts.

**Responsibilities:** image selection, camera hints, drag and drop, previews, ordering, compression, upload progress, retry, voice permission, waveform, timer, cancel, batch and streaming transcription, editable dictation drafts, playable voice-message audio, transcript status, file validation, and attachment lifecycle. OCR, vision, batch ASR, streaming ASR, and on-device ASR are adapter interfaces rather than fixed providers.

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

**Acceptance:** image/file upload failure preserves the text draft; voice-message upload and transcription have independent retry states; voice messages remain playable when transcription fails; the assistant consumes only a completed or user-corrected transcript; live dictation preserves partial text on recoverable failure; neither mode silently changes execution location; frontend and backend enforce the same audio type, duration, size, and privacy policy.

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

**Purpose:** standardize user-reviewed business changes while preserving host authority.

```text
proposed -> editing <-> awaiting_confirmation -> applying -> applied
editing -> cancelled
awaiting_confirmation -> cancelled | expired | blocked_plugin_disabled
applying -> failed -> retrying
applied -> undoing -> undone | undo_failed
blocked_plugin_disabled -> awaiting_confirmation  (compatible re-enable + revalidation)
blocked_plugin_disabled -> cancelled | archived   (manual resolution)
```

**Responsibilities:** typed proposals, schema-driven editing, confirmation, cancellation, plugin-disable blocking, conflict handling, idempotent application, partial results, retry, archival, and optional undo.

**Acceptance:** the model can propose but cannot apply; confirmation rechecks authorization and validation; duplicate confirmation cannot duplicate a business write; undo is available only when the Host Adapter declares a compensating operation. Disabling a contributing plugin moves every not-yet-applying Pending Action to `blocked_plugin_disabled` without cancelling or executing it. Compatible re-enable requires revalidation before returning to `awaiting_confirmation`; permanent removal allows manual cancellation or archival. Applied history remains readable, and an Action already in `applying` records its eventual Host result rather than being silently interrupted.

### M12. Safety & Governance

**Purpose:** enforce the minimum security and observability baseline.

**Responsibilities:** permission classes, data scopes, sensitive-data redaction, cost and rate limits, timeouts, maximum tool calls, audit events, and integration/plugin permission checks.

**Acceptance:** minimum permission enforcement, write blocking, redaction, and audit contracts cannot be disabled; advanced quotas are configurable; audit records preserve debugging metadata without storing credentials, raw private attachments, or unredacted context.

### M13. Developer Toolkit

**Purpose:** let contributors integrate, debug, and test without a live model or production data.

**Responsibilities:** Mock model server, stream inspector, context-profile simulator, Context Manifest/token inspector, tool playground, permission viewer, Integration Generator, Manifest review report, generated adapter/fixture scaffolding, replay runner, plugin compatibility validator, fixed evaluation corpus, and failure simulation.

**Acceptance:** CI runs without provider credentials; a sanitized replay fixture reproduces a failed run; the Integration Generator never activates writes and reports unresolved security or transaction semantics; error simulation covers disconnect, timeout, malformed events, tool failure, permission denial, renderer failure, and attachment failure.

### M14. Reference Integrations and Migration Proof

**Purpose:** prove that the public contracts are not tailored to one domain.

The repository SHOULD include domain-neutral examples for wellness logging, itinerary planning, and household finance. The examples collectively cover direct embed, declarative Manifest, generated integration, and custom plugin paths. One real or representative Host MUST integrate the Host Adapter, default UI, and at least one confirmed Action.

**Acceptance:** all examples use the same event, tool, Action, and renderer contracts; at least one business Action works without custom plugin code; no domain field is added to core schemas; renderer failure falls back safely; permission changes prevent confirmation; the example suite runs with Mock model and Fake Host Adapter fixtures.

## Official capability packages

“Official” means maintained, tested, versioned, and compatible with the core. It does not mean enabled automatically.

| Package | Default state | MVP contents |
| --- | --- | --- |
| Essentials | enabled | date/time, calculator, unit conversion, formatting, text cleanup, bounded page context |
| Multimodal Input | disabled | image and file lifecycle plus persisted `voice_message` batch transcription and editable `live_dictation` streaming transcription |
| Context Management | disabled | `balanced` and `durable` profiles, segmentation, ledger, summaries, retrieval, invalidation, rebuild, and Context Manifest; core always provides `lite` |
| Knowledge & Retrieval | disabled | web, URL, document, host knowledge, citations |
| Memory | disabled | explicit scoped Memory with user controls |
| Action Workspace | disabled | editable confirmed actions and idempotent host application |
| Safety & Governance | minimum baseline required | permission enforcement, write blocking, redaction, and audit; advanced limits are configurable |
| Developer Toolkit | development only | Mock services, inspectors, replay, validation, evaluation, and failure simulation |

## Host integration manifest and plugin lifecycle

### Host Integration Manifest

A `Level 1` integration is declarative. A `Level 2` Integration Generator produces the same format with `review_status: draft` and an unresolved-risk report.

```yaml
application:
  id: org.example.sample-app
  conversation_mode: single
  context_profile: durable

context_sources:
  - id: current_record
    source: page_state
    fields: [record_id, selected_date]

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
    confirmation: explicit
    renderer: schema-form

review_status: approved
```

The Manifest contains approved mappings, not arbitrary executable business code. Read tools and generic schema renderers MAY activate after validation. Every write-proposal mapping requires explicit review of authorization, validation, idempotency, transaction, confirmation, privacy, and optional undo semantics.

### Custom Plugin Manifest

The minimum `Level 3` custom plugin manifest contains:

```json
{
  "id": "org.example.sample-plugin",
  "name": "Sample Plugin",
  "version": "0.1.0",
  "protocol_range": ">=0.1.0 <0.2.0",
  "capabilities": ["sample.read", "sample.propose"],
  "permissions": ["host.sample.read", "host.sample.write-proposal"],
  "tools": ["sample.lookup", "sample.propose-update"],
  "actions": ["sample.update"],
  "renderers": ["sample.result", "sample.action"],
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

When a plugin is disabled, every not-yet-applying Pending Action contributed by that plugin enters `blocked_plugin_disabled`. The framework MUST NOT cancel or execute it automatically. Compatible re-enable triggers permission, payload, schema, and version revalidation before the Action returns to `awaiting_confirmation`. Permanent removal allows manual cancellation or archival. Applied Actions remain readable through stored data and a generic renderer.

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
- distinguish history loading, sending, streaming, tool execution, upload, transcription, and action application;
- auto-follow streaming only while the user remains at the bottom;
- preserve the reading anchor when older history is prepended;
- derive localized time dividers with a five-minute default inactivity threshold, recomputing them after pagination without changing Message order;
- keep `voice_message` playback/transcription states separate from `live_dictation` recording, partial-text, and editable-draft states;
- honor the configured disclosure level without inventing unavailable reasoning data;
- show user-facing tool outcomes rather than internal function names;
- make proposed actions editable before confirmation;
- render `blocked_plugin_disabled` Actions as readable but non-confirmable, with compatible re-enable, manual cancel, and archival guidance;
- provide accessible error, retry, cancellation, and permission-denied states;
- meet WCAG 2.2 AA for the default web kit;
- support reduced motion and 44 px minimum touch targets;
- support mobile widths from 360 px and embedded panels from 320 px.

## Context, memory, and data authority

The framework distinguishes three information classes:

| Class | Authority | Retention rule |
| --- | --- | --- |
| Structured host data | host application | controlled by the host business and retention policy |
| Context View | per-Run compiled input | immutable for its Run; reproducible from its Manifest where sources remain authorized |
| Context summary | derived cache | rebuildable; never replaces or deletes original messages |
| Memory | explicit persistent information | scoped, inspectable, editable, deletable, and authorized |

Cancelled actions and unverified model statements MUST NOT become Memory. Context summaries MUST NOT be used to repair or override structured host facts.

## Security and privacy

### Permission classes

- `none`: deterministic computation without protected data;
- `read`: host or page data access;
- `write-proposal`: creation of an uncommitted Action;
- `external-read`: outbound access to a third-party source;
- `dangerous`: high-risk capability, unavailable in the MVP.

### Required controls

- Protected tools MUST declare permissions and data scope.
- External calls MUST declare what data leaves the host boundary.
- Sensitive fields MUST be redacted from logs and developer fixtures.
- Provider credentials MUST remain server-side.
- Attachment access MUST be private and host-authorized.
- Action confirmation MUST revalidate authorization and payload integrity.
- Every committed Action MUST have an idempotency key and audit record.
- Partial failure MUST identify successful, failed, and retryable items.
- Live-dictation audio is ephemeral by default and is not retained as a Message. Voice-message audio is persisted as private user content under explicit Host retention and deletion policy.
- `raw_trace` requires explicit Host policy and viewer authorization, is excluded from normal logs, Memory, and Context Summary by default, and is not persisted unless the Host separately enables trace retention.
- Raw-trace exports MUST be labelled as sensitive provider reasoning content.
- Generated Host Integration Manifests remain `draft` until a reviewer resolves permission, privacy, idempotency, transaction, confirmation, cascading-delete, and undo risks. Runtime discovery MUST NOT activate undeclared Host operations.

## Versioning and compatibility

- Core packages and official capability packages use Semantic Versioning.
- The event protocol has its own schema version.
- A plugin declares a supported protocol range.
- Additive optional fields MAY be introduced in a compatible minor release.
- Removing a field, changing its meaning, or changing required state transitions requires a new protocol major version.
- Clients MUST tolerate unknown event types and optional fields.
- Stored Actions, summaries, Host Integration Manifests, and plugin configuration MUST retain the schema version used to create them.
- Migration code MUST be deterministic, testable, and reversible through release rollback or explicit compensating migration.

## Parallel implementation plan

| Wave | Parallel work | Exit gate |
| --- | --- | --- |
| 0 | M0, repository skeleton, CI | schema `0.1`, fixtures, and compatibility policy frozen |
| 1 | M1, M2, M3, M4, M5, M12, M13 | each module passes M0 conformance independently |
| 2 | M6, M7, M8, M9, M10, M11 | module acceptance passes using public APIs or fakes |
| 3 | M14 and cross-module recovery, permission, and idempotency tests | one representative host and three example domains pass |
| Release | documentation, migration notes, performance and security review | all MVP acceptance criteria pass |

Parallel work rules:

- M0 changes require compatibility review.
- Every module publishes a fake, fixture, or stub.
- Modules depend on public contracts, not another module’s storage or UI internals.
- Domain exceptions remain in plugins rather than entering core schemas.

## Conformance

### Required test suites

- schema validation with valid and invalid fixtures;
- event replay with duplicates, sequence gaps, interruption, and reconciliation;
- conversation-mode tests for single and multiple topology over the same Runtime and storage contracts;
- context-profile tests for `lite`, `balanced`, and `durable`, including profile switching and atomic activation;
- runtime lifecycle and provider error mapping;
- Host Adapter allow, deny, timeout, conflict, and refresh behavior;
- integration-level tests for direct embed, declarative Manifest, generated Manifest review, and custom Domain Plugin paths;
- Integration Generator tests for read-only scaffolding, write-proposal review gates, unresolved-risk reporting, and zero runtime activation;
- tool schema, permission, timeout, cancellation, and safe retry behavior;
- integration/plugin compatibility, disablement, migration preflight, renderer failure, and `blocked_plugin_disabled` Pending Actions;
- Headless reducers for every event type;
- UI component, accessibility, responsive, and recovery tests;
- message chronology tests for sequence ordering, five-minute grouping, cross-date labels, timezone formatting, pagination recomputation, and in-place Action updates;
- disclosure tests for all six levels, provider capability mismatch, authorization denial, and raw-trace persistence defaults;
- image, file, voice-message, live-dictation, ASR capability, transcript revision, privacy, fallback-disclosure, and attachment lifecycle tests;
- context segmentation, summary trigger, correction/supersession, compaction race, invalidation, permission filtering, provenance, Manifest, and rebuild tests;
- retrieval citations and external-data permission tests;
- Memory scope and deletion tests;
- Action state, reauthorization, idempotency, partial failure, and undo tests;
- redaction, quota, audit, replay, and failure-simulation tests.

### Cross-module scenarios

| Scenario | Modules | Required outcome |
| --- | --- | --- |
| Text conversation | M0, M1, M5, M6 | persisted input, streamed output, completed run |
| Read-only tool | M0, M1, M3, M6, M12 | visible lifecycle, authorized execution, validated output |
| Image upload failure | M5, M6, M7 | draft retained, retry available, clear error |
| Voice message | M0, M1, M5, M6, M7, M12 | private playable audio persists, batch transcript completes before assistant consumption, failure remains retryable |
| Live dictation | M5, M6, M7, M12 | on-device or disclosed server streaming fills an editable draft, never auto-sends, and retains no audio Message |
| Message time grouping | M0, M5, M6 | sequence order remains stable, continuous messages share one time anchor, five-minute/date boundaries create localized dividers, pagination recomputes without jump |
| Long single Conversation | M1, M8, M13 | selected profile compiles a bounded Context View, original history remains unchanged, Manifest explains inclusion and exclusion |
| Confirmed write | M0, M2, M11, M12 | proposal, confirmation, host application, idempotency, audit |
| Disabled plugin | M3, M4, M6 | no callable tool, safe renderer behavior, actionable diagnostic |
| Disabled plugin with Pending Action | M4, M11, M12 | Action becomes `blocked_plugin_disabled`, never auto-cancels or executes, and requires revalidation after compatible re-enable |
| Config-only application | M0, M2, M3, M4, M13 | approved Manifest supplies a read tool and confirmed Action without custom plugin code |
| External retrieval | M6, M9, M12 | citation, freshness, permission, and budget enforcement |
| Deleted Memory | M8, M10, M13 | record no longer enters context; audit remains |
| Domain portability | M0, M4, M11, M14 | three examples introduce no domain fields into core |

## MVP acceptance criteria

The MVP is complete when:

- [ ] M0 schemas are frozen at `0.1` and the conformance command passes.
- [ ] M1-M14 satisfy their module acceptance requirements.
- [ ] A representative host embeds the default UI through a real Host Adapter.
- [ ] Text, image/file attachment, persisted voice-message with backend transcript, and live editable dictation flows work.
- [ ] Streaming Markdown, all six disclosure levels, tool activity, citations, and Action cards render through public contracts.
- [ ] A `Level 1` Host Integration Manifest contributes a tool and a confirmed Action without custom plugin code.
- [ ] A `Level 2` generated Manifest reports unresolved risks and cannot activate writes before review.
- [ ] A sample `Level 3` Domain Plugin contributes a custom renderer or business handler without modifying core.
- [ ] Every side-effecting operation passes through Action Workspace and host confirmation.
- [ ] Context Management proves summary rebuild and unchanged original history.
- [ ] The same Runtime supports `single` and `multiple` Conversation modes, and Context Management supports `lite`, `balanced`, and `durable` profiles through one compiler contract.
- [ ] Stream interruption, upload failure, permission denial, provider failure, renderer failure, and partial Action failure have tested recovery paths.
- [ ] Official packages can be enabled or disabled according to their policy.
- [ ] CI runs conformance and end-to-end Mock scenarios without external credentials.
- [ ] Direct-embed, Integration Manifest, Integration Generator, custom-plugin, UI, testing, security, and migration documentation is published.

## Deferred work

The following work is intentionally deferred beyond the MVP:

- official React, SwiftUI, and other framework-specific UI kits;
- vector database and embedding-provider standardization;
- signed plugin distribution and remote update infrastructure;
- cross-application Memory federation;
- multi-agent orchestration;
- autonomous background tasks and proactive notifications;
- organization-wide approval workflows for high-risk capabilities.
