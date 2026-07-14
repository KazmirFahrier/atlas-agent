"""Reusable sandboxed Python executor (importable + unit-testable).

Isolation applied on POSIX via `resource` rlimits in a preexec hook:
  * RLIMIT_CPU  — CPU-seconds ceiling (hard stop on busy loops)
  * RLIMIT_AS   — address-space (memory) ceiling on Linux
  * RLIMIT_FSIZE— max bytes the child may write (0 = no file writes)
Plus: runs in a throwaway temp cwd, wall-clock timeout, and stdout cap.

This is a pragmatic single-host boundary. For untrusted multi-tenant use,
wrap the child in gVisor / a microVM / Docker with `--network none`; the
`preexec` limits still apply inside those and compose cleanly.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass

CPU_SECONDS = 4
MEM_BYTES = 256 * 1024 * 1024  # 256 MB
FSIZE_BYTES = 0  # no file writes
WALL_TIMEOUT_S = 8
OUTPUT_CAP = 20_000


def _limits() -> None:  # pragma: no cover - runs only in the child process
    import resource

    resource.setrlimit(resource.RLIMIT_CPU, (CPU_SECONDS, CPU_SECONDS))
    # RLIMIT_AS is reliable on Linux, but setting it below the parent process's
    # existing virtual-memory footprint can make macOS fail in preexec_fn.
    if sys.platform.startswith("linux"):
        resource.setrlimit(resource.RLIMIT_AS, (MEM_BYTES, MEM_BYTES))
    resource.setrlimit(resource.RLIMIT_FSIZE, (FSIZE_BYTES, FSIZE_BYTES))


@dataclass
class SandboxResult:
    ok: bool
    output: str


def run_python(code: str) -> SandboxResult:
    """Execute a snippet under resource limits; return captured stdout."""
    preexec = _limits if os.name == "posix" else None
    with tempfile.TemporaryDirectory() as workdir:
        script = os.path.join(workdir, "snippet.py")
        with open(script, "w") as fh:
            fh.write(code)
        try:
            proc = subprocess.run(
                [sys.executable, "-I", script],  # -I: isolated, ignore env/user site
                capture_output=True,
                text=True,
                timeout=WALL_TIMEOUT_S,
                cwd=workdir,
                preexec_fn=preexec,
            )
        except subprocess.TimeoutExpired:
            return SandboxResult(False, "ERROR: execution timed out (wall-clock limit)")
    if proc.returncode < 0:  # killed by a signal (e.g. SIGXCPU / SIGXFSZ resource limit)
        return SandboxResult(False, f"ERROR: terminated by resource limit (signal {-proc.returncode})")
    if proc.returncode != 0:
        return SandboxResult(False, f"ERROR: {proc.stderr[:2000] or 'non-zero exit'}")
    return SandboxResult(True, (proc.stdout or "(no stdout)")[:OUTPUT_CAP])
