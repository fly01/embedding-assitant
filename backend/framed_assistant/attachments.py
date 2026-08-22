from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from .errors import ValidationError
from .models import Attachment, AttachmentKind, HostContext, Transcript
from .store import Store

MAX_ATTACHMENT_BYTES = 50 * 1024 * 1024


class AttachmentService:
    def __init__(self, store: Store):
        self.store = store

    async def upload(
        self,
        host: HostContext,
        file: UploadFile,
        *,
        conversation_id: str | None,
        source: str,
    ) -> Attachment:
        if file.filename is None:
            raise ValidationError("Attachment filename is required")
        content = await file.read()
        if len(content) > MAX_ATTACHMENT_BYTES:
            raise ValidationError("Attachment exceeds the 50 MiB limit")

        storage_path = self.store.attachments_dir / f"{uuid4().hex}-{Path(file.filename).name}"
        storage_path.write_bytes(content)
        kind = attachment_kind(file.content_type or "application/octet-stream", file.filename)
        attachment = self.store.create_attachment(
            host,
            conversation_id=conversation_id,
            kind=kind,
            name=Path(file.filename).name,
            mime_type=file.content_type or "application/octet-stream",
            size_bytes=len(content),
            source=source,
            storage_path=storage_path,
        )
        self._emit(attachment, "attachment.upload.updated", {"status": "uploaded"})
        return self.process(host, attachment.id)

    def process(self, host: HostContext, attachment_id: str) -> Attachment:
        attachment, storage_path = self.store.get_attachment(host, attachment_id)
        self.store.update_attachment(attachment.id, processing_status="processing", metadata={})
        self._emit(attachment, "attachment.processing.updated", {"status": "processing"})

        if attachment.kind is AttachmentKind.TEXT:
            result = {"text": storage_path.read_text(encoding="utf-8")[:20_000]}
            processor = "text-extract"
        elif attachment.kind is AttachmentKind.IMAGE:
            result = {"caption": f"Image attachment {attachment.name}"}
            processor = "image-metadata"
        elif attachment.kind is AttachmentKind.AUDIO:
            result = {"duration": None, "playable": True}
            processor = "audio-metadata"
        elif attachment.kind in {AttachmentKind.DOCUMENT, AttachmentKind.SPREADSHEET}:
            result = {"name": attachment.name, "size_bytes": attachment.size_bytes}
            processor = "file-metadata"
        else:
            self.store.update_attachment(attachment.id, processing_status="unsupported", metadata={})
            self._emit(attachment, "attachment.processing.updated", {"status": "unsupported"})
            return self.store.get_attachment(host, attachment.id)[0]

        self.store.add_attachment_result(
            attachment.id,
            processor=processor,
            processor_version="0.1",
            status="ready",
            result=result,
            warnings=[],
        )
        self.store.update_attachment(attachment.id, processing_status="ready", metadata=result)
        processed = self.store.get_attachment(host, attachment.id)[0]
        self._emit(processed, "attachment.processing.updated", {"status": "ready", "result": result})
        return processed

    def transcribe(self, host: HostContext, attachment_id: str) -> Transcript:
        attachment, _ = self.store.get_attachment(host, attachment_id)
        if attachment.kind is not AttachmentKind.AUDIO:
            raise ValidationError("Only audio attachments can be transcribed")
        self._emit(attachment, "transcription.started", {})
        transcript = self.store.create_transcript(
            attachment.id,
            f"Voice message from {attachment.name}",
            adapter="mock-batch-asr",
            is_user_correction=False,
        )
        self._emit(
            attachment,
            "transcription.completed",
            {"transcript": transcript.model_dump(mode="json")},
        )
        return transcript

    def correct_transcript(self, host: HostContext, attachment_id: str, text: str) -> Transcript:
        attachment, _ = self.store.get_attachment(host, attachment_id)
        transcript = self.store.create_transcript(
            attachment.id,
            text,
            adapter="user-correction",
            is_user_correction=True,
        )
        if attachment.conversation_id:
            self.store.invalidate_context(attachment.conversation_id)
        self._emit(
            attachment,
            "transcription.completed",
            {"transcript": transcript.model_dump(mode="json")},
        )
        return transcript

    def _emit(self, attachment: Attachment, event_type: str, payload: dict[str, object]) -> None:
        self.store.append_event(
            scope_kind="attachment",
            scope_id=attachment.id,
            event_type=event_type,
            payload=payload,
            conversation_id=attachment.conversation_id,
        )


def attachment_kind(mime_type: str, filename: str) -> AttachmentKind:
    if mime_type.startswith("image/"):
        return AttachmentKind.IMAGE
    if mime_type.startswith("audio/"):
        return AttachmentKind.AUDIO
    if mime_type.startswith("text/"):
        return AttachmentKind.TEXT
    suffix = Path(filename).suffix.lower()
    if suffix in {".csv", ".xls", ".xlsx"}:
        return AttachmentKind.SPREADSHEET
    if suffix in {".pdf", ".doc", ".docx"}:
        return AttachmentKind.DOCUMENT
    if suffix in {".zip", ".tar", ".gz"}:
        return AttachmentKind.ARCHIVE
    return AttachmentKind.UNKNOWN
