#!/usr/bin/env python3
"""Validate that public documentation is self-contained and release-ready."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DOCS = (
    ROOT / "README.md",
    ROOT / "DESIGN.md",
    ROOT / "docs" / "mvp-spec.md",
)

FORBIDDEN_PATTERNS = {
    "absolute user-home path": re.compile(
        r"(?:/Users/|/home/|[A-Za-z]:\\Users\\|~/)", re.IGNORECASE
    ),
    "local file URI": re.compile(r"file://", re.IGNORECASE),
    "unexplained parent-workspace reference": re.compile(
        r"\.\./(?!DESIGN\.md(?:\b|#)|README\.md(?:\b|#))", re.IGNORECASE
    ),
}

REQUIRED_HEADINGS = {
    "README.md": (
        "# Framed Assistant",
        "## Project status",
        "## Why Framed Assistant?",
        "## Architecture",
        "## MVP scope",
        "## Documentation",
        "## Contributing",
        "## License",
    ),
    "DESIGN.md": (
        "# Design",
        "## Source of truth",
        "## Design principles",
        "## Components",
        "## Accessibility",
        "## Implementation constraints",
        "## Open questions",
    ),
    "mvp-spec.md": (
        "# Framed Assistant MVP Specification",
        "## Status",
        "## Abstract",
        "## Normative language",
        "## Goals",
        "## Non-goals",
        "## Terminology",
        "## Architecture",
        "## Protocol",
        "## Module specifications",
        "## Official capability packages",
        "## Host integration manifest and plugin lifecycle",
        "## Security and privacy",
        "## Conformance",
        "## MVP acceptance criteria",
    ),
}

REQUIRED_SPEC_TERMS = (
    "M0",
    "M14",
    "Headless",
    "Multimodal Input",
    "Context Management",
    "Knowledge & Retrieval",
    "Memory",
    "Action Workspace",
    "Safety & Governance",
    "Developer Toolkit",
    "image",
    "voice",
    "thinking status",
    "raw_trace",
    "reasoning.trace.delta",
    "reasoning.trace.unavailable",
    "reasoning_visibility",
    "MUST NOT synthesize a raw trace",
    "requires explicit Host policy plus viewer authorization",
    "is always excluded from normal logs, Memory, Context Summary",
    "Separate Host trace retention makes it eligible only for authorized display, export, and deletion",
    "scope: {",
    "applyAction(action: ExecutableAction)",
    'schema_version: "0.1"\napplication:',
    '"schema_version": "0.1",\n  "id": "org.example.sample-plugin"',
    '"data_schema_version": "1"',
    "conversation_mode: single | multiple",
    "multiple Host-managed Conversations",
    "context_profile: lite | balanced | durable",
    "Profiles are policy presets, not separate implementations",
    "Context Compiler",
    "Context Manifest",
    "Working Ledger",
    "Host Integration Manifest",
    "Run Host Context",
    "EmbeddedAssistant.create",
    "undoAction",
    "private Attachment bytes",
    "Integration Generator",
    "custom Domain Plugin is optional",
    "MUST NOT activate write operations automatically",
    "blocked_plugin_disabled",
    "blocked_plugin_disabled -> policy_evaluating",
    "action_type`-keyed Action renderer slots",
    "MUST NOT auto-register reference or sample plugins",
    "advertises no reference-Host tools",
    "Host-driven Conversation switching",
    "Plugin data migration, automated upgrade, and rollback orchestration are deferred beyond v0.1",
    "MessageTimeDivider",
    "inactivity_threshold_seconds: 300",
    "voice_message",
    "live_dictation",
    "transcription.started",
    "transcription.delta",
    "transcription.completed",
    "transcription.failed",
    "voice_input:",
    "modes: [voice_message, live_dictation]",
    "Live-dictation audio is ephemeral by default",
    "Voice-message audio is persisted as private user content",
    "Privacy Center",
    "The default UI uses only two surfaces",
    "PrivacyJobStatus",
    "Privacy Resource",
    "Privacy Job",
    "privacy.job.updated",
    "/v1/assistant/privacy/resources",
    "/v1/assistant/privacy/exports",
    "/v1/assistant/privacy/deletions/preview",
    "never report full success when any registered processor is unresolved",
    "Attachment Asset",
    "Draft Attachment",
    "Message Attachment Part",
    "Attachment Processing Result",
    "Attachment Promotion",
    "AttachmentTray",
    "AttachmentGrid",
    "AttachmentLightbox",
    "tray_position: inside_composer_above_text",
    "selection_mode: append",
    "max_count: 8",
    "required_attachment_failure: ask_user",
    "source_attachment_refs",
    "promoted_attachment_refs",
    "attachment.upload.updated",
    "attachment.processing.updated",
    "Execution mode",
    "Auto-apply policy",
    "execution_mode: read_only | confirm_each | auto_apply_allowlist",
    "action.policy_evaluated",
    "action.auto_applying",
    "confirm_each",
    "auto_apply_allowlist",
    "AutoAppliedResultCard",
    "ExecutionModeSettings",
    "Host Data Write Tool",
    "Host data adapter",
    "HostDataToolSettings",
    "host_data_tools:",
    "enabled: false",
    "raw_sql: false",
    "getDataToolCapabilities",
    "absent from model manifests by default",
    "arbitrary SQL",
    "Wave 0 — Contract foundation",
    "Wave 1 — Platform kernel",
    "Wave 2 — Experience and capability packages",
    "Wave 3 — Reference integration and cross-module proof",
    "A Wave advances only when its Exit Gate passes",
    "Domain-specific schemas and exceptions remain in Host Integration Manifests or optional Domain Plugins",
    "C0. Protocol and schema conformance",
    "C9. End-to-end and portability conformance",
    "C7a. Safety and Privacy baseline",
    "C7b. Action Workspace integration",
    "Multiple Conversation continuity",
    "Reasoning disclosure lifecycle",
    "Version migration and rollback",
    "release time",
    "runtime",
    "MUST NOT delete or rewrite original messages",
)

OFFICIAL_CAPABILITY_PACKAGES = (
    "Essentials",
    "Multimodal Input",
    "Context Management",
    "Knowledge & Retrieval",
    "Memory",
    "Action Workspace",
    "Safety & Governance",
    "Developer Toolkit",
)

REASONING_DISCLOSURE_LEVELS = (
    "hidden",
    "status",
    "contextual",
    "activity",
    "developer",
    "raw_trace",
)

CONTEXT_PROFILES = (
    "lite",
    "balanced",
    "durable",
)

HOST_INTEGRATION_LEVELS = (
    "Level 0",
    "Level 1",
    "Level 2",
    "Level 3",
)

ACTION_EXECUTION_MODES = (
    "read_only",
    "confirm_each",
    "auto_apply_allowlist",
)

CONFORMANCE_SUITE_IDS = tuple(str(index) for index in range(10))

MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def validate_file(path: Path, failures: list[str]) -> str:
    if not path.exists():
        failures.append(f"missing required public document: {path.relative_to(ROOT)}")
        return ""

    text = path.read_text(encoding="utf-8")
    relative = path.relative_to(ROOT)

    for label, pattern in FORBIDDEN_PATTERNS.items():
        for match in pattern.finditer(text):
            failures.append(
                f"{relative}:{line_number(text, match.start())}: forbidden {label}: {match.group(0)!r}"
            )

    for number, line in enumerate(text.splitlines(), start=1):
        if line.endswith((" ", "\t")):
            failures.append(f"{relative}:{number}: trailing whitespace")

    if text.count("```") % 2:
        failures.append(f"{relative}: unbalanced fenced code block")

    for heading in REQUIRED_HEADINGS[path.name]:
        if heading not in text:
            failures.append(f"{relative}: missing required heading {heading!r}")

    for match in MARKDOWN_LINK.finditer(text):
        target = match.group(1).strip()
        if not target or target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        target_path = target.split("#", 1)[0]
        resolved = (path.parent / target_path).resolve()
        try:
            resolved.relative_to(ROOT)
        except ValueError:
            failures.append(
                f"{relative}:{line_number(text, match.start())}: local link escapes repository {target!r}"
            )
            continue
        if not resolved.exists():
            failures.append(
                f"{relative}:{line_number(text, match.start())}: broken local link {target!r}"
            )

    return text


def main() -> int:
    failures: list[str] = []
    texts = {path.name: validate_file(path, failures) for path in PUBLIC_DOCS}
    spec = texts.get("mvp-spec.md", "")

    module_ids = re.findall(r"^### M(\d+)\.", spec, flags=re.MULTILINE)
    expected_ids = [str(index) for index in range(15)]
    if module_ids != expected_ids:
        failures.append(
            "docs/mvp-spec.md: module headings must appear exactly once and in order from M0 to M14 "
            f"(found {module_ids})"
        )

    for term in REQUIRED_SPEC_TERMS:
        if term not in spec:
            failures.append(f"docs/mvp-spec.md: missing preserved requirement {term!r}")

    try:
        package_section = spec.split("## Official capability packages", 1)[1].split(
            "## Host integration manifest and plugin lifecycle", 1
        )[0]
    except IndexError:
        package_section = ""
    package_rows = tuple(
        match.group(1)
        for match in re.finditer(r"^\| ([^|]+?) \|", package_section, flags=re.MULTILINE)
        if match.group(1) not in {"Package", "---"}
    )
    if package_rows != OFFICIAL_CAPABILITY_PACKAGES:
        failures.append(
            "docs/mvp-spec.md: official capability package table must contain exactly the eight "
            f"approved packages in order (found {package_rows})"
        )

    try:
        disclosure_section = spec.split("### Reasoning disclosure levels", 1)[1].split(
            "Minimum behavior:", 1
        )[0]
    except IndexError:
        disclosure_section = ""
    disclosure_rows = tuple(
        match.group(1)
        for match in re.finditer(
            r"^\| `([^`]+)` \|", disclosure_section, flags=re.MULTILINE
        )
    )
    if disclosure_rows != REASONING_DISCLOSURE_LEVELS:
        failures.append(
            "docs/mvp-spec.md: reasoning disclosure table must contain exactly the six approved "
            f"levels in order (found {disclosure_rows})"
        )

    try:
        profile_section = spec.split(
            "All profiles use one Context Compiler", 1
        )[1].split("Profiles are policy presets", 1)[0]
    except IndexError:
        profile_section = ""
    profile_rows = tuple(
        match.group(1)
        for match in re.finditer(r"^- `([^`]+)`:", profile_section, flags=re.MULTILINE)
    )
    if profile_rows != CONTEXT_PROFILES:
        failures.append(
            "docs/mvp-spec.md: context profile definitions must contain exactly lite, balanced, "
            f"and durable in order (found {profile_rows})"
        )

    try:
        integration_section = spec.split("### Host integration levels", 1)[1].split(
            "### Core entities", 1
        )[0]
    except IndexError:
        integration_section = ""
    integration_rows = tuple(
        match.group(1)
        for match in re.finditer(
            r"^\| `([^`]+)` \|", integration_section, flags=re.MULTILINE
        )
    )
    if integration_rows != HOST_INTEGRATION_LEVELS:
        failures.append(
            "docs/mvp-spec.md: Host integration table must contain exactly Level 0 through "
            f"Level 3 in order (found {integration_rows})"
        )

    try:
        execution_section = spec.split("### Action execution modes", 1)[1].split(
            "### Core entities", 1
        )[0]
    except IndexError:
        execution_section = ""
    execution_modes = tuple(
        match.group(1)
        for match in re.finditer(r"^- `([^`]+)`:", execution_section, flags=re.MULTILINE)
    )
    if execution_modes != ACTION_EXECUTION_MODES:
        failures.append(
            "docs/mvp-spec.md: Action execution modes must contain exactly read_only, "
            f"confirm_each, and auto_apply_allowlist in order (found {execution_modes})"
        )

    conformance_ids = tuple(
        re.findall(r"^### C(\d+)\.", spec, flags=re.MULTILINE)
    )
    if conformance_ids != CONFORMANCE_SUITE_IDS:
        failures.append(
            "docs/mvp-spec.md: conformance suites must appear exactly once and in order from "
            f"C0 to C9 (found {conformance_ids})"
        )

    if failures:
        print("Public documentation check failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Public documentation check passed for README.md, DESIGN.md, and docs/mvp-spec.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
