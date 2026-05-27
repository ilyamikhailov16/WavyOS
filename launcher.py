#!/usr/bin/env python3
import subprocess
import sys
import time
import signal
import logging
import threading as th
from pathlib import Path

logger = logging.getLogger("launcher")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

ROOT_DIR = Path(__file__).resolve().parent
PYTHON = sys.executable

PROCESSES = [
    ("Core", "core.py", 8.0),
    ("GUI", "gui.py", 1.0),
    ("Tray", "tray.py", 0.5),
]

active_procs = []

def start_process(name: str, script: str, delay: float) -> subprocess.Popen:
    logger.info(f"Starting {name}...")
    proc = subprocess.Popen(
        [PYTHON, str(ROOT_DIR / script)],
        cwd=ROOT_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    time.sleep(delay)
    logger.info(f"{name} started (PID {proc.pid})")
    return proc

def forward_logs(proc: subprocess.Popen, prefix: str):
    for line in proc.stdout:
        if line.strip():
            logger.info(f"[{prefix}] {line.strip()}")

def cleanup_all():
    logger.info("Terminating all processes...")
    for name, proc in reversed(active_procs):
        if proc.poll() is None:
            proc.terminate()
    for name, proc in active_procs:
        try: proc.wait(timeout=3)
        except: proc.kill()

def main():
    logger.info("=== UniversalApp Launcher ===")
    try:
        for name, script, delay in PROCESSES:
            proc = start_process(name, script, delay)
            th.Thread(target=forward_logs, args=(proc, name), daemon=True).start()
            active_procs.append((name, proc))

        logger.info("All processes started. Monitoring...")
        while True:
            for name, proc in active_procs:
                if proc.poll() is not None:
                    logger.error(f"{name} exited unexpectedly (code {proc.returncode})")
                    cleanup_all()
                    return 1
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Launcher: Shutting down...")
        cleanup_all()
        return 0
    except Exception as e:
        logger.error(f"Launcher error: {e}", exc_info=True)
        cleanup_all()
        return 1

if __name__ == "__main__":
    sys.exit(main())