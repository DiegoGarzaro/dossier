"""Encrypted backup archive format: Argon2id key derivation + AES-256-GCM (G-36).

Pure, unit-testable — no DB, no FastAPI. `app/services/backup_service.py` is
the only caller.

Byte layout (a 46-byte header, then the AES-256-GCM ciphertext with its
16-byte tag appended):

```
offset size  field
0      8     magic          b"DOSSIER1"
8      1     version        uint8, currently 1
9      4     time_cost      uint32 big-endian
13     4     memory_cost    uint32 big-endian (KiB)
17     1     parallelism    uint8
18     16    salt           os.urandom
34     12    nonce          os.urandom
46     ...   AES-256-GCM ciphertext, with its 16-byte tag appended
```

The entire 46-byte header is passed as AES-GCM's associated data (AAD) on
both `encrypt` and `decrypt`. That binds the KDF parameters to the
ciphertext they produced: tampering with so much as one byte of the header
(e.g. lowering `time_cost` to make a brute-force attack cheaper) changes the
AAD, so GCM authentication fails even if the attacker also recomputes a key
from the tampered parameters. Nobody can hand back a file with weaker KDF
settings and have us honor them.

The key is derived fresh on every call with Argon2id
(`argon2.low_level.hash_secret_raw`, `Type.ID`, `hash_len=32`). `decrypt`
reads the cost parameters back from the header rather than assuming
today's defaults, so a future change to `DEFAULT_*` never breaks decrypting
an older archive.

Those cost parameters come straight from whatever file was posted, so
`decrypt` bounds-checks them (`_MIN/MAX_*` below) before ever touching
Argon2. The AAD binding stops a *downgrade* of someone else's archive, but
it can't stop an attacker from encrypting their own file with an absurd
`memory_cost` (a `uint32`, so up to ~4 TiB) — and the expensive allocation
would happen before GCM authentication could possibly fail, so
authentication can never rescue work that already happened. The bounds are
checked unconditionally, before deriving anything, regardless of whether
the file later turns out to be authentic.
"""

import os
import struct

from argon2.low_level import Type, hash_secret_raw
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.errors import InvalidInputError

MAGIC = b"DOSSIER1"
VERSION = 1

# Argon2id defaults (time_cost, memory_cost in KiB, parallelism). Chosen to
# cost roughly a second of single-user CPU/RAM on modest hardware, which is
# the point: a stolen archive is expensive to brute-force offline.
DEFAULT_TIME_COST = 3
DEFAULT_MEMORY_COST = 65536  # KiB = 64 MiB
DEFAULT_PARALLELISM = 4

# Sane bounds for header-supplied Argon2 cost parameters (see module
# docstring): generous enough that a future increase to the defaults above
# still decrypts on an older build, but nowhere near enough to let a small
# hostile file demand gigabytes of RAM or minutes of CPU before it's even
# been authenticated.
_MIN_TIME_COST = 1
_MAX_TIME_COST = 10
_MIN_MEMORY_COST = 8  # KiB
_MAX_MEMORY_COST = 262144  # KiB = 256 MiB
_MIN_PARALLELISM = 1
_MAX_PARALLELISM = 16

_KEY_LEN = 32
_SALT_LEN = 16
_NONCE_LEN = 12
# magic(8s) + version(B) + time_cost(I) + memory_cost(I) + parallelism(B), big-endian.
_PREFIX = struct.Struct(">8sBIIB")
_HEADER_LEN = _PREFIX.size + _SALT_LEN + _NONCE_LEN  # 18 + 16 + 12 = 46


def _derive_key(
    passphrase: str, salt: bytes, time_cost: int, memory_cost: int, parallelism: int
) -> bytes:
    """Derive a 256-bit AES key from a passphrase with Argon2id.

    Args:
        passphrase (str): The user-supplied passphrase.
        salt (bytes): The 16-byte per-archive salt.
        time_cost (int): Argon2 iteration count.
        memory_cost (int): Argon2 memory cost in KiB.
        parallelism (int): Argon2 parallelism (lanes).

    Returns:
        bytes: A 32-byte key suitable for AES-256-GCM.
    """
    return hash_secret_raw(
        secret=passphrase.encode("utf-8"),
        salt=salt,
        time_cost=time_cost,
        memory_cost=memory_cost,
        parallelism=parallelism,
        hash_len=_KEY_LEN,
        type=Type.ID,
    )


def _check_kdf_params(time_cost: int, memory_cost: int, parallelism: int) -> None:
    """Reject Argon2 cost parameters outside a sane range, before deriving anything.

    Must run before `_derive_key` is ever called for these values — see the
    module docstring for why authentication can't substitute for this check.

    Args:
        time_cost (int): Argon2 iteration count read from the header.
        memory_cost (int): Argon2 memory cost in KiB read from the header.
        parallelism (int): Argon2 parallelism read from the header.

    Returns:
        None

    Raises:
        InvalidInputError: Any parameter falls outside its allowed range.
            The message never echoes the offending values back — that would
            imply they were actually attempted.
    """
    in_range = (
        _MIN_TIME_COST <= time_cost <= _MAX_TIME_COST
        and _MIN_MEMORY_COST <= memory_cost <= _MAX_MEMORY_COST
        and _MIN_PARALLELISM <= parallelism <= _MAX_PARALLELISM
    )
    if not in_range:
        raise InvalidInputError("This backup declares unsupported encryption parameters")


def encrypt(
    plaintext: bytes,
    passphrase: str,
    *,
    time_cost: int = DEFAULT_TIME_COST,
    memory_cost: int = DEFAULT_MEMORY_COST,
    parallelism: int = DEFAULT_PARALLELISM,
) -> bytes:
    """Encrypt plaintext into a self-describing Dossier backup archive.

    A fresh random `salt` and `nonce` are drawn from `os.urandom` on every
    call and are never reused.

    Args:
        plaintext (bytes): The data to encrypt (a gzipped tar, for backups).
        passphrase (str): The passphrase to derive the key from. Never
            logged or included in any returned/raised value.
        time_cost (int): Argon2 iteration count to record in the header.
        memory_cost (int): Argon2 memory cost in KiB to record in the header.
        parallelism (int): Argon2 parallelism to record in the header.

    Returns:
        bytes: The 46-byte header followed by the AES-256-GCM ciphertext
            (tag included).

    Raises:
        InvalidInputError: A cost parameter falls outside the range `decrypt`
            accepts, which would produce an unreadable archive.
    """
    # Same bounds as on the way in, so this can never mint an archive that
    # `decrypt` would refuse to open — a backup nobody can read is worse than
    # no backup at all.
    _check_kdf_params(time_cost, memory_cost, parallelism)
    salt = os.urandom(_SALT_LEN)
    nonce = os.urandom(_NONCE_LEN)
    header = _PREFIX.pack(MAGIC, VERSION, time_cost, memory_cost, parallelism) + salt + nonce
    key = _derive_key(passphrase, salt, time_cost, memory_cost, parallelism)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, header)
    return header + ciphertext


def decrypt(blob: bytes, passphrase: str) -> bytes:
    """Decrypt a Dossier backup archive produced by `encrypt`.

    The magic bytes are checked first, before the version and before any
    Argon2 work — a file that isn't a Dossier backup is rejected instantly
    rather than costing 64 MiB and roughly a second of CPU to find out.

    Args:
        blob (bytes): The full archive: header + ciphertext.
        passphrase (str): The passphrase to attempt.

    Returns:
        bytes: The decrypted plaintext.

    Raises:
        InvalidInputError: The file is too short, isn't a Dossier archive
            (bad magic), was made by an unsupported archive version, declares
            Argon2 cost parameters outside the accepted range, or the
            passphrase is wrong / the file is damaged or tampered with (an
            AES-GCM tag mismatch) — the last two are reported identically so
            a wrong guess can't be distinguished from corruption.
    """
    if len(blob) < _HEADER_LEN or blob[:8] != MAGIC:
        raise InvalidInputError("This doesn't look like a Dossier backup file")
    version = blob[8]
    if version != VERSION:
        raise InvalidInputError("This backup was made by an unsupported archive version")

    header = blob[:_HEADER_LEN]
    _, _, time_cost, memory_cost, parallelism = _PREFIX.unpack(header[: _PREFIX.size])
    # Bounds-checked before touching Argon2: these three values came from the
    # file itself, and deriving with them is the expensive step (see module
    # docstring) — it must never run on unbounded, attacker-chosen input.
    _check_kdf_params(time_cost, memory_cost, parallelism)
    salt = header[_PREFIX.size : _PREFIX.size + _SALT_LEN]
    nonce = header[_PREFIX.size + _SALT_LEN : _HEADER_LEN]
    ciphertext = blob[_HEADER_LEN:]

    key = _derive_key(passphrase, salt, time_cost, memory_cost, parallelism)
    try:
        return AESGCM(key).decrypt(nonce, ciphertext, header)
    except InvalidTag as error:
        raise InvalidInputError("Wrong passphrase, or this backup file is damaged") from error
