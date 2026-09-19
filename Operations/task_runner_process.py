from __future__ import annotations

import os
import signal
import subprocess
import sys
from pathlib import Path


def get_pid_file_path(running_dir: Path) -> Path:
    return running_dir / "__task_runner_pid__.txt"


def is_process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def kill_process(pid: int) -> None:
    if pid <= 0:
        return

    if sys.platform.startswith("win"):
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            text=True,
            check=False,
        )
        return

    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        return


def kill_active_run_if_present(running_dir: Path) -> None:
    pid_file = get_pid_file_path(running_dir)

    if not pid_file.exists():
        return

    try:
        raw_pid = pid_file.read_text(encoding="utf-8").strip()
        if not raw_pid:
            return

        pid = int(raw_pid)
    except Exception:
        return

    if is_process_alive(pid):
        kill_process(pid)
