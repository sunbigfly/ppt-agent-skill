#!/usr/bin/env python3
"""Persist subagent command output to a local runtime log."""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import TextIO


def _timestamp() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _open_log(path: Path) -> TextIO:
    path.parent.mkdir(parents=True, exist_ok=True)
    return path.open("a", encoding="utf-8")


def _write_header(handle: TextIO, *, kind: str, label: str, cwd: Path, cmd: list[str] | None = None) -> None:
    handle.write(f"=== {kind} { _timestamp() } ===\n")
    handle.write(f"label: {label}\n")
    handle.write(f"cwd: {cwd}\n")
    if cmd is not None:
        handle.write(f"cmd: {shlex.join(cmd)}\n")
    handle.flush()


def _tee_stream(
    stream: TextIO | None,
    sink: TextIO,
    capture: list[str],
    writer: TextIO,
    lock: threading.Lock,
    section: str,
) -> None:
    if stream is None:
        return
    wrote_section = False
    for chunk in stream:
        capture.append(chunk)
        writer.write(chunk)
        writer.flush()
        with lock:
            if not wrote_section:
                sink.write(f"{section}:\n")
                wrote_section = True
            sink.write(chunk)
            sink.flush()
    if not wrote_section:
        with lock:
            sink.write(f"{section}:\n")
            sink.flush()


def run_command(args: argparse.Namespace) -> int:
    if not args.command:
        print("ERROR: missing command after --", file=sys.stderr)
        return 2

    log_path = Path(args.log)
    cwd = Path(args.cwd).resolve() if args.cwd else Path.cwd()

    with _open_log(log_path) as handle:
        _write_header(handle, kind="RUN", label=args.label, cwd=cwd, cmd=args.command)

        proc = subprocess.Popen(
            args.command,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        stdout_chunks: list[str] = []
        stderr_chunks: list[str] = []
        lock = threading.Lock()

        stdout_thread = threading.Thread(
            target=_tee_stream,
            args=(proc.stdout, handle, stdout_chunks, sys.stdout, lock, "stdout"),
            daemon=True,
        )
        stderr_thread = threading.Thread(
            target=_tee_stream,
            args=(proc.stderr, handle, stderr_chunks, sys.stderr, lock, "\nstderr"),
            daemon=True,
        )
        stdout_thread.start()
        stderr_thread.start()
        stdout_thread.join()
        stderr_thread.join()

        exit_code = proc.wait()
        handle.write("\n")
        handle.write(f"exit_code: {exit_code}\n")
        handle.write(f"finished_at: {_timestamp()}\n")
        handle.write("=== END ===\n\n")
        handle.flush()

    return exit_code


def write_note(args: argparse.Namespace) -> int:
    log_path = Path(args.log)
    cwd = Path.cwd()
    with _open_log(log_path) as handle:
        _write_header(handle, kind="NOTE", label=args.label, cwd=cwd)
        handle.write(f"message: {args.message}\n")
        handle.write("=== END ===\n\n")
        handle.flush()

    print(f"[subagent-log] {args.label}: {args.message}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Persist subagent notes and command output to a log file")
    subparsers = parser.add_subparsers(dest="command_name")

    run_parser = subparsers.add_parser("run", help="Run a command and tee stdout/stderr into a log file")
    run_parser.add_argument("--log", required=True, help="Target log file path")
    run_parser.add_argument("--label", required=True, help="Short label for this command")
    run_parser.add_argument("--cwd", help="Optional working directory for the wrapped command")
    run_parser.add_argument("command", nargs=argparse.REMAINDER, help="Wrapped command, passed after --")

    note_parser = subparsers.add_parser("note", help="Append a note to a log file")
    note_parser.add_argument("--log", required=True, help="Target log file path")
    note_parser.add_argument("--label", required=True, help="Short label for the note")
    note_parser.add_argument("--message", required=True, help="Note content")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command_name == "run":
        if args.command and args.command[0] == "--":
            args.command = args.command[1:]
        return run_command(args)

    if args.command_name == "note":
        return write_note(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
