"""Exercise the documented public workflow using only a built wheel."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def _run(
    command: list[str],
    *,
    cwd: Path,
    expected: int = 0,
    environment: dict[str, str],
) -> str:
    rendered = " ".join(command)
    print(f"$ {rendered}", flush=True)
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    output = completed.stdout + completed.stderr
    print(output.rstrip(), flush=True)
    print(f"[exit {completed.returncode}; expected {expected}]", flush=True)
    if completed.returncode != expected:
        raise RuntimeError(f"command returned {completed.returncode}, expected {expected}")
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("wheel", type=Path)
    arguments = parser.parse_args()
    wheel = arguments.wheel.resolve()
    if not wheel.is_file():
        parser.error(f"wheel does not exist: {wheel}")

    with tempfile.TemporaryDirectory(prefix="agent-effects-clean-room-") as temporary:
        root = Path(temporary)
        virtualenv = root / ".venv"
        subprocess.run([sys.executable, "-m", "venv", str(virtualenv)], check=True)
        python = virtualenv / "bin" / "python"
        executable = virtualenv / "bin" / "agent-effects"
        environment = dict(os.environ)
        environment.pop("PYTHONPATH", None)
        environment.pop("PYTEST_DISABLE_PLUGIN_AUTOLOAD", None)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"

        _run(
            [str(python), "-m", "pip", "install", str(wheel), "pytest"],
            cwd=root,
            environment=environment,
        )
        identity_code = (
            "import agent_effects, importlib.metadata, sys; "
            "print('PACKAGE_VERSION=' + importlib.metadata.version('agent-effects-testkit')); "
            "print('PACKAGE_FILE=' + str(agent_effects.__file__)); "
            "print('SYS_PATH_0=' + sys.path[0])"
        )
        _run(
            [str(python), "-c", identity_code],
            cwd=root,
            environment=environment,
        )
        plugin_smoke = root / "plugin-smoke"
        plugin_smoke.mkdir()
        (plugin_smoke / "test_plugin.py").write_text(
            "def test_installed_plugin(agent_effects_runner):\n"
            "    assert agent_effects_runner.__class__.__name__ == 'TrialRunner'\n",
            encoding="utf-8",
        )
        _run(
            [str(python), "-m", "pytest", "-q"],
            cwd=plugin_smoke,
            environment=environment,
        )
        _run(
            [str(executable), "init", "demo", "--template", "lost-ack"],
            cwd=root,
            environment=environment,
        )
        demo = root / "demo"
        first_test = _run(
            [str(python), "-m", "pytest", "-q"],
            cwd=demo,
            expected=1,
            environment=environment,
        )
        if "duplicate effect detected after timeout_after_commit" not in first_test:
            raise RuntimeError("initial test did not fail for the duplicate-effect reason")
        bundles = sorted((demo / ".agent-effects" / "failures").iterdir())
        if len(bundles) != 1:
            raise RuntimeError(f"expected one bundle, found {len(bundles)}")
        bundle = bundles[0]
        for command in (
            [str(executable), "bundle", "verify", str(bundle)],
            [str(executable), "bundle", "inspect", str(bundle)],
            [str(executable), "reproduce", "--dry-run", str(bundle)],
            [str(executable), "reproduce", str(bundle)],
        ):
            _run(command, cwd=demo, environment=environment)

        policy = demo / "policy.py"
        current = policy.read_text(encoding="utf-8")
        policy.write_text(
            current.replace("STABLE_IDEMPOTENCY = False", "STABLE_IDEMPOTENCY = True"),
            encoding="utf-8",
        )
        _run(
            [str(python), "-m", "pytest", "-q"],
            cwd=demo,
            environment=environment,
        )
        print("CLEAN_ROOM_ACCEPTANCE=PASS", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
