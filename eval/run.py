"""Run the Atlas eval suite.

    python -m eval.run            # uses LLM if a key is set, else offline
    python -m eval.run --offline  # force offline (CI mode, no network)

Exit code is non-zero if any case fails, so CI blocks regressions.
"""
from __future__ import annotations

import sys
import uuid

from orchestrator.agent import answer_traced
from orchestrator.config import CONFIG
from orchestrator.guardrails import GuardrailError, assert_read_only_sql

from .cases import CASES


def _run_case(case: dict, offline: bool) -> tuple[bool, str]:
    # Guardrail-only cases don't need the agent.
    if case.get("guardrail_should_block"):
        try:
            assert_read_only_sql(case["turns"][0])
            return False, "expected guardrail to block, but it passed"
        except GuardrailError:
            return True, "guardrail correctly blocked write"

    session_id = str(uuid.uuid4())
    last, tools = "", []
    for turn in case["turns"]:
        last, tools = answer_traced(turn, session_id)

    if offline or not CONFIG.has_llm:
        missing = [s for s in case.get("offline_contains", []) if s not in last]
        if missing:
            return False, f"offline output missing: {missing}"
        return True, "offline assertions passed"

    # Online: assert the expected tool was ACTUALLY invoked (from the trace),
    # not merely mentioned in the answer text.
    tool = case.get("expects_tool")
    if tool and tool not in tools:
        return False, f"expected tool '{tool}' not invoked; trace={tools}"
    return True, f"online assertions passed (tools={tools})"


def main() -> None:
    offline = "--offline" in sys.argv
    passed = 0
    print(f"Running {len(CASES)} eval cases (offline={offline or not CONFIG.has_llm})\n")
    for case in CASES:
        ok, msg = _run_case(case, offline)
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {case['id']}: {msg}")
        passed += ok
    total = len(CASES)
    print(f"\n{passed}/{total} passed  (pass rate {passed / total:.0%})")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
