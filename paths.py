import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def get_data_dir() -> Path:
    """Resolve the allowed data/ directory, overridable via PREPDESK_DATA_DIR for tests."""
    env_dir = os.environ.get("PREPDESK_DATA_DIR")
    if env_dir:
        return Path(env_dir).resolve()
    return (BASE_DIR / "data").resolve()


def safe_data_path(path: str | Path) -> Path:
    """Resolve path and ensure it lies strictly inside the project's data/ directory."""
    data_dir = get_data_dir()
    target = Path(path)
    if target.is_absolute():
        resolved = target.resolve()
    else:
        project_root = data_dir.parent if data_dir.name == "data" else BASE_DIR
        resolved = (project_root / target).resolve()

    if not resolved.is_relative_to(data_dir):
        raise ValueError(
            f"Access denied: '{path}' resolves outside the allowed data/ directory."
        )
    return resolved
