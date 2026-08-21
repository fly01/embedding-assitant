# Design

## Source of truth

- Status: Active for MVP v0.1
- Last refreshed: 2026-08-21
- Primary product surfaces: embedded assistant shell, conversation thread, multimodal composer, thinking/tool activity, action workspace, citations, plugin renderers, developer inspectors.
- Related specification: `docs/mvp-spec.md`.
- Evidence reviewed: the public MVP specification, established embedded-assistant patterns across wellness, itinerary-planning, and household-finance domains, and common accessibility and recovery requirements for mobile chat interfaces.

## Brand

- Personality: dependable, calm, application-native, precise.
- Trust signals: explicit permissions and confirmation states, visible tool progress, recoverable stream/upload errors, traceable summaries, and citations when external information is used.
- Avoid: generic chatbot chrome, decorative AI gradients, raw internal tool names, raw chain-of-thought, hidden writes, irreversible agent actions, and assistant styling that fights the host application.

## Product goals

- Goals: give current and future applications one high-standard embedded AI assistant instead of repeatedly rebuilding chat, streaming, tools, action confirmation, memory, attachments, and recovery.
- Goals: support progressive adoption from a text-only panel to multimodal input, tool activity, confirmable domain actions, context management, retrieval, memory, and additional plugins.
- Goals: provide both a production-ready default experience and a headless interaction layer.
- Non-goals: third-party plugin marketplace, arbitrary online hot installation, browser automation, arbitrary code execution, payments/transfers, background autonomous agents, or a shared cross-domain business schema.
- Success signals: a new host can embed the basic assistant in one working day; a domain plugin can add tools and renderers without changing core; a second host reuses the same event and action contracts; no model or plugin can bypass host authorization and transaction boundaries.

## Personas and jobs

- Primary personas: application developers integrating the assistant, plugin authors adding domain capabilities, and product users asking the assistant to understand or act on current application context.
- User jobs: ask and follow up, attach an image or file, dictate editable text, understand visible activity, review proposed changes, confirm or revise actions, and recover from interrupted work.
- Developer jobs: register tools, expose bounded context, declare permissions, implement host-side actions, provide domain renderers, theme the assistant, inspect event streams, and test upgrades without a live model.
- Key contexts of use: mobile-first private applications, authenticated user or workspace scopes, long conversations, slow networks, and workflows where AI-proposed writes require confirmation.

## Information architecture

- Primary navigation: owned by the host application; the framework supplies embeddable surfaces rather than a global navigation model.
- Core routes/screens: `AssistantPanel`, `AssistantDrawer`, `AssistantInline`, `AssistantFullScreen`, optional conversation history, and development-only inspector surfaces.
- Content hierarchy: conversation thread first; composer second; thinking, tool, citation, and action state inline with the relevant assistant turn; high-risk confirmation always explicit.

## Design principles

- Principle 1: the framework owns assistant behavior consistency; the host application owns business authority.
- Principle 2: default UI is polished enough to ship, while the headless layer lets an application replace every visible component without reimplementing state behavior.
- Principle 3: progressive disclosure starts with the user-facing result, then exposes safe activity summaries, tools, sources, and editable actions as needed.
- Principle 4: model output is not a committed business change; side effects pass through typed actions, confirmation policy, host validation, idempotency, and audit.
- Principle 5: context summaries are rebuildable model-input caches, not memory and not business truth. Compression never deletes or rewrites original messages.
- Principle 6: plugins extend declared contracts and slots; they cannot bypass host data access, permissions, transactions, or audit.
- Tradeoffs: MVP prioritizes a portable protocol, a Python/FastAPI reference runtime, and one polished Vue 3 implementation. SwiftUI and other UI-framework adapters follow the same protocol later.

## Visual language

- Color: inherit host semantic tokens first; provide neutral fallback tokens for surface, border, text, muted text, accent, warning, danger, and success.
- Typography: inherit host typography; use a compact, readable hierarchy rather than an assistant-specific brand face.
- Spacing/layout rhythm: mobile-first 8 px rhythm, minimum 44 px touch targets, stable composer footprint, and no horizontal overflow in ordinary message content.
- Shape/radius/elevation: host-native panels and cards; action cards remain visually distinct without nested decorative card stacks.
- Motion: short, purposeful transitions for streaming, tool progress, upload progress, and action outcomes; honor reduced motion.
- Imagery/iconography: use the host icon system when available; never load arbitrary model-generated remote Markdown images.

## Components

- Existing patterns to preserve as behavioral evidence: streaming Markdown, paginated message history, multimodal composition, editable voice transcripts, visible tool activity, resumable streams, attachment previews, and editable confirm/cancel action cards.
- New/changed components: headless assistant store, assistant shell, conversation thread, message-part renderers, multimodal composer, thinking disclosure, tool activity, citations, action workspace, error recovery, plugin slots, host-context badges, and developer inspectors.
- Variants and states: inline, drawer, side panel, full-screen tab, and floating panel; signed out, disabled by host, loading history, streaming, interrupted, offline, uploading, transcribing, permission denied, awaiting confirmation, applying, partial failure, applied, cancelled, and undo available.
- Token/component ownership: the framework owns semantic token names and slot contracts; host applications override values or renderers without forking runtime state.

## Accessibility

- Target standard: WCAG 2.2 AA for the default web component kit.
- Keyboard/focus behavior: composer, attachment controls, stop/regenerate, thinking disclosure, tool details, citations, and action controls must be reachable, labelled, and visibly focused.
- Contrast/readability: permission, confirmation, and error states never rely on color alone.
- Screen-reader semantics: streaming and tool status use restrained live regions; disclosures expose expanded state; action cards announce current state and available operations.
- Reduced motion and sensory considerations: waveform, loading, and streaming animations simplify or pause under reduced-motion preferences.

## Responsive behavior

- Supported breakpoints/devices: primary web targets are 360–430 px mobile widths and 320–720 px embedded/desktop panels; contracts remain platform-neutral for native clients.
- Layout adaptations: shells respect safe areas and keyboard insets; the composer pins only when the host container permits it; tables and domain cards provide narrow-width fallbacks.
- Touch/hover differences: touch targets remain at least 44 px; icon-only actions expose labels and desktop tooltips.

## Interaction states

- Loading: distinguish history loading, sending, model streaming, tool execution, upload processing, transcription, and action application.
- Empty: show host-provided starter prompts and current-context hints, never fabricated conversation content.
- Error: preserve the draft and safe attachment metadata; explain whether retry, reconcile, edit, or cancellation is available.
- Success: applied action cards show the user-facing outcome and invoke an explicit host refresh callback.
- Disabled: expose the reason visually and to assistive technology.
- Offline/slow network: retain existing messages, stop indeterminate loading, and offer bounded reconnection or retry.

## Content voice

- Tone: concise, calm, and transparent. The first reference locale is Simplified Chinese, but all default copy MUST be replaceable through localization resources; domain terminology comes from the host plugin.
- Terminology: “助手”, “正在思考”, “正在查看”, “待确认”, “确认”, “修改”, “取消”, “已应用”, “恢复回复”, “引用来源”.
- Microcopy rules: describe user-facing activity and outcomes rather than internal function names. Thinking UI may show stage summaries, elapsed time, and tool intent, but never raw chain-of-thought.

## Implementation constraints

- Framework/styling system: MVP reference client uses Vue 3, TypeScript, and a headless store; the reference backend uses Python/FastAPI. JSON Schema and the event protocol are the cross-language source of truth.
- Design-token constraints: semantic CSS variables and typed slot props; no application-specific palette in framework packages.
- Performance constraints: paginated or virtualized history, bounded attachment previews, stream backpressure, token-budgeted context assembly, and no full-resolution image decoding in message lists.
- Compatibility constraints: authenticated private-data hosts, resumable event streams, host-controlled media URLs, mobile Safari attachment behavior, and plugins installed at release time but enabled or disabled at runtime.
- Test/screenshot expectations: contract fixtures, reducer tests, component interaction and accessibility tests, mobile/desktop visual smoke checks, disconnect recovery, permission denial, and action idempotency.

## Open questions

- [ ] Select the first public reference host and example domain / owner: maintainers / impact: medium.
- [ ] Decide whether a SwiftUI client kit belongs in v0.2 or starts after the v0.1 event protocol freezes / owner: maintainers / impact: medium.
- [ ] Confirm the public package namespace and release strategy / owner: maintainers / impact: low.
