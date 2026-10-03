"""Unit tests for the full equipment MCP server wrappers."""

from __future__ import annotations

from unittest.mock import patch

import pytest

import server


def test_server_is_named_equipment() -> None:
    assert server.mcp.name == "equipment"


def test_get_employee_info_delegates() -> None:
    rows = [{"employee_id": "E-1", "name": "Ada"}]
    with patch("server.retrieve_employee_info", return_value=rows) as fn:
        assert server.get_employee_info("E-1") == rows
    fn.assert_called_once_with("E-1")


def test_get_employee_info_propagates_error() -> None:
    with (
        patch("server.retrieve_employee_info", side_effect=ValueError("missing")),
        pytest.raises(ValueError, match="missing"),
    ):
        server.get_employee_info("E-9999")


def test_get_policy_limits_delegates() -> None:
    payload = {"role": "employee", "limits": []}
    with patch("server.retrieve_policy_limits", return_value=payload) as fn:
        assert server.get_policy_limits("employee") == payload
    fn.assert_called_once_with("employee")


def test_get_policy_limits_propagates_error() -> None:
    with (
        patch("server.retrieve_policy_limits", side_effect=RuntimeError("bad role")),
        pytest.raises(RuntimeError, match="bad role"),
    ):
        server.get_policy_limits("contractor")


def test_check_request_eligibility_delegates() -> None:
    payload = {"eligible": True}
    with patch("server.run_eligibility_check", return_value=payload) as fn:
        assert server.check_request_eligibility("E-1", "laptop") == payload
    fn.assert_called_once_with("E-1", "laptop")


def test_check_request_eligibility_propagates_error() -> None:
    with (
        patch("server.run_eligibility_check", side_effect=ValueError("parse")),
        pytest.raises(ValueError, match="parse"),
    ):
        server.check_request_eligibility("E-1", "")


def test_flag_for_human_review_delegates() -> None:
    payload = {"review_ticket_id": "REV-0001"}
    with patch("server.record_human_review", return_value=payload) as fn:
        assert server.flag_for_human_review("E-1", "laptop", "unknown id") == payload
    fn.assert_called_once_with("E-1", "laptop", "unknown id")


def test_flag_for_human_review_propagates_error() -> None:
    with (
        patch("server.record_human_review", side_effect=OSError("disk")),
        pytest.raises(OSError, match="disk"),
    ):
        server.flag_for_human_review("E-1", "laptop", "unknown id")
