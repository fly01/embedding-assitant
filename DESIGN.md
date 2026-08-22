# Design

## Source of truth

- Status: Active for MVP v0.1
- Last refreshed: 2026-08-22
- Primary product surfaces: embedded assistant shell, conversation thread, multimodal composer, Attachment System and Lightbox, voice input, reasoning/tool activity, Action Workspace, citations, Privacy Center, integration/plugin renderers, and developer inspectors.
- Related specification: `docs/mvp-spec.md`.
- Evidence reviewed: the public MVP specification, established embedded-assistant patterns across wellness, itinerary-planning, and household-finance domains, and common accessibility and recovery requirements for mobile chat interfaces.

## Brand

- Personality: dependable, calm, application-native, precise.
- Trust signals: explicit permissions and confirmation states, visible tool progress, recoverable stream/upload errors, traceable summaries, and citations when external information is used.
- Avoid: generic chatbot chrome, decorative AI gradients, accidental reasoning-trace exposure, hidden writes, irreversible agent actions, and assistant styling that fights the host application.

## Product goals

- Goals: give current and future applications one high-standard embedded AI assistant instead of repeatedly rebuilding chat, streaming, tools, action confirmation, memory, attachments, and recovery.
- Goals: support progressive adoption from a text-only panel to configuration-driven domain tools and Actions, generated integrations, multimodal input, context management, retrieval, Memory, and optional custom plugins.
- Goals: provide both a production-ready default experience and a headless interaction layer.
- Goals: provide one Privacy Center for assistant data inventory, export, deletion, retention visibility, and derived-data cleanup across core, official packages, integrations, and plugins.
- Non-goals: third-party plugin marketplace, arbitrary online hot installation, browser automation, arbitrary code execution, payments/transfers, background autonomous agents, or a shared cross-domain business schema.
- Success signals: a new Host can embed the basic assistant in one working day; a standard CRUD-style application can add a confirmed Action through an approved Integration Manifest without custom plugin code; a custom plugin can still add specialized behavior without changing core; users can inventory/export/delete registered assistant data from one place; no model, generated integration, or plugin can bypass Host authorization and transaction boundaries.

## Personas and jobs

- Primary personas: application developers embedding the assistant, maintainers reviewing generated Integration Manifests, plugin authors adding specialized capabilities, and product users asking the assistant to understand or act on current application context.
- User jobs: ask and follow up, attach an image or file, send a voice message, dictate editable text, understand visible activity, review proposed changes, confirm or revise Actions, inspect retention, export or delete assistant data, and recover from interrupted work.
- Developer jobs: register tools, expose bounded context, declare permissions, implement host-side actions, provide domain renderers, theme the assistant, inspect event streams, and test upgrades without a live model.
- Key contexts of use: mobile-first private applications, authenticated user or workspace scopes, long conversations, slow networks, and workflows where AI-proposed writes require confirmation.

## Information architecture

- Primary navigation: owned by the host application; the framework supplies embeddable surfaces rather than a global navigation model.
- Core routes/screens: `AssistantPanel`, `AssistantDrawer`, `AssistantInline`, `AssistantFullScreen`, optional conversation history, and development-only inspector surfaces.
- Content hierarchy: conversation thread first; composer second; thinking, tool, citation, and action state inline with the relevant assistant turn; high-risk confirmation always explicit.

## Design principles

- Principle 1: the framework owns assistant behavior consistency; the host application owns business authority.
- Principle 2: default UI is polished enough to ship, while the headless layer lets an application replace every visible component without reimplementing state behavior.
- Principle 3: reasoning disclosure is progressive and Host-bounded, ranging from hidden status through contextual activity and developer diagnostics to an explicitly enabled raw provider trace.
- Principle 4: model output is not a committed business change; side effects pass through typed actions, confirmation policy, host validation, idempotency, and audit.
- Principle 5: context summaries are rebuildable model-input caches, not memory and not business truth. Compression never deletes or rewrites original messages.
- Principle 6: Host integrations and optional plugins extend declared contracts and slots; they cannot bypass Host data access, permissions, transactions, Privacy controls, or audit.
- Principle 7: single and multiple Conversation modes share one Runtime, while `lite`, `balanced`, and `durable` context profiles are presets over one Context Compiler rather than separate implementations.
- Principle 8: every Host supplies an integration boundary, but custom Domain Plugin code is optional; direct embed, declarative Manifest, generated integration, and custom plugin are progressive levels over the same contracts.
- Principle 9: Privacy Center is one mandatory control surface for all assistant-managed data; source deletion cascades to registered derivatives, while Host-owned business records and required audit retention are disclosed and handed off rather than silently deleted.
- Tradeoffs: MVP prioritizes a portable protocol, a Python/FastAPI reference runtime, and one polished Vue 3 implementation. SwiftUI and other UI-framework adapters follow the same protocol later.

## Visual language

- Color: inherit host semantic tokens first; provide neutral fallback tokens for surface, border, text, muted text, accent, warning, danger, and success.
- Typography: inherit host typography; use a compact, readable hierarchy rather than an assistant-specific brand face.
- Spacing/layout rhythm: mobile-first 8 px rhythm, minimum 44 px touch targets, stable composer footprint, and no horizontal overflow in ordinary message content.
- Shape/radius/elevation: host-native panels and cards; action cards remain visually distinct without nested decorative card stacks.
- Motion: short, purposeful transitions for streaming, tool progress, upload progress, and action outcomes; honor reduced motion.
- Imagery/iconography: use the host icon system when available; never load arbitrary model-generated remote Markdown images.

## Components

- Existing patterns to preserve as behavioral evidence: streaming Markdown, sequence-stable paginated history, grouped message-time dividers, multimodal composition, multi-image selection, private thumbnail/preview/original variants, playable voice messages, editable live dictation, visible tool activity, resumable streams, and editable confirm/cancel Action cards.
- New/changed components: headless assistant store, assistant shell, conversation thread, `MessageTimeDivider`, message-part renderers, multimodal composer, `AttachmentTray`, `AttachmentGrid`, `AttachmentFileCard`, `AttachmentProcessingStatus`, `AttachmentLightbox`, `VoiceMessageBubble`, `LiveDictationControl`, `TranscriptionStatus`, reasoning disclosure, tool activity, citations, Action Workspace, `PrivacyCenter`, `PrivacyResourceList`, `DeletionImpactPreview`, `PrivacyJobStatus`, error recovery, plugin slots, Host-context badges, Integration Manifest editor/review, generated-risk report, Context Profile settings, Context Manifest inspector, and developer inspectors.
- Variants and states: inline, drawer, side panel, full-screen tab, and floating panel; signed out, disabled by Host, loading history, streaming, interrupted, offline, attachment selected/validating/optimizing/uploading/uploaded/processing/ready/partial/failed/unsupported/blocked, required attachment waiting for user decision, Attachment Lightbox open/unavailable, recording voice message, voice message transcribing, voice transcription failed, live dictation loading/listening/partial/final, permission denied, privacy inventory loading, export preparing/ready/failed, deletion preview/awaiting-confirmation/running/partial/completed/failed, unresolved processor, retention restricted, Integration Manifest draft, review blocked, plugin disabled, Action blocked by plugin, reasoning unavailable, raw trace visible, context profile preparing, context fallback active, context rebuild failed, awaiting confirmation, applying, partial failure, applied, cancelled, archived, and undo available.
- Token/component ownership: the framework owns semantic token names and slot contracts; host applications override values or renderers without forking runtime state.

### Attachment System

The framework distinguishes `AttachmentAsset`, `DraftAttachment`, `MessageAttachmentPart`, derived processing results, and promoted Host business resources. A chat attachment never becomes a business receipt, record photo, gallery item, or other Host resource without an explicit confirmed Action.

Default Composer behavior is:

```yaml
attachments:
  tray_position: inside_composer_above_text
  selection_mode: append
  max_count: 8
  allow_reorder: true
  required_attachment_failure: ask_user
```

- `AttachmentTray` is inside the Composer above the text field, hidden when empty, and shared with expanded input. Reopening selection appends. Every item exposes thumbnail/file identity, stable order, state, progress, retry, removal, and reorder. Replacing or truncating a selection without prior disclosure is forbidden.
- Validation and optimization complete before send. Private upload completes before Message submission. After send, processing may continue inside the Message while the assistant Run waits for required results. Required failure offers retry, remove-and-continue, or cancel; optional failure continues only with a visible warning.
- Text and attachments form one Message group with one time anchor, delivery state, retry surface, and privacy scope. User attachments default above user text. Assistant-generated files default below explanatory text. `ContentPart.order` remains authoritative.
- Image layout: one large constrained thumbnail; two columns for two images; a 2x2 grid for three or four; a compact three-column grid for five to eight with `+N` overflow where needed. Message lists load thumbnails only.
- Every authorized image opens `AttachmentLightbox` at the selected item. The default gallery scope is the parent Message. It supports previous/next, index, zoom, keyboard/touch navigation, close with focus restoration, and Host-controlled download/share/original access. Deleted, expired, unauthorized, or failed previews show a labelled tombstone or retry state rather than a dead tap.
- Non-image files use `AttachmentFileCard` with name, kind, size, pages/count where known, upload state, processing state, warnings, and exactly one clear capability: preview, download, retry, or unavailable reason.
- Upload, processing, and Assistant Run failures are separate. Retrying a model Run never repeats successful upload or parsing. The UI never hides a failed attachment or lets a backend silently ignore items beyond its lower limit.
- OCR, captions, text extraction, structured parsing, embeddings, summaries, thumbnails, and previews are derived and display source Attachment plus processor/version provenance. History uses stable private Attachment IDs and refreshed authorized variants, never persisted `blob:`/data URLs or array indexes.
- Attachment-derived Action cards show source file, page/region where relevant, processor/version, uncertain fields, and selected Promotion targets. Users can open the source before confirmation. Privacy Center displays chat sources and promoted Host resources separately and previews cross-resource deletion effects.

### Message chronology and time grouping

- Server `sequence` determines Message order. User messages display from `created_at`; assistant messages display from `visible_at ?? created_at`. Completion, transcription, tool, Action, or plugin updates never move the parent Message.
- `MessageTimeDivider` is derived UI. Show it for the first visible Message, a local-date boundary, or an inactivity gap at least `300` seconds by default. Continuous messages within that threshold share one time anchor. Hosts may configure the threshold.
- Localized labels are: today `HH:mm`; yesterday `Yesterday HH:mm`; recent week `weekday HH:mm`; earlier this year `month day HH:mm`; prior years `year month day HH:mm`.
- Viewer timezone is the default; Conversation or Host timezone may override it. Business-domain time remains separate from chat display time.
- After history pages merge, recompute adjacent dividers and preserve the prior reading anchor. Time dividers are never persisted as Messages.
- Message details expose exact timestamp, timezone, delivery/completion state, and edit time where available. Screen readers receive the full localized date and time even when the visible divider is compact.

### Voice input modes

```yaml
voice_input:
  modes: [voice_message, live_dictation]
  default_mode: live_dictation
  allow_user_switch: true
```

- `voice_message`: record and send a playable audio bubble. Upload through private Host storage, show duration/playback immediately, display transcription progress, and start the assistant Run only after a transcript is ready. The resulting transcript is available as a collapsible caption. The original audio is authoritative user content under Host retention policy; the automatic transcript is derived, versioned, and linked to its audio source. Failure preserves the playable Message with retry and correction paths. Correcting a transcript after an assistant response offers explicit regenerate and never silently replays an earlier Action.
- `live_dictation`: use streaming ASR to replace only the current dictation suffix in the Composer. Prefer an available on-device model; disclose any switch to server transcription before audio leaves the device. Stopping keeps editable text and never sends automatically. Audio is ephemeral and is not a Message.
- When both modes are enabled, use an explicit mode switch or clearly distinct gestures and labels. Never infer a mode change from provider failure. Persist user preference only when Host policy permits it.
- ASR adapters declare `batch` and/or `streaming`, `device` or `server`, supported languages/formats, partial-result behavior, and retention behavior. The UI shows model download/preparation, permission denial, recording, upload, transcription, partial text, completion, failure, and retry as distinct states.

### Reasoning disclosure

| Level | Default presentation |
| --- | --- |
| `hidden` | No reasoning disclosure control or content. |
| `status` | Short stage label and optional elapsed time. This is the framework default. |
| `contextual` | Authorized attachment, entity, or task context. |
| `activity` | User-facing tools, completion summaries, sources, and timing. |
| `developer` | Redacted parameters, event sequence, context composition, token usage, model metadata, and correlation IDs. |
| `raw_trace` | Complete provider reasoning trace exactly as returned by a trace-capable adapter. |

The Host defines the maximum permitted level. `raw_trace` is disabled by default, carries a persistent sensitive-content warning while visible, and shows an explicit unavailable state when the provider does not expose a trace. It is not added to normal logs, Memory, or Context Summary, and it is not persisted unless the Host separately enables trace retention.

### Conversation and context configuration

- `single` and `multiple` are Host-selected Conversation modes over the same data model and Runtime. In `single`, one Host-defined scope has one active Conversation; in `multiple`, users may create and manage several Conversations in that scope.
- `lite` is the core context profile and uses authoritative Host facts, current input, current Action state, and a bounded recent raw window.
- `balanced` adds a Working Ledger, summaries, relevant history retrieval, and a Context Manifest.
- `durable` adds immutable internal Context Segments, correction and supersession tracking, hybrid raw retrieval, complete provenance, invalidation, and rebuild. It is the recommended profile for long-lived single-Conversation assistants.

Profile controls belong to Host or administrator settings, not the ordinary chat composer. A profile upgrade shows preparing progress in developer/settings surfaces and activates atomically when its derived artifacts are ready. A failed build keeps the previous profile active and exposes diagnostics. A downgrade changes context selection without deleting the raw Conversation.

### Host integration experience

| Level | Maintainer experience |
| --- | --- |
| `Level 0` | Embed the assistant shell and provide the minimal Host Adapter; no domain tools or writes. |
| `Level 1` | Author and review a declarative Host Integration Manifest using generic context, OpenAPI, schema-form, and Action mappings. |
| `Level 2` | Run the Integration Generator, inspect discovered reads and proposed writes, resolve risk findings, and approve the generated Manifest. |
| `Level 3` | Add a custom Domain Plugin only for behavior that configuration and generated adapters cannot express safely. |

Integration authoring and generated-risk review are developer/maintainer surfaces, not end-user chat controls. Generated writes remain visibly blocked until permission, privacy, validation, idempotency, transaction, confirmation, cascading-delete, and undo questions are resolved.

If a contributing plugin is disabled, its not-yet-applying Action card remains readable and changes to `blocked_plugin_disabled`. Confirm and edit controls are disabled; the card explains compatible re-enable, manual cancellation, and archival. Re-enabling never resumes execution automatically—it first reruns compatibility, permission, payload, and schema validation. Applied history remains readable through a generic renderer.

### Privacy Center

- Present user-understandable categories for Conversations/Messages, attachments, voice-message audio, transcript revisions, Memory, retained raw traces, context artifacts, Pending Actions, integration/plugin data, and restricted Host/audit records.
- Each category shows owner, scope, item count or size where available, retention policy, export support, deletion support, and downstream effects. Internal indexes and caches appear as derived consequences rather than confusing standalone user data.
- Export uses private authenticated delivery and includes a manifest of included categories, schema versions, omissions, and retention restrictions.
- Deletion starts with an impact preview, then destructive confirmation. The progress surface shows per-category and per-processor status and never collapses partial completion into success.
- Removing source content removes or invalidates dependent transcripts, summaries, Working Ledger entries, retrieval indexes, Context Manifests, caches, and extension data. Host-owned committed records link to Host controls instead of being silently deleted.
- Required audit or legal retention is explicit: show retained fields, reason, owner, and expiry. A minimal tombstone must not expose deleted content.
- Plugin disablement or removal cannot strand data-management controls. Stable Host or migration handlers keep export/deletion available until the declared retention period ends.

## Accessibility

- Target standard: WCAG 2.2 AA for the default web component kit.
- Keyboard/focus behavior: composer, Attachment Tray removal/reorder/retry, file-card actions, Lightbox navigation/zoom/close with focus restoration, voice-mode switch, record/stop, voice-message playback, transcript retry/correction, Privacy Center inventory/export/delete controls, stop/regenerate, reasoning disclosure, tool details, citations, and Action controls must be reachable, labelled, and visibly focused.
- Contrast/readability: permission, confirmation, and error states never rely on color alone.
- Screen-reader semantics: Attachment Tray announces count, order, kind, progress, error, and available action; image grid items announce gallery position and unavailable reason; file cards expose name/type/size/processing capability; time dividers expose full localized time; voice messages expose duration and transcription status; live dictation announces state without reading every partial replacement; Privacy Jobs announce category progress and partial/unresolved outcomes without flooding; streaming and tool status use restrained live regions; reasoning disclosures expose their current level and expanded state; raw trace does not continuously flood a live region; and Action cards announce current state and available operations.
- Reduced motion and sensory considerations: waveform, loading, and streaming animations simplify or pause under reduced-motion preferences while recording state remains unambiguous.

## Responsive behavior

- Supported breakpoints/devices: primary web targets are 360–430 px mobile widths and 320–720 px embedded/desktop panels; contracts remain platform-neutral for native clients.
- Layout adaptations: shells respect safe areas and keyboard insets; the composer pins only when the Host container permits it; Attachment Tray uses a bounded horizontal strip or compact wrap without covering text/actions; grids recalculate columns without horizontal page overflow; Lightbox fills the safe viewport; tables and domain cards provide narrow-width fallbacks.
- Touch/hover differences: touch targets remain at least 44 px; attachment reorder uses accessible long-press/drag plus non-drag alternatives; Lightbox supports swipe/pinch and keyboard controls; icon-only actions expose labels and desktop tooltips.

## Interaction states

- Loading: distinguish history loading, sending, model streaming, tool execution, attachment validation/optimization/upload/processing, voice-message batch transcription, live-dictation model preparation/streaming transcription, Privacy inventory/export/deletion jobs, and Action application.
- Empty: show host-provided starter prompts and current-context hints, never fabricated conversation content.
- Error: preserve the text draft, ordered Draft Attachments, sent Message attachments, playable voice Message, partial dictation text, and safe metadata as applicable; distinguish validation, optimization, upload, processing, preview, permission, and Assistant Run failure; Privacy Jobs retain item-level success/failure and unresolved-processor evidence; explain whether retry, remove-and-continue, cancel, transcription correction, privacy retry, reconcile, edit, archival, compatible plugin re-enable, or context-profile fallback is available.
- Success: applied Action cards show the user-facing outcome and invoke an explicit Host refresh callback; Privacy Jobs summarize exported/deleted categories and remaining restrictions without claiming more than processors confirmed.
- Disabled: expose the reason visually and to assistive technology.
- Offline/slow network: retain existing messages, stop indeterminate loading, and offer bounded reconnection or retry.

## Content voice

- Tone: concise, calm, and transparent. The first reference locale is Simplified Chinese, but all default copy MUST be replaceable through localization resources; domain terminology comes from the Host Integration Manifest or optional plugin.
- Terminology: “助手”, “附件”, “正在校验”, “正在压缩”, “正在上传”, “正在解析”, “解析失败”, “不支持预览”, “查看原图”, “保存为业务资料”, “来源附件”, “隐私中心”, “导出助手数据”, “删除助手数据”, “删除影响”, “部分完成”, “保留期限”, “语音消息”, “实时转写”, “正在录音”, “正在转写”, “转写失败”, “正在思考”, “正在查看”, “待确认”, “确认”, “修改”, “取消”, “已应用”, “恢复回复”, “引用来源”.
- Microcopy rules: below developer level, describe user-facing activity and outcomes rather than internal function names. `raw_trace` is labelled as verbatim provider reasoning, not verified fact or framework-authored explanation. Integration review surfaces distinguish “generated candidate”, “approved mapping”, “blocked risk”, and “active capability”; a disabled-plugin Action never appears cancelled or executable.

## Implementation constraints

- Framework/styling system: MVP reference client uses Vue 3, TypeScript, and a headless store; the reference backend uses Python/FastAPI. JSON Schema and the event protocol are the cross-language source of truth.
- Design-token constraints: semantic CSS variables and typed slot props; no application-specific palette in framework packages.
- Performance constraints: paginated or virtualized history, bounded Attachment Tray and grid rendering, thumbnails only in Message lists, preview/original loading on demand, sequential or bounded-concurrency image decoding/optimization, stream backpressure, profile-driven token budgeting, one Context Compiler contract, and Context Manifest diagnostics.
- Compatibility constraints: authenticated private-data Hosts, registered Privacy Resources and export/delete/invalidation handlers, generic adapters backed by approved configuration, review-gated generated integrations, resumable event streams, Host-controlled media URLs, batch/streaming and device/server ASR adapters, explicit fallback disclosure, mobile Safari attachment behavior, and optional custom plugins installed at release time but enabled or disabled at runtime.
- Test/screenshot expectations: contract fixtures, reducer tests, Attachment Tray placement/append/limit/reorder, per-item state and retry, one-Message grouping, grid/file card/Lightbox/unavailable tombstones, history replay, required/optional processing gates, Action provenance/Promotion, Privacy invalidation, five-minute message-time grouping and pagination recomputation, both voice modes and ASR execution locations, audio retention/privacy, transcription failure/correction, all four Host integration levels, generated-risk review, `blocked_plugin_disabled` Actions, generic historical renderer fallback, single/multiple Conversation modes, `lite`/`balanced`/`durable` context profiles, profile preparation/fallback/failure states, all six reasoning disclosure levels, trace-unavailable and authorization states, component interaction and accessibility tests, mobile/desktop visual smoke checks, disconnect recovery, permission denial, and Action idempotency.

## Open questions

- [ ] Select the first public reference host and example domain / owner: maintainers / impact: medium.
- [ ] Decide whether a SwiftUI client kit belongs in v0.2 or starts after the v0.1 event protocol freezes / owner: maintainers / impact: medium.
- [ ] Confirm the public package namespace and release strategy / owner: maintainers / impact: low.
