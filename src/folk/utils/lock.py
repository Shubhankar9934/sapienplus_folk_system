"""Cross-process run lock.

A single FOLK ``outputs/`` directory and its ``folk.sqlite`` DB are shared by
every mutating command. Running two of them at once lets the last finalizer
clobber the other's published outputs (prune + republish a different ISO set).

``run_lock`` serialises mutating commands with an atomically-created lockfile
(``outputs/.folk_run.lock``). A second command refuses to start while another
holds the lock, naming the holding process. Locks left behind by a dead process
are reclaimed automatically.
"""

from __future__ import annotations

import json
import os
import socket
from contextlib import contextmanager
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

from folk.utils.logging import get_logger

log = get_logger()

LOCK_FILENAME = ".folk_run.lock"


class RunLockError(RuntimeError):
    """Raised when another FOLK run already holds the lock."""


def _pid_alive(pid: int) -> bool:
    """Best-effort cross-platform check that ``pid`` is a live process."""
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return False
        try:
            code = wintypes.DWORD()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return True  # can't tell - assume alive (fail safe)
            return code.value == STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # exists, owned by another user
    except OSError:
        return True  # ambiguous - assume alive (fail safe)
    return True


def _read_holder(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _write_holder(fd: int, label: str) -> None:
    payload = {
        "pid": os.getpid(),
        "started_at": datetime.now(timezone.utc).isoformat(),
        "label": label,
        "host": socket.gethostname(),
    }
    os.write(fd, json.dumps(payload).encode("utf-8"))


@contextmanager
def run_lock(outputs_dir: Path, label: str) -> Iterator[Path]:
    """Hold an exclusive run lock for the lifetime of the ``with`` block.

    Raises :class:`RunLockError` if another live process already holds it.
    """
    outputs_dir.mkdir(parents=True, exist_ok=True)
    path = outputs_dir / LOCK_FILENAME
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY

    def _acquire() -> int:
        fd = os.open(path, flags)
        try:
            _write_holder(fd, label)
        finally:
            os.close(fd)
        return os.getpid()

    try:
        _acquire()
    except FileExistsError:
        holder = _read_holder(path)
        pid = int(holder.get("pid", -1)) if isinstance(holder, dict) else -1
        if holder is None or not _pid_alive(pid):
            # Stale lock from a dead/unknown process - reclaim it once.
            log.warning(
                f"Reclaiming stale run lock at {path} "
                f"(holder pid={pid if pid > 0 else 'unknown'} not alive).")
            try:
                path.unlink()
            except OSError:
                pass
            try:
                _acquire()
            except FileExistsError as exc:  # lost a race with another reclaimer
                raise RunLockError(
                    f"Another FOLK run just acquired the lock at {path}.") from exc
        else:
            held = holder.get("label", "?")
            since = holder.get("started_at", "?")
            raise RunLockError(
                f"Another FOLK run is already in progress (pid={pid}, "
                f"command='{held}', since={since}). Wait for it to finish or "
                f"remove {path} if you are sure it is dead.")

    try:
        yield path
    finally:
        # Only remove the lock if it is still ours (defensive against reclaim).
        holder = _read_holder(path)
        if isinstance(holder, dict) and holder.get("pid") == os.getpid():
            try:
                path.unlink()
            except OSError:
                pass
