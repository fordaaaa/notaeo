"""Mac-only supervisor regressions; run through uv after building the sidecar."""
from __future__ import annotations

import os
from pathlib import Path
import shlex
import signal
import subprocess
import tempfile
import time


ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts" / "test_macos_workflows.sh"


def scratch_directories(root: Path) -> set[Path]:
    return set(root.glob("notaeo-workflow-build.*"))


def command(backend: Path) -> list[str]:
    return ["sh", str(RUNNER), "--no-build", "--backend", str(backend)]


def child_is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def main() -> None:
    if not __debug__:
        raise RuntimeError("Run these checks without Python optimization; assertions must remain enabled")
    with tempfile.TemporaryDirectory(prefix="notaeo-runner-regression-") as scratch:
        directory = Path(scratch)
        runner_temp = directory / "runner-temp"
        runner_temp.mkdir(mode=0o700)
        environment = {**os.environ, "TMPDIR": str(runner_temp)}
        baseline = scratch_directories(runner_temp)
        missing = subprocess.run(command(directory / "absent"), env=environment, capture_output=True, text=True, timeout=10, check=False)
        assert missing.returncode == 1
        assert "Packaged backend missing" in missing.stderr
        assert scratch_directories(runner_temp) == baseline
        print("missing fixture: PASS (hard failure, no scratch created)", flush=True)

        for label, body, expected in [
            ("exit-before-ready", "exit 0\n", "stopped before readiness"),
            ("invalid-readiness", "printf '%s\\n' 'RESEARCH_READY http://127.0.0.1:0'\nexec /bin/sleep 120\n", "invalid/non-loopback URL"),
        ]:
            backend = directory / f"{label}.sh"
            backend.write_text("#!/bin/sh\n" + body)
            backend.chmod(0o700)
            result = subprocess.run(command(backend), cwd=ROOT, env=environment, text=True, capture_output=True, timeout=50, check=False)
            assert result.returncode != 0, label
            assert expected in result.stdout + result.stderr, (label, result.stdout, result.stderr)
            assert scratch_directories(runner_temp) == baseline, f"{label} leaked scratch data"
            print(f"{label}: PASS (exit {result.returncode}, scratch removed)", flush=True)

        pid_file = directory / "owned.pid"
        backend = directory / "interrupt.sh"
        backend.write_text("#!/bin/sh\nprintf '%s\\n' \"$$\" > " + shlex.quote(str(pid_file)) + "\nexec /bin/sleep 120\n")
        backend.chmod(0o700)
        process = subprocess.Popen(command(backend), cwd=ROOT, env=environment, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        child_pid: int | None = None
        try:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                assert process.poll() is None, "Runner exited before its synthetic child started"
                if pid_file.exists():
                    recorded = pid_file.read_text().strip()
                    if recorded.isdecimal():
                        child_pid = int(recorded)
                        break
                time.sleep(0.025)
            assert child_pid is not None and child_pid > 1, "Synthetic child did not start"
            process.send_signal(signal.SIGTERM)
            stdout, stderr = process.communicate(timeout=20)
            assert process.returncode != 0, (stdout, stderr)
            assert not child_is_alive(child_pid), "Interrupted runner left its owned child alive"
            assert scratch_directories(runner_temp) == baseline, "Interrupted runner leaked scratch data"
            print(f"interrupted startup: PASS (exit {process.returncode}, child stopped, scratch removed)", flush=True)
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.communicate(timeout=20)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.communicate(timeout=5)
            if child_pid is not None and child_is_alive(child_pid):
                # This PID came only from the synthetic executable created above.
                os.kill(child_pid, signal.SIGKILL)
        assert scratch_directories(runner_temp) == baseline
    print("RUNNER FAILURE CHECKS PASS: four scenarios, no retained child or scratch data")


if __name__ == "__main__":
    main()
