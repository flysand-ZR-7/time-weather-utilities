import sys
import os
import io
from contextlib import redirect_stdout, redirect_stderr
import pytest

if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf), redirect_stderr(buf):
        try:
            ret = pytest.main(["-v", "--tb=short", "tests"])
        except Exception as e:
            ret = 99
            print(f"Exception running pytest: {e}")

    output = buf.getvalue()
    print(output)

    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if summary_path:
        try:
            with open(summary_path, "a", encoding="utf-8") as f:
                f.write(f"### Pytest Run Summary\nExit code: {ret}\n```\n{output}\n```\n")
        except Exception as err:
            print(f"Could not write to summary: {err}")

    sys.exit(int(ret))
