from orchestrator.guardrails import (
    GuardrailError,
    assert_read_only_sql,
    call_with_retry,
    validate_json,
    verify_tool_result,
)

import pytest

SCHEMA = {"type": "object", "required": ["campaign"], "properties": {"campaign": {"type": "string"}}}


def test_valid_json_passes():
    assert validate_json({"campaign": "x"}, SCHEMA)["campaign"] == "x"


def test_invalid_json_raises():
    with pytest.raises(GuardrailError):
        validate_json({"campaign": 1}, SCHEMA)


def test_read_only_sql_allows_select():
    assert_read_only_sql("SELECT * FROM campaign_daily")
    assert_read_only_sql("WITH t AS (SELECT 1) SELECT * FROM t")


@pytest.mark.parametrize("bad", ["DROP TABLE campaign_daily", "delete from campaign_daily", "UPDATE x SET y=1"])
def test_read_only_sql_blocks_writes(bad):
    with pytest.raises(GuardrailError):
        assert_read_only_sql(bad)


def test_verify_rejects_empty_and_errors():
    with pytest.raises(GuardrailError):
        verify_tool_result(None)
    with pytest.raises(GuardrailError):
        verify_tool_result("ERROR: boom")
    assert verify_tool_result("ok") == "ok"


def test_retry_eventually_succeeds():
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 2:
            raise RuntimeError("transient")
        return "done"

    assert call_with_retry(flaky) == "done"
    assert calls["n"] == 2
