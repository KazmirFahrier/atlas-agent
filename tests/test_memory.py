from orchestrator.memory import MemoryStore, SqliteMemoryStore


def test_assemble_respects_budget_and_pins():
    s = MemoryStore().get("s1")
    s.add("user", "a" * 400)              # ~100 tokens
    s.add("tool", "b" * 4000, pinned=True)  # big but pinned -> always kept
    s.add("user", "c" * 40)
    msgs = s.assemble(token_budget=60)
    contents = "".join(m["content"] for m in msgs)
    assert "b" * 4000 in contents          # pinned survived
    assert msgs[-1]["content"] == "c" * 40  # most-recent kept


def test_tool_role_mapped_to_user():
    s = MemoryStore().get("s2")
    s.add("tool", "result", pinned=True)
    assert s.assemble(1000)[0]["role"] == "user"


def test_sqlite_persists_across_instances(tmp_path):
    db = str(tmp_path / "sessions.db")
    store = SqliteMemoryStore(db)
    sess = store.get("abc")
    sess.add("user", "hello")
    sess.add("assistant", "hi", pinned=True)

    reopened = SqliteMemoryStore(db).get("abc")
    assert [t.content for t in reopened.turns] == ["hello", "hi"]
    assert reopened.turns[1].pinned is True
