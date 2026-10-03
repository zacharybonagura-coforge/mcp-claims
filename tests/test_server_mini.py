"""Unit tests for the mini MCP server wrapper."""

from __future__ import annotations

from unittest.mock import patch

import pytest

import server_mini


def test_server_is_named_equipment_mini() -> None:
    assert server_mini.mcp.name == "equipment-mini"


def test_get_employee_info_delegates() -> None:
    rows = [{"employee_id": "E-1001", "name": "Amina Cole"}]
    with patch("server_mini.retrieve_employee_info", return_value=rows) as fn:
        assert server_mini.get_employee_info("E-1001") == rows
    fn.assert_called_once_with("E-1001")


def test_get_employee_info_propagates_error() -> None:
    with patch(
        "server_mini.retrieve_employee_info", side_effect=ValueError("no row")
    ), pytest.raises(ValueError, match="no row"):
        server_mini.get_employee_info("E-9999")