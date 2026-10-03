"""Unit tests for the full equipment MCP client."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import client


def test_server_params_points_at_full_server() -> None:
    params = client.server_params()

    assert params.command == str(client.PYTHON)
    assert params.args == ["src/server.py"]
    assert params.cwd == str(client.ROOT)
    assert params.env == {"PYTHONPATH": str(client.ROOT / "src")}


def test_call_tool_returns_structured_content() -> None:
    session = AsyncMock()
    session.call_tool.return_value = SimpleNamespace(
        is_error=False,
        structured_content={"employee_id": "E-1001"},
        content=None,
    )

    payload = asyncio.run(
        client.call_tool(session, "get_employee_info", {"employee_id": "E-1001"})
    )

    session.call_tool.assert_awaited_once_with(
        "get_employee_info", {"employee_id": "E-1001"}
    )
    assert payload == {"employee_id": "E-1001"}


def test_call_tool_exits_on_error() -> None:
    session = AsyncMock()
    session.call_tool.return_value = SimpleNamespace(
        is_error=True,
        structured_content=None,
        content="boom",
    )

    with pytest.raises(SystemExit, match=r"tool error \(get_employee_info\): boom"):
        asyncio.run(client.call_tool(session, "get_employee_info", {}))


def _session(names: list[str]) -> AsyncMock:
    session = AsyncMock()
    session.initialize = AsyncMock()
    session.list_tools = AsyncMock(
        return_value=SimpleNamespace(
            tools=[SimpleNamespace(name=name) for name in names]
        )
    )
    return session


def _run_main(session: AsyncMock) -> None:
    stdio_cm = AsyncMock()
    stdio_cm.__aenter__.return_value = (MagicMock(), MagicMock())
    stdio_cm.__aexit__.return_value = False
    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = False
    with (
        patch("client.stdio_client", return_value=stdio_cm),
        patch("client.ClientSession", return_value=session_cm),
    ):
        asyncio.run(client.main())


def test_main_lists_expected_tools() -> None:
    session = _session(
        [
            "get_employee_info",
            "get_policy_limits",
            "check_request_eligibility",
            "flag_for_human_review",
        ]
    )
    _run_main(session)
    session.initialize.assert_awaited_once()
    session.list_tools.assert_awaited_once()


def test_main_fails_when_tool_names_differ() -> None:
    session = _session(["get_employee_info"])

    with pytest.raises(AssertionError):
        _run_main(session)