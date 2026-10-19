"""Bounded worker pool: system operations never run on the GUI thread."""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal


def command(args: list[str], timeout: int = 20, input_text: str | None = None) -> str:
    if not args or not shutil.which(args[0]):
        raise RuntimeError(f"Benötigtes Programm fehlt: {args[0] if args else '?'}")
    result = subprocess.run(
        args,
        input=input_text,
        capture_output=True,
        text=True,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode:
        # Do not include arguments: they can include identifying connection data.
        detail = (result.stderr or result.stdout).strip()[-1500:]
        raise RuntimeError(f"{args[0]}: {detail or 'Vorgang fehlgeschlagen'}")
    return result.stdout.strip()


class WorkerSignals(QObject):
    result = Signal(str, object)
    failed = Signal(str, str)


class Worker(QRunnable):
    def __init__(self, name: str, task: Callable[[], Any], signals: WorkerSignals):
        super().__init__()
        self.name, self.task, self.signals = name, task, signals

    def run(self) -> None:
        try:
            self.signals.result.emit(self.name, self.task())
        except Exception as exc:
            self.signals.failed.emit(self.name, str(exc))


class Jobs(QObject):
    result = Signal(str, object)
    failed = Signal(str, str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(3)
        self.signals = WorkerSignals(self)
        self.signals.result.connect(self.result)
        self.signals.failed.connect(self.failed)
        self.pending: set[str] = set()
        self.result.connect(self._finished)
        self.failed.connect(self._finished)

    def _finished(self, name: str, _value: Any) -> None:
        self.pending.discard(name)

    def submit(self, name: str, task: Callable[[], Any]) -> None:
        if name not in self.pending:
            self.pending.add(name)
            self.pool.start(Worker(name, task, self.signals))
