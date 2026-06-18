"""Thread-aware progress recording for Streamlit pipeline callbacks."""

from __future__ import annotations

from collections.abc import Callable
from threading import Lock, get_ident


class ThreadSafeProgress:
    """Record progress from any thread and render only on the creating thread."""

    def __init__(self, title: str, render_markdown: Callable[[str], None]) -> None:
        self._title = title
        self._render_markdown = render_markdown
        self._ui_thread_id = get_ident()
        self._lock = Lock()
        self._lines: list[str] = []

    def __call__(self, message: str) -> None:
        self.add(message)
        if get_ident() == self._ui_thread_id:
            self.render()

    def add(self, message: str) -> None:
        text = str(message).strip()
        if not text:
            return
        with self._lock:
            self._lines.append(f"- {text}")

    def markdown(self) -> str:
        with self._lock:
            lines = list(self._lines)
        return f"**{self._title}**\n" + "\n".join(lines)

    def render(self) -> None:
        try:
            self._render_markdown(self.markdown())
        except Exception:
            pass
