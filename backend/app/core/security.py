"""
Security and Cryptographic Utilities.
Enforces standard bcrypt hashing with 12 rounds and constant-time password verification.
"""

import bcrypt

# Pre-computed dummy hash with 12 rounds for constant-time evaluation on nonexistent users
DUMMY_HASH = "$2b$12$e8Y1x9d2sZvZ5u6r0t0LreT7aQ3qD5n9G8w1e7r6t5y4u3i2o1p0a"


def hash_password(password: str) -> str:
    """Hashes a plaintext password using bcrypt with 12 salt rounds."""
    pwd_bytes = password.encode("utf-8")
    if len(pwd_bytes) > 72:
        raise ValueError("Password cannot exceed 72 bytes")
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against a bcrypt hash in constant time."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), hashed_password.encode("utf-8")
        )
    except Exception:
        return False


def dummy_verify_password() -> None:
    """Simulates password verification against dummy hash to mitigate timing attacks."""
    try:
        bcrypt.checkpw(b"dummy_password_verification", DUMMY_HASH.encode("utf-8"))
    except Exception:
        pass
