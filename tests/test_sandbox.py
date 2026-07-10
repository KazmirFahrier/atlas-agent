from mcp_servers.py_sandbox.sandbox import run_python


def test_basic_stdout():
    r = run_python("print(2 + 2)")
    assert r.ok and r.output.strip() == "4"


def test_runaway_loop_is_stopped():
    # Stopped by either the CPU rlimit (SIGXCPU) or the wall-clock timeout.
    r = run_python("while True:\n    pass")
    assert not r.ok
    assert "limit" in r.output.lower() or "timed out" in r.output.lower()


def test_error_is_reported():
    r = run_python("raise ValueError('nope')")
    assert not r.ok and "ERROR" in r.output


def test_computation_over_fetched_data():
    # The real use case: rank rows the SQL tool already returned.
    code = (
        "rows=[('A',0.8),('B',3.1),('C',0.5)]\n"
        "worst=sorted(rows,key=lambda r:r[1])[:2]\n"
        "print([r[0] for r in worst])"
    )
    r = run_python(code)
    assert r.ok and "['C', 'A']" in r.output
