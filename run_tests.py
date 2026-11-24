import sys
import pytest

if __name__ == "__main__":
    ret = pytest.main(["-v", "--tb=short", "tests"])
    print(f"Pytest finished with code: {ret}")
    sys.exit(int(ret))
