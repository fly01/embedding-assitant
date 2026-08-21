# Framed Assistant

Framed Assistant is a framework intended for open-source release that embeds a consistent, safe, and progressively extensible AI assistant into an existing application.

It combines a shared runtime protocol, host-controlled tools and actions, a Headless frontend SDK, a production-ready default interface, and optional official capability packages for multimodal input, retrieval, context management, Memory, and more.

## Project status

**Specification-first, pre-alpha.**

The MVP architecture and public contracts are defined, but installable runtime and UI packages have not been released yet. The current repository is intended for specification review, module ownership, and implementation planning.

See the [MVP specification](docs/mvp-spec.md) for normative requirements and [DESIGN.md](DESIGN.md) for the UI and interaction contract.

## Why Framed Assistant?

Embedded assistants often repeat the same difficult work:

- conversation persistence and streaming recovery;
- image, voice, and file input;
- visible thinking status and tool activity;
- safe, editable action confirmation;
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
- **Confirmed side effects:** business writes are typed Action proposals until the user confirms them and the host applies them.
- **Configurable reasoning disclosure:** hosts can choose from hidden status through contextual activity, developer diagnostics, and an opt-in `raw_trace` level that displays the complete reasoning trace returned by a capable model provider.
- **Rebuildable context summaries:** Context Management never deletes or rewrites original messages.
- **Controlled plugins:** plugins are installed during a release and may be enabled or disabled at runtime; arbitrary remote code installation is out of scope for the MVP.

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
       Runtime      Tool/Action      Plugin host
          │          governance          │
          └──────────────┬───────────────┘
                         ▼
              Official capability packages
```

The JSON Schema event protocol is the cross-language source of truth. The MVP reference implementation targets a Python/FastAPI runtime and a Vue 3/TypeScript web client while keeping the protocol portable to other clients.

## MVP scope

The MVP is divided into independently testable modules:

| Group | Modules |
| --- | --- |
| Protocol and runtime | M0 Contracts, M1 Runtime, M2 Host Integration Bridge, M3 Tool Runtime, M4 Plugin System |
| Frontend | M5 Headless SDK, M6 Default UI, M7 Multimodal Input |
| Optional capabilities | M8 Context Management, M9 Knowledge & Retrieval, M10 Memory, M11 Action Workspace |
| Trust and delivery | M12 Safety & Governance, M13 Developer Toolkit, M14 Reference Integrations |

Each module publishes fixtures or fakes so teams can work in parallel after M0 contracts are frozen.

### Official capability packages

| Package | Default state |
| --- | --- |
| Essentials | enabled |
| Multimodal Input | disabled |
| Context Management | disabled |
| Knowledge & Retrieval | disabled |
| Memory | disabled |
| Action Workspace | disabled |
| Safety & Governance | minimum baseline required |
| Developer Toolkit | development only |

## Progressive adoption

A host can adopt Framed Assistant incrementally:

1. Embed the default text assistant.
2. Implement the Host Adapter and enable deterministic Essentials tools.
3. Add image, voice, and file input.
4. Add configurable reasoning disclosure, tool activity, and Context Management.
5. Add retrieval, citations, and explicit Memory where appropriate.
6. Add confirmed business actions and domain plugins.

No stage requires the host to surrender authorization or transaction control.

## Security model

- Tools declare input/output schemas, permissions, side-effect class, retry policy, and redaction rules.
- Protected reads and external calls require host authorization.
- Side effects pass through Action Workspace and are reauthorized at confirmation time.
- Committed actions require idempotency keys and audit records.
- Provider credentials remain server-side.
- Private attachments use host-authorized access.
- Logs and replay fixtures exclude secrets, raw private attachments, and unredacted model context.
- Raw provider reasoning traces are disabled by default and require explicit Host policy, viewer authorization, and a separate retention decision.

Security-sensitive behavior is defined normatively in the [Security and privacy section](docs/mvp-spec.md#security-and-privacy).

## Repository layout

```text
.
├── README.md
├── DESIGN.md
├── docs/
│   └── mvp-spec.md
└── scripts/
    └── check_public_docs.py
```

The implementation workspace will follow the module boundaries in the specification rather than a single monolithic package.

## Documentation

- [MVP specification](docs/mvp-spec.md) — normative architecture, contracts, modules, security, conformance, and acceptance criteria.
- [Design contract](DESIGN.md) — product principles, default UI, interaction states, accessibility, responsive behavior, and visual constraints.

Validate public documentation locally:

```bash
python3 scripts/check_public_docs.py
```

The check rejects local filesystem references, broken local links, malformed Markdown fences, missing public sections, and accidental removal of core MVP requirements.

This script validates publication hygiene for the current documents only. It is not the M0 protocol conformance suite described in the specification.

## Contributing

The project is currently accepting specification and architecture contributions.

Before proposing an implementation change:

1. Identify the affected M0-M14 module.
2. Preserve the Host Adapter authority boundary.
3. Add or update public schemas and conformance fixtures before implementation.
4. Keep domain-specific fields in plugins rather than core contracts.
5. Include unit tests, conformance tests, and failure-path coverage.
6. Run `python3 scripts/check_public_docs.py` for documentation changes.

Breaking protocol changes require an explicit schema-version proposal and migration plan.

## License

Framed Assistant is licensed under the [Apache License 2.0](LICENSE).
