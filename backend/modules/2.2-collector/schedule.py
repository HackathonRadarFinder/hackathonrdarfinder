"""One-shot scheduled raw collection. No scheduler runs inside the web process."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from collector_engine.scheduler import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
