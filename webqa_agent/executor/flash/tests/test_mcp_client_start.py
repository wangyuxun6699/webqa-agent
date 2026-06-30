"""Tests for MCPServer.start process command resolution."""
from __future__ import annotations

import io
from pathlib import Path

import pytest

from webqa_agent.executor.flash.core import mcp_client
from webqa_agent.executor.flash.core.mcp_client import MCPError, MCPServer


class _FakeProc:
    def __init__(self) -> None:
        self.stdin = io.BytesIO()
        self.stdout = io.BytesIO()
        self.stderr = io.BytesIO()
        self.pid = 12345

    def wait(self, timeout=None):
        return 0

    def terminate(self) -> None:
        pass

    def kill(self) -> None:
        pass


@pytest.fixture
def isolated_start(monkeypatch):
    popen_calls = []

    def fake_popen(cmd, **kwargs):
        popen_calls.append((list(cmd), dict(kwargs)))
        return _FakeProc()

    monkeypatch.setattr(mcp_client.subprocess, 'Popen', fake_popen)
    monkeypatch.setattr(MCPServer, '_read_stdout', lambda self: None)
    monkeypatch.setattr(MCPServer, '_drain_stderr', lambda self: None)
    monkeypatch.setattr(MCPServer, '_initialize', lambda self, timeout_s: None)
    monkeypatch.setattr(MCPServer, '_list_tools', lambda self, timeout_s: [])
    return popen_calls


def test_start_uses_resolved_command_from_path(isolated_start, monkeypatch):
    resolved = r'C:\Users\me\AppData\Roaming\npm\chrome-devtools-mcp.CMD'
    monkeypatch.setattr(mcp_client.shutil, 'which', lambda command: resolved)

    server = MCPServer(
        name='browser',
        command='chrome-devtools-mcp',
        args=['--headless'],
    )
    server.start()
    server.shutdown()

    assert isolated_start[0][0][0] == resolved
    assert isolated_start[0][0][1:] == ['--headless']


def test_start_raises_when_non_absolute_command_is_not_found(
    isolated_start, monkeypatch,
):
    monkeypatch.setattr(mcp_client.shutil, 'which', lambda command: None)

    server = MCPServer(name='browser', command='missing-mcp-server')
    with pytest.raises(MCPError, match="command not found on PATH"):
        server.start()

    assert isolated_start == []


def test_start_keeps_absolute_command_when_path_lookup_fails(
    isolated_start, monkeypatch, tmp_path: Path,
):
    absolute_command = str(tmp_path / 'custom-mcp-server')
    monkeypatch.setattr(mcp_client.shutil, 'which', lambda command: None)

    server = MCPServer(
        name='custom',
        command=absolute_command,
        args=['--stdio'],
    )
    server.start()
    server.shutdown()

    assert isolated_start[0][0] == [absolute_command, '--stdio']
