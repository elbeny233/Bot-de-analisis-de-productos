import base64
import hashlib
import hmac
import secrets

ITERATIONS = 600_000


def hash_password(password: str) -> str:
    if not 12 <= len(password) <= 1024:
        raise ValueError("La contraseña debe contener entre 12 y 1024 caracteres")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return "$".join(
        [
            "pbkdf2_sha256",
            str(ITERATIONS),
            base64.b64encode(salt).decode(),
            base64.b64encode(digest).decode(),
        ]
    )


def verify_password(password: str, encoded: str) -> bool:
    if len(password) > 1024:
        return False
    try:
        algorithm, rounds, salt, expected = encoded.split("$")
        count = int(rounds)
        if algorithm != "pbkdf2_sha256" or not 100_000 <= count <= 1_000_000:
            return False
        salt_bytes = base64.b64decode(salt, validate=True)
        digest_bytes = base64.b64decode(expected, validate=True)
        if len(salt_bytes) != 16 or len(digest_bytes) != 32:
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt_bytes, count)
        return hmac.compare_digest(actual, digest_bytes)
    except (ValueError, TypeError):
        return False
