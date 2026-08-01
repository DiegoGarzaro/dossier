"""Encrypted backup / restore: one archive holding the full dataset and its
uploaded files (Phase 3, closes G-36).

Unlike the plain JSON export (SEC-7, which withholds `sensitive` field
values by default), an encrypted backup **always** includes them in
plaintext inside the archive — that is the entire point of encrypting the
file: it can safely carry secrets, and a "backup" that silently dropped
them would not be a usable disaster-recovery copy.

The archive itself is a gzipped tar:

```
backup.tar.gz
├── dossier.json        the full dataset export, include_sensitive=True
└── uploads/…            every referenced file, at its path under settings.uploads_dir
```

sealed with `app/core/crypto.py`'s Argon2id + AES-256-GCM construction.
Restoring one goes through `ImportService.apply()` — the same additive,
never-destructive rules as a plain JSON import — after safely extracting
the archive's files onto `settings.uploads_dir` so those rows can point at
real files instead of being reported as unrestorable.
"""

import io
import tarfile
from datetime import datetime
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.crypto import decrypt, encrypt
from app.core.errors import InvalidInputError, PayloadTooLargeError
from app.models.base import utcnow
from app.repositories.app_meta_repo import AppMetaRepository
from app.schemas.export import ExportEnvelope, ImportReport
from app.services.export_service import ExportService
from app.services.import_service import ImportService

LAST_BACKUP_KEY = "last_backup_at"

_JSON_MEMBER = "dossier.json"
_UPLOADS_PREFIX = "uploads/"

MIN_PASSPHRASE_LENGTH = 12
MAX_PASSPHRASE_LENGTH = 1024


def _check_passphrase(passphrase: str) -> None:
    """Enforce the passphrase length bound shared by backup and restore.

    Kept as one function so `POST /api/backup` (a JSON body field) and
    `POST /api/restore` (a multipart form field) apply the identical rule
    instead of declaring it twice and risking drift.

    Args:
        passphrase (str): The candidate passphrase. Never logged or echoed.

    Returns:
        None

    Raises:
        InvalidInputError: The passphrase is shorter than `MIN_PASSPHRASE_LENGTH`
            or longer than `MAX_PASSPHRASE_LENGTH` characters. The message
            never includes the passphrase itself.
    """
    if not (MIN_PASSPHRASE_LENGTH <= len(passphrase) <= MAX_PASSPHRASE_LENGTH):
        raise InvalidInputError(
            f"Passphrase must be between {MIN_PASSPHRASE_LENGTH} and "
            f"{MAX_PASSPHRASE_LENGTH} characters"
        )


class BackupService:
    """Builds and restores encrypted, self-contained backup archives (G-36)."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the service.

        Args:
            session (AsyncSession): The request-scoped database session.
        """
        self._export = ExportService(session)
        self._import = ImportService(session)
        self._app_meta = AppMetaRepository(session)

    async def create(self, passphrase: str) -> tuple[bytes, str]:
        """Build and encrypt a full backup of the vault: data plus every uploaded file.

        Args:
            passphrase (str): The passphrase to encrypt the archive with
                (12-1024 characters). Never logged or included in any error.

        Returns:
            tuple[bytes, str]: (encrypted archive bytes, download filename).

        Raises:
            InvalidInputError: The passphrase fails its length bound.
            PayloadTooLargeError: The plaintext archive exceeds
                `DOSSIER_MAX_BACKUP_MB` — checked before encrypting, since
                AES-GCM here is one-shot and the whole archive passes
                through memory.
        """
        _check_passphrase(passphrase)
        envelope, _ = await self._export.export_dataset(
            include_sensitive=True, include_storage_paths=True
        )
        archive = self._build_archive(envelope)

        settings = get_settings()
        if len(archive) > settings.max_backup_bytes:
            raise PayloadTooLargeError(f"Backup exceeds the {settings.max_backup_mb} MB limit")

        blob = encrypt(archive, passphrase)
        await self._app_meta.set(LAST_BACKUP_KEY, utcnow().isoformat())
        stamp = datetime.now().strftime("%Y-%m-%d")
        return blob, f"dossier-backup-{stamp}.dossier"

    async def restore(self, blob: bytes, passphrase: str) -> ImportReport:
        """Decrypt a backup archive and apply it, restoring data and uploaded files.

        Args:
            blob (bytes): The encrypted archive. The caller (the router) is
                responsible for capping this at `DOSSIER_MAX_BACKUP_MB` while
                streaming the upload in, before it ever reaches this method.
            passphrase (str): The passphrase the archive was encrypted with.
                Never logged or included in any error.

        Returns:
            ImportReport: What was created/restored/skipped — the same
                additive rules as a plain JSON import (`ImportService.apply`).

        Raises:
            InvalidInputError: The passphrase fails its length bound, the
                file isn't a Dossier backup, is an unsupported archive
                version, the passphrase is wrong, or the archive is
                damaged/tampered with.
        """
        _check_passphrase(passphrase)
        archive = decrypt(blob, passphrase)
        envelope = self._extract_archive(archive)
        return await self._import.apply(envelope)

    def _build_archive(self, envelope: ExportEnvelope) -> bytes:
        """Pack the export envelope and every uploaded file it references into a gzipped tar.

        Args:
            envelope (ExportEnvelope): The dataset export, built with
                `include_sensitive=True, include_storage_paths=True` so its
                documents/photo carry real `storage_path`/`photo_path` values.

        Returns:
            bytes: The gzipped tar archive.
        """
        settings = get_settings()
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
            self._add_bytes(tar, _JSON_MEMBER, envelope.model_dump_json(indent=2).encode("utf-8"))
            added: set[str] = set()
            for person in envelope.people:
                if person.photo_path:
                    self._add_upload(tar, settings.uploads_dir, person.photo_path, added)
                for document in person.documents:
                    if document.storage_path:
                        self._add_upload(tar, settings.uploads_dir, document.storage_path, added)
        return buffer.getvalue()

    @staticmethod
    def _add_bytes(tar: tarfile.TarFile, name: str, data: bytes) -> None:
        """Add an in-memory blob to a tar archive as a regular file member.

        Args:
            tar (tarfile.TarFile): The open archive, in write mode.
            name (str): The member name (e.g. "dossier.json").
            data (bytes): The file content.

        Returns:
            None
        """
        info = tarfile.TarInfo(name=name)
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))

    @staticmethod
    def _add_upload(
        tar: tarfile.TarFile, uploads_dir: Path, relative: str, added: set[str]
    ) -> None:
        """Add one uploaded file to the archive under `uploads/<relative>`, at most once.

        Args:
            tar (tarfile.TarFile): The open archive, in write mode.
            uploads_dir (Path): The uploads directory the relative path is under.
            relative (str): The file's path relative to `uploads_dir` (its
                `storage_path`/`photo_path`).
            added (set[str]): Relative paths already added, so a photo that
                happens to equal a document's path is never added twice.

        Returns:
            None
        """
        if relative in added:
            return
        path = uploads_dir / relative
        if path.is_file():
            tar.add(path, arcname=f"{_UPLOADS_PREFIX}{relative}")
            added.add(relative)

    def _extract_archive(self, archive: bytes) -> ExportEnvelope:
        """Safely extract a decrypted archive: the data export in memory, files to disk.

        Rejects any `uploads/` member whose name is absolute, contains `..`,
        or resolves outside `settings.uploads_dir`, and rejects symlinks,
        hardlinks, and device nodes — only regular files are ever written.
        A rejected or unrecoverable member is simply not extracted; its
        document/photo is then reported as unrestorable by
        `ImportService` rather than aborting the whole restore. A file that
        already exists on disk is left alone and never overwritten —
        storage names are random UUIDs, so a collision means it's the same
        file.

        Args:
            archive (bytes): The decrypted gzipped tar.

        Returns:
            ExportEnvelope: The parsed `dossier.json` member.

        Raises:
            InvalidInputError: The archive isn't a valid tar, carries no
                `dossier.json` member, or that member isn't a valid export
                envelope.
        """
        settings = get_settings()
        uploads_root = settings.uploads_dir
        uploads_root.mkdir(parents=True, exist_ok=True)
        resolved_root = uploads_root.resolve()

        envelope_bytes: bytes | None = None
        try:
            with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
                for member in tar.getmembers():
                    if member.isfile() and member.name == _JSON_MEMBER:
                        extracted = tar.extractfile(member)
                        if extracted is not None:
                            envelope_bytes = extracted.read()
                        continue
                    target = self._safe_target(member, uploads_root, resolved_root)
                    if target is None or target.exists():
                        continue
                    extracted = tar.extractfile(member)
                    if extracted is None:
                        continue
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(extracted.read())
        except tarfile.TarError as error:
            raise InvalidInputError(
                "This backup file is not a valid archive and could not be read"
            ) from error

        if envelope_bytes is None:
            raise InvalidInputError("This backup file doesn't contain a Dossier data export")
        try:
            return ExportEnvelope.model_validate_json(envelope_bytes)
        except ValidationError as error:
            raise InvalidInputError("This backup's data export is malformed") from error

    @staticmethod
    def _safe_target(
        member: tarfile.TarInfo, uploads_root: Path, resolved_root: Path
    ) -> Path | None:
        """Resolve an `uploads/` tar member to a safe on-disk path, or None if unsafe.

        Args:
            member (tarfile.TarInfo): The tar member to check.
            uploads_root (Path): The uploads directory (unresolved).
            resolved_root (Path): `uploads_root.resolve()`, precomputed once
                per archive rather than per member.

        Returns:
            Path | None: The safe absolute target path, or None when the
                member is a symlink/hardlink/device/directory, isn't under
                `uploads/`, or would traverse outside `uploads_root`.
        """
        if not member.isfile():
            return None
        name = member.name
        if not name.startswith(_UPLOADS_PREFIX):
            return None
        relative = name[len(_UPLOADS_PREFIX) :]
        if not relative or relative.startswith("/") or ".." in Path(relative).parts:
            return None
        target = (uploads_root / relative).resolve()
        if not target.is_relative_to(resolved_root):
            return None
        return target
