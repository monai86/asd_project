from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from runtime_support import validation_error  # noqa: E402


def test_supported_python_versions_are_accepted():
    assert validation_error((3, 11)) is None
    assert validation_error((3, 12)) is None
    assert validation_error((3, 13)) is None


def test_unsupported_old_python_is_rejected():
    assert "supports Python" in validation_error((3, 10))


def test_python_314_is_rejected_before_native_imports():
    assert "Python 3.12" in validation_error((3, 14))
    # Verify import isolation in a fresh interpreter. The full suite legitimately
    # imports librosa in earlier acoustic tests, so the parent process module
    # cache cannot prove what importing runtime_support itself loads.
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                "sys.path.insert(0, 'scripts'); "
                "import runtime_support; "
                "raise SystemExit(1 if 'librosa' in sys.modules else 0)"
            ),
        ],
        cwd=ROOT,
        check=False,
    )
    assert result.returncode == 0
