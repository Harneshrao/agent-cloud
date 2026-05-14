import hashlib

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 256


def validate_password(password: str) -> None:
    if password is None:
        raise ValueError("Password cannot be empty.")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError("Password must be at least 8 characters.")
    if len(password) > MAX_PASSWORD_LENGTH:
        raise ValueError("Password cannot exceed 256 characters.")


def hash_password(password: str) -> str:
    validate_password(password)
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    return hashlib.sha256(password.encode()).hexdigest() == hashed
