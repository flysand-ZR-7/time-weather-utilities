import sys
import os
from pathlib import Path
import pytest

if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent
    tests_dir = base_dir / "tests"
    sys.path.insert(0, str(base_dir))
    os.chdir(str(base_dir))

    ret = pytest.main(["-v", "--tb=short", str(tests_dir)])
    print(f"Pytest finished with code: {ret}")
    sys.exit(int(ret))
