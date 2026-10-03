"""Unit tests for the interactive equipment CLI."""

from __future__ import annotations

from unittest.mock import patch

import pytest

import cli


def test_ask_returns_stripped_text() -> None:
    with patch("cli.input", return_value="  E-1001  "):
        assert cli._ask("employee_id") == "E-1001"


def test_ask_quit_and_eof_return_none() -> None:
    with patch("cli.input", return_value="QUIT"):
        assert cli._ask("item") is None
    with patch("cli.input", side_effect=EOFError):
        assert cli._ask("reason") is None


def test_read_request_happy_path() -> None:
    with patch("cli._ask", side_effect=["E-1003", "monitor", "need a screen"]):
        assert cli.read_request() == {
            "label": "cli-request",
            "employee_id": "E-1003",
            "item": "monitor",
            "reason": "need a screen",
        }


def test_read_request_rejects_bad_id_then_accepts() -> None:
    with patch("cli._ask", side_effect=["E-12", "E-1001", "laptop", "broken"]):
        req = cli.read_request()
    assert req is not None
    assert req["employee_id"] == "E-1001"


def test_read_request_quit_on_id() -> None:
    with patch("cli._ask", return_value=None):
        assert cli.read_request() is None


def test_read_request_quit_on_empty_then_quit_item() -> None:
    with patch("cli._ask", side_effect=["E-1001", "", None]):
        assert cli.read_request() is None


def test_read_request_quit_on_reason() -> None:
    with patch("cli._ask", side_effect=["E-1001", "laptop", None]):
        assert cli.read_request() is None


def test_print_decision_with_and_without_ticket(
    capsys: pytest.CaptureFixture[str],
) -> None:
    cli.print_decision(
        {"final": "allow", "rationale": "under cap", "flagged": False}
    )
    out = capsys.readouterr().out
    assert "Final Answer: allow" in out
    assert "review_ticket_id" not in out

    cli.print_decision(
        {
            "final": "escalate",
            "rationale": "unknown",
            "flagged": True,
            "review_ticket_id": "REV-0001",
        }
    )
    assert "REV-0001" in capsys.readouterr().out


def test_main_keyboard_interrupt(capsys: pytest.CaptureFixture[str]) -> None:
    with patch("cli.asyncio.run", side_effect=KeyboardInterrupt) as run:
        cli.main()
    if run.call_args:
        run.call_args[0][0].close()
    assert "bye" in capsys.readouterr().out


def test_main_runs_loop() -> None:
    with patch("cli.asyncio.run") as run:
        cli.main()
    run.assert_called_once()
    run.call_args[0][0].close()


def test_read_request_rejects_empty_reason_then_accepts() -> None:
    with patch(
        "cli._ask",
        side_effect=["E-1001", "laptop", "", "keys sticking"],
    ):
        req = cli.read_request()
    assert req is not None
    assert req["reason"] == "keys sticking"