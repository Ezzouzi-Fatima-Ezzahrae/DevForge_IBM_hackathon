from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parent.parent
ORIGINAL = ROOT / "tests" / "fixtures" / "demo_bug_original.py"
TARGET = ROOT / "backend" / "demo_bug.py"


def restore_demo_bug() -> None:
    """Restore the pristine buggy version used for the demo."""
    shutil.copy2(ORIGINAL, TARGET)


if __name__ == "__main__":
    restore_demo_bug()
    print("Demo bug restored.")