# Framed Assistant

Framed Assistant is a framework intended for open-source release that embeds a consistent, safe, and progressively extensible AI assistant into an existing application.

It combines a shared runtime protocol, host-controlled tools and actions, a Headless frontend SDK, a production-ready default interface, and optional official capability packages for multimodal input, retrieval, context management, Memory, and more.

## Project status

**Runnable reference MVP, pre-alpha.**

The repository now includes the versioned JSON contracts, a FastAPI/SQLite reference Runtime, a Vue 3 Headless/default client, a reference Host, Mock and OpenAI-compatible model adapters, and real browser E2E coverage. The package is suitable for evaluation and contribution, not yet for a production deployment.

See the [MVP specification](docs/mvp-spec.md) for normative requirements and [DESIGN.md](DESIGN.md) for the UI and interaction contract.

## Why Framed Assistant?

Embedded assistants often repeat the same difficult work:

- conversation persistence and streaming recovery;
- image, voice, and file input;
- visible thinking status and tool activity;
- safe, policy-controlled confirmed or allowlisted automatic Actions;
- long-context summarization and retrieval;
- permissions, redaction, audit, and idempotency;
- plugin compatibility and domain-specific rendering;
- accessible mobile and desktop chat behavior.

Framed Assistant standardizes those concerns while leaving business authority with the host application.

The framework manages assistant behavior. The host application keeps control of identity, private data, authorization, validation, transactions, and committed writes.

## Key design decisions

- **Host-controlled authority:** models and plugins cannot access or modify business data outside the Host Adapter.
- **Two-layer frontend:** a polished default UI is built on a replaceable Headless state layer.
- **Progressive capabilities:** applications enable only the packages they need.
- **Policy-controlled side effects:** every business write is a typed Action; the Host may require confirmation or automatically apply only a reviewed low-risk allowlisted Action.
- **Default-off Host Data Write Tools:** reviewed schema-bound create/update/upsert/delete/link/unlink tools can write through a Host transaction adapter, but the model never receives raw SQL, credentials, or unrestricted database access.
- **Configurable reasoning disclosure:** hosts can choose from hidden status through contextual activity, developer diagnostics, and an opt-in `raw_trace` level that displays the complete reasoning trace returned by a capable model provider.
- **Rebuildable context summaries:** Context Management never deletes or rewrites original messages.
- **Configurable conversation and context policy:** single and Host-managed multiple Conversation modes share one Runtime; `lite`, `balanced`, and `durable` profiles share one Context Compiler.
- **Progressive Host integration:** applications can start with direct embed, move to a declarative or generated Host Integration Manifest, and write a custom Domain Plugin only when configuration cannot express the required behavior safely.
- **Chat-native chronology:** sequence-stable Messages use localized time dividers only at the first visible Message, a date boundary, or a configurable inactivity gap that defaults to five minutes.
- **Two voice modes:** persisted playable `voice_message` input uses backend batch transcription, while `live_dictation` uses on-device or disclosed server streaming ASR to fill an editable draft.
- **One Attachment System:** draft selection, private upload, parsing, Message rendering, Lightbox preview, retry, provenance, Privacy cleanup, and explicit Host Promotion share one contract.
- **Unified Privacy Center:** users can inventory, export, and delete registered assistant data from one place, with explicit retention limits and derived-data cleanup.
- **Controlled plugins:** plugins are installed during a release and may be enabled or disabled at runtime; arbitrary remote installation and plugin-owned data migration/automated rollback are out of scope for v0.1.

## Architecture

```text
Host application
  identity · permissions · business data · transactions
                         │
                         ▼
Host Adapter ── Framed Assistant protocol ── Headless SDK ── Default UI
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
       Runtime      Tool/Action      Integration and plugin host
          │          governance          │
          └──────────────┬───────────────┘
                         ▼
              Official capability packages
```

The JSON Schema event protocol is the cross-language source of truth. The MVP reference implementation targets a Python/FastAPI runtime and a Vue 3/TypeScript web client while keeping the protocol portable to other clients.

## Quick start

Requirements: Python 3.11+, [uv](https://docs.astral.sh/uv/), Node.js, and npm.

```bash
uv sync
npm install
```

Start the API and reference Host in separate terminals:

```bash
.venv/bin/uvicorn framed_assistant.app:app --reload --port 8000
npm run dev --workspace frontend -- --host 127.0.0.1 --port 5173
```

Open `http://127.0.0.1:5173`. The reference Host uses explicit `X-Actor-ID` and `X-Scope-Key` headers and the credential-free Mock Provider by default.

To use an OpenAI-compatible Chat Completions endpoint:

```bash
FRAMED_PROVIDER=openai-compatible \
OPENAI_API_KEY=... \
OPENAI_BASE_URL=https://api.openai.com/v1 \
OPENAI_MODEL=gpt-4.1-mini \
.venv/bin/uvicorn framed_assistant.app:app --port 8000
```

The Mock Provider exposes deterministic reference prompts used by the E2E suite, including `Create record: Title | 12.50`, `List records`, `Calculate: 2 + 3`, and `Search knowledge: query`.

Set `FRAMED_CONVERSATION_MODE=single` when a Host scope must expose only one active Conversation. The reference Host defaults to `multiple` and owns its Conversation navigation outside the assistant shell.

## MVP scope

The MVP is divided into independently testable modules:

| Group | Modules |
| --- | --- |
| Protocol and runtime | M0 Contracts, M1 Runtime, M2 Host Integration Bridge, M3 Tool Runtime, M4 Integration and Plugin System |
| Frontend | M5 Headless SDK, M6 Default UI, M7 Multimodal Input |
| Optional capabilities | M8 Context Management, M9 Knowledge & Retrieval, M10 Memory, M11 Action Workspace |
| Trust and delivery | M12 Safety & Governance, M13 Developer Toolkit, M14 Reference Integrations |

Each module publishes fixtures or fakes so teams can work in parallel after M0 contracts are frozen.

### Official capability packages

| Package | Default state |
| --- | --- |
| Essentials | enabled |
| Multimodal Input | disabled |
| Context Management | disabled; the core still provides the `lite` profile |
| Knowledge & Retrieval | disabled |
| Memory | disabled |
| Action Workspace | disabled |
| Safety & Governance | minimum baseline required |
| Developer Toolkit | development only |

### Conversation and context profiles

| Setting | Options | Meaning |
| --- | --- | --- |
| Conversation mode | `single`, `multiple` | One active Conversation or several Host-managed Conversations; the framework renders the active `conversation_id` |
| Context profile | `lite` | Host facts, current input, current Action state, and recent raw turns |
| Context profile | `balanced` | `lite` plus a Working Ledger, summaries, relevant history retrieval, and a Context Manifest |
| Context profile | `durable` | `balanced` plus immutable segments, correction tracking, hybrid raw retrieval, invalidation, rebuild, and complete provenance |

`durable` is recommended for long-lived single-Conversation assistants. Profiles are presets over one compiler, so switching profiles never changes or deletes the raw Conversation.

### Host integration levels

| Level | Integration path |
| --- | --- |
| `Level 0` | Direct embed with the minimal Host Adapter, enabled Essentials baseline, and no domain tools or writes |
| `Level 1` | Declarative Host Integration Manifest using approved context, OpenAPI/JSON-Schema tools, generic renderers, and Action mappings |
| `Level 2` | Development-time Integration Generator that produces a reviewable Manifest, adapters, fixtures, and unresolved-risk report |
| `Level 3` | Optional custom Domain Plugin for complex validation, transactions, retrieval, renderers, services, or undo behavior |

Every level retains the Host Adapter authority boundary. Generated write mappings never activate automatically; they require human review of permissions, privacy, validation, idempotency, transaction, confirmation, cascading-delete, and undo semantics.

### Action execution modes

| Mode | Behavior |
| --- | --- |
| `read_only` | Reads and analysis only; business writes cannot execute. |
| `confirm_each` | Every business Action waits for user review and confirmation. This is the default. |
| `auto_apply_allowlist` | Reviewed low-risk allowlisted Actions may apply automatically through Host validation, transaction, idempotency, audit, result visibility, and optional undo. |

Automatic mode never gives the model direct database access. Payments, transfers, and other dangerous capabilities remain unavailable in the MVP. Supported Actions for delete, external communication, private-data sharing, account or permission change, bulk or irreversible mutation, Attachment Promotion, ambiguous targets, low-confidence OCR/ASR, and operations without approved compensation still require confirmation. Privacy deletion uses its separate Privacy Job destructive-confirmation flow.

Host Data Write Tools are a separate, default-disabled capability:

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
```

Hosts enable individual entities, operations, writable fields, actor/tenant row scope, optimistic concurrency, and execution mode. Every model call becomes a typed Action and executes through the Host-owned transactional adapter. Enabling one entity or operation never enables the rest.

### Message time and voice input

- Continuous Messages inside the default five-minute interval share one compact time anchor; date and time labels become more explicit for older history and are recomputed after pagination.
- `voice_message` sends a private playable audio bubble, retains the audio under Host policy, and waits for a backend transcript before assistant processing.
- `live_dictation` streams partial transcription into the Composer, remains editable, never auto-sends, and does not create or retain an audio Message.
- ASR adapters may be batch or streaming and device-side or server-side. A fallback that moves audio off device must be disclosed before upload.

### Attachment system

- One `AttachmentTray` lives inside the Composer above text. Repeated selection appends by default, preserves order, allows reorder/removal, and enforces a visible configurable limit that defaults to eight.
- Validation, optimization, upload, processing, and model readiness are separate per-item states. Required processing failure pauses for retry, remove-and-continue, or cancel; optional failure continues only with a warning.
- Sent text and attachments remain one Message with one time/delivery/retry/privacy group. Images use a consistent grid and authorized `AttachmentLightbox`; files use cards with name, type, size, processing state, and one explicit preview/download/retry/unavailable action.
- History uses stable private Attachment IDs and thumbnail/preview/original variants, never persisted `blob:` URLs, data URLs, or array indexes.
- A chat attachment becomes a Host receipt, record photo, gallery item, or other business resource only through a confirmed Action showing source and promoted Attachment references.

### Privacy Center

Privacy Center is part of the mandatory Safety & Governance baseline. It shows only registered categories across Conversations/Messages, media/transcripts, Memory, retained traces, context, Actions, and extension data.

- `PrivacyCenter` is the single inventory and export/deletion entry surface; `PrivacyJobStatus` contains preview, confirmation, progress, partial results, and retry.
- Exports use private authenticated delivery and include a machine-readable category/schema manifest. Deletion removes or invalidates registered derived summaries, ledgers, indexes, manifests, and caches.
- Host-owned committed business records link to Host deletion controls rather than being silently deleted.
- Required audit or legal retention is disclosed with retained fields, reason, owner, and expiry.
- Partial or unresolved processors remain visible and retryable; the framework never reports full success without confirmation.

## Progressive adoption

A host can adopt Framed Assistant incrementally:

1. Embed the default text assistant with the minimal Host Adapter and enabled Essentials baseline.
2. Add bounded Host context and choose an integration level for deterministic read-only tools.
3. Enable the unified Attachment System for multi-image/file input, private processing, gallery preview, persisted voice-message, and editable live dictation.
4. Select a context profile, then add configurable reasoning disclosure, tool activity, and Context Management as needed.
5. Add retrieval, citations, and explicit Memory where appropriate.
6. Optionally enable reviewed Host Data Write Tools through a Manifest, generated integration, or custom Domain Plugin, then choose `confirm_each` or reviewed `auto_apply_allowlist` policy.

No stage requires the host to surrender authorization or transaction control.

## Security model

- Tools declare input/output schemas, permissions, side-effect class, retry policy, and redaction rules.
- Protected reads and external calls require host authorization.
- Host business mutations pass through Action Workspace and are reauthorized immediately before confirmed or automatic application; Privacy deletion uses the mandatory Privacy Job policy flow.
- `auto_apply_allowlist` is deny-by-default, cannot be selected by the model, and records the reviewed policy decision for every automatic Action.
- Host Data Write Tools are absent from the model manifest by default; raw SQL, table browsing, connection details, unrestricted predicates, undeclared fields, and out-of-scope rows are forbidden.
- Committed actions require idempotency keys and audit records.
- Provider credentials remain server-side.
- Private attachments use host-authorized access.
- Attachment limits and processing capabilities are disclosed before send; selected items are never silently truncated or dropped, and promotion into Host business resources requires confirmed source references.
- Logs and replay fixtures exclude secrets, raw private attachments, and unredacted model context.
- Raw provider reasoning traces are disabled by default and require explicit Host policy, viewer authorization, and a separate retention decision.
- Voice-message audio is private persisted user content under Host retention policy; live-dictation audio is ephemeral by default and cannot move from device to server through a silent fallback.
- Integration Generator output remains draft until unresolved security and transaction semantics are reviewed; production runtime discovery cannot activate undeclared Host operations.
- Privacy inventory, exports, and deletion jobs require actor plus Host-scope authorization; plugins cannot persist undeclared data or orphan export/deletion handlers when disabled or removed.

Security-sensitive behavior is defined normatively in the [Security and privacy section](docs/mvp-spec.md#security-and-privacy).

## Repository layout

```text
.
├── README.md
├── DESIGN.md
├── pyproject.toml
├── package.json
├── contracts/               # Canonical JSON Schemas and fixtures
├── backend/framed_assistant # Runtime, adapters, tools, policies, and APIs
├── frontend/src             # Headless store and Vue default/reference UI
├── e2e/                     # Real browser and public HTTP flows
├── tests/                   # Focused contract verification
├── docs/
│   └── mvp-spec.md
└── scripts/
    └── check_public_docs.py
```

Runtime modules depend on public contracts and explicit Host boundaries; the reference Host remains separate from assistant UI state.

## Documentation

- [MVP specification](docs/mvp-spec.md) — normative architecture, contracts, modules, security, conformance, and acceptance criteria.
- [Design contract](DESIGN.md) — product principles, default UI, interaction states, accessibility, responsive behavior, and visual constraints.

## Testing

The primary verification path is the Playwright E2E suite. It starts the real FastAPI server and Vue client and covers streaming, Host-owned Conversation switching, attachments/Lightbox, both voice modes, confirmed and automatic Actions, Privacy, Context, Retrieval, Integration Generator, and Plugin disable/re-enable.

```bash
PLAYWRIGHT_BROWSERS_PATH=.data/playwright npx playwright install chromium
npm run test:e2e
```

Run the smaller contract, static, and build gates:

```bash
framed-conformance
.venv/bin/python -m pytest
.venv/bin/ruff check backend tests
.venv/bin/ruff format --check backend tests
npm run typecheck
npm run build
python3 scripts/check_public_docs.py
```

`framed-conformance` validates canonical schemas and explicit valid/invalid fixtures. `check_public_docs.py` separately validates publication hygiene and preservation of accepted product requirements.

## Contributing

The project accepts implementation, test, specification, and design contributions.

Before proposing an implementation change:

1. Identify the affected M0-M14 module.
2. Preserve the Host Adapter authority boundary.
3. Add or update public schemas and conformance fixtures before implementation.
4. Keep domain-specific fields in Host Integration Manifests or optional plugins rather than core contracts.
5. Prefer a real public-API or browser E2E scenario; add a smaller test only when it proves a contract that E2E cannot isolate clearly.
6. Run the relevant commands from the Testing section.

Breaking protocol changes require an explicit schema-version proposal and migration plan.

## License

Framed Assistant is licensed under the [Apache License 2.0](LICENSE).
