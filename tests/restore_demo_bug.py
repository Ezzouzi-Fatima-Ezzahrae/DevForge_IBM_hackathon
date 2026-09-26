from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parent.parent
ORIGINAL = ROOT / "tests" / "fixtures" / "demo_bug_original.py"
TARGET = ROOT / "backend" / "demo_bug.py"


def restore_demo_bug() -> None:
    """Restore the pristine buggy version used for the demo."""
    # copyfile (not copy2): the file gets a fresh modification time, so Python
    # never reuses a stale compiled copy of the previously patched version.
    shutil.copyfile(ORIGINAL, TARGET)
    for cached in (ROOT / "backend" / "__pycache__").glob("demo_bug*.pyc"):
        cached.unlink()


if __name__ == "__main__":
    restore_demo_bug()
    print("Demo bug restored.")
