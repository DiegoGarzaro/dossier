"""Encrypted backup request schema (G-36)."""

from pydantic import BaseModel


class BackupRequest(BaseModel):
    """Request body for `POST /api/backup`.

    The passphrase's length bound (12-1024 characters) is enforced by
    `BackupService`, not a Pydantic `Field` constraint here: the identical
    rule also has to apply to the multipart form field on `POST /api/restore`,
    so it lives once, in the service both routes call, instead of being
    declared twice and risking drift.
    """

    passphrase: str
