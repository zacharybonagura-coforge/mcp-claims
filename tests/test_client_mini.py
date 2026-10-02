"""Unit tests for the mini MCP client."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import client_mini


def _session(names: list[str], result: SimpleNamespace) -> AsyncMock:
    session = AsyncMock()
    session.initialize = AsyncMock()
    session.list_tools = AsyncMock(
        return_value=SimpleNamespace(
            tools=[SimpleNamespace(name=name) for name in names]
        )
    )
    session.call_tool = AsyncMock(return_value=result)
    return session


def _run_main(session: AsyncMock) -> None:
    stdio_cm = AsyncMock()
    stdio_cm.__aenter__.return_value = (MagicMock(), MagicMock())
    stdio_cm.__aexit__.return_value = False
    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = False
    with (
        patch("client_mini.stdio_client", return_value=stdio_cm),
        patch("client_mini.ClientSession", return_value=session_cm) as ctor,
        patch("client_mini.StdioServerParameters") as params,
    ):
        asyncio.run(client_mini.main())
    params.assert_called_once_with(
        command=str(client_mini.PYTHON),
        args=["src/server_mini.py"],
        cwd=str(client_mini.ROOT),
        env={"PYTHONPATH": str(client_mini.ROOT / "src")},
    )
    ctor.assert_called_once()


def test_main_lists_tool_and_prints_employee() -> None:
    payload = {"employee_id": "E-1001", "name": "Amina Cole"}
    session = _session(
        ["get_employee_info"],
        SimpleNamespace(is_error=False, structured_content=payload, content=None),
    )

    _run_main(session)

    session.call_tool.assert_awaited_once_with(
        "get_employee_info", {"employee_id": "E-1001"}
    )


def test_main_exits_on_tool_error() -> None:
    session = _session(
        ["get_employee_info"],
        SimpleNamespace(is_error=True, structured_content=None, content="nope"),
    )

    with pytest.raises(SystemExit, match="tool error: nope"):
        _run_main(session)


def test_main_fails_when_tool_list_wrong() -> None:
    session = _session(
        ["get_employee_info", "get_policy_limits"],
        SimpleNamespace(is_error=False, structured_content={}, content=None),
    )

    with pytest.raises(AssertionError):
        _run_main(session)
    session.call_tool.assert_not_awaited()