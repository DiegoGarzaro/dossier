"""Application configuration, loaded from DOSSIER_-prefixed environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the application.

    Attributes:
        secret_key (str): Signing key reserved for future use; must be overridden in production.
        data_dir (Path): Directory holding the SQLite database and uploaded files.
        session_idle_days (int): Idle days before a session expires (FR-4).
        max_upload_mb (int): Maximum accepted upload size in megabytes (FR-20).
        max_backup_mb (int): Maximum accepted plaintext backup archive size in
            megabytes, checked on both backup and restore (G-36).
        trust_proxy (bool): Whether the app runs behind a reverse proxy (SEC-8).
        login_max_attempts (int): Consecutive failed logins before an account locks (G-07).
        login_lockout_minutes (int): Minutes an account stays locked after too many failures.
    """

    model_config = SettingsConfigDict(env_prefix="DOSSIER_")

    secret_key: str = "dev-insecure-change-me"
    data_dir: Path = Path("data")
    session_idle_days: int = 14
    max_upload_mb: int = 25
    max_backup_mb: int = 200
    trust_proxy: bool = False
    login_max_attempts: int = 5
    login_lockout_minutes: int = 15

    @property
    def database_url(self) -> str:
        """Async SQLAlchemy URL for the SQLite database.

        Returns:
            str: The sqlite+aiosqlite connection URL.
        """
        return f"sqlite+aiosqlite:///{self.data_dir / 'app.db'}"

    @property
    def uploads_dir(self) -> Path:
        """Directory for uploaded person documents.

        Returns:
            Path: The uploads directory inside the data volume.
        """
        return self.data_dir / "uploads"

    @property
    def photos_dir(self) -> Path:
        """Directory for profile photos.

        Returns:
            Path: The photos directory inside the uploads volume.
        """
        return self.uploads_dir / "_photos"

    @property
    def max_upload_bytes(self) -> int:
        """Maximum upload size in bytes.

        Returns:
            int: The configured limit converted to bytes.
        """
        return self.max_upload_mb * 1024 * 1024

    @property
    def max_backup_bytes(self) -> int:
        """Maximum plaintext backup archive size in bytes.

        Returns:
            int: The configured limit converted to bytes.
        """
        return self.max_backup_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings.

    Returns:
        Settings: The singleton settings instance.
    """
    return Settings()
