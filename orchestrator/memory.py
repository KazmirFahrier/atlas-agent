"""Multi-turn session memory + context assembly.

Keeps a rolling transcript per session and assembles a context window that
stays under a token budget by dropping older, unpinned turns and preserving
high-signal artifacts (tool results, generated file paths).

Two backends:
  * MemoryStore        — in-process dict (fast, ephemeral; used in tests/CI).
  * SqliteMemoryStore  — durable store so multi-turn context survives restarts
                         and horizontal scaling on Cloud Run.

Both satisfy the same interface: `.get(session_id) -> Session`.

Phase-2 done: durable backend below.
Phase-2 TODO (stretch): embedding-based retrieval of the most relevant past
turns instead of pure recency, for very long sessions.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import dataclass, field


def _approx_tokens(text: str) -> int:
    # Cheap heuristic; swap for tiktoken/anthropic tokenizer later.
    return max(1, len(text) // 4)


@dataclass
class Turn:
    role: str  # "user" | "assistant" | "tool"
    content: str
    pinned: bool = False  # pinned turns (e.g. tool artifacts) survive trimming


@dataclass
class Session:
    session_id: str
    turns: list[Turn] = field(default_factory=list)
    _store: "SqliteMemoryStore | None" = None

    def add(self, role: str, content: str, pinned: bool = False) -> None:
        turn = Turn(role, content, pinned)
        self.turns.append(turn)
        if self._store is not None:
            self._store._append(self.session_id, turn)

    def assemble(self, token_budget: int) -> list[dict]:
        """Return messages within budget, keeping pinned + most-recent turns."""
        kept: list[Turn] = []
        used = 0
        for turn in reversed(self.turns):
            cost = _approx_tokens(turn.content)
            if used + cost > token_budget and not turn.pinned:
                continue
            kept.append(turn)
            used += cost
        kept.reverse()
        role_map = {"tool": "user"}  # tool outputs fed back as user context
        return [{"role": role_map.get(t.role, t.role), "content": t.content} for t in kept]


class MemoryStore:
    """Ephemeral in-process store."""

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def get(self, session_id: str) -> Session:
        return self._sessions.setdefault(session_id, Session(session_id))


class SqliteMemoryStore:
    """Durable store; transcript survives process restarts."""

    def __init__(self, path: str = "data/sessions.db") -> None:
        self._path = path
        # check_same_thread=False + a lock: safe under ThreadingHTTPServer.
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.Lock()
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS turns (
                session_id TEXT,
                idx INTEGER,
                role TEXT,
                content TEXT,
                pinned INTEGER,
                PRIMARY KEY (session_id, idx)
            )
            """
        )
        self._conn.commit()

    def _append(self, session_id: str, turn: Turn) -> None:
        with self._lock:
            cur = self._conn.execute(
                "SELECT COALESCE(MAX(idx), -1) + 1 FROM turns WHERE session_id = ?",
                (session_id,),
            )
            idx = cur.fetchone()[0]
            self._conn.execute(
                "INSERT INTO turns VALUES (?, ?, ?, ?, ?)",
                (session_id, idx, turn.role, turn.content, int(turn.pinned)),
            )
            self._conn.commit()

    def get(self, session_id: str) -> Session:
        with self._lock:
            rows = self._conn.execute(
                "SELECT role, content, pinned FROM turns WHERE session_id = ? ORDER BY idx",
                (session_id,),
            ).fetchall()
        turns = [Turn(r[0], r[1], bool(r[2])) for r in rows]
        return Session(session_id, turns=turns, _store=self)

    def export(self, session_id: str) -> str:
        s = self.get(session_id)
        return json.dumps([t.__dict__ for t in s.turns], default=str)
