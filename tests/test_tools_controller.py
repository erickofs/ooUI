"""Tests for ToolsController — discovery and execution."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from gui.controllers.tools_controller import ToolsController
from gui.models.tool_info import ToolInfo


class TestToolDiscovery:
    """Tests for tool discovery from the tools/ directory."""

    def test_discover_emits_tool_list(self, qtbot):
        """TC: discover() emits tools_discovered with ToolInfo list."""
        fake_tools = [
            {"name": "Ollama Chat", "filename": "ollama_chat.py", "path": "/fake/ollama_chat.py"},
            {"name": "Ollama Keys", "filename": "ollama_keys.py", "path": "/fake/ollama_keys.py"},
        ]
        with patch("gui.controllers.tools_controller.get_tool_scripts", return_value=fake_tools):
            ctrl = ToolsController()
            received = []
            ctrl.tools_discovered.connect(received.append)
            ctrl.discover()

            assert len(received) == 1
            tools = received[0]
            assert len(tools) == 2
            assert all(isinstance(t, ToolInfo) for t in tools)

    def test_discover_enriches_known_tools(self, qtbot):
        """Known tools get metadata (description, icon, interactive flag)."""
        fake_tools = [
            {"name": "Ollama Chat", "filename": "ollama_chat.py", "path": "/fake/ollama_chat.py"},
        ]
        with patch("gui.controllers.tools_controller.get_tool_scripts", return_value=fake_tools):
            ctrl = ToolsController()
            ctrl.discover()

            chat_tool = ctrl.tools[0]
            assert chat_tool.interactive is True
            assert chat_tool.icon_char == "💬"
            assert "Chat" in chat_tool.description or "chat" in chat_tool.description.lower()

    def test_discover_empty_directory(self, qtbot):
        """Empty tools/ directory emits empty list."""
        with patch("gui.controllers.tools_controller.get_tool_scripts", return_value=[]):
            ctrl = ToolsController()
            received = []
            ctrl.tools_discovered.connect(received.append)
            ctrl.discover()

            assert received[0] == []


class TestToolExecution:
    """Tests for tool execution via ToolRunner."""

    def test_interactive_tool_opens_external(self, qtbot):
        """TC: Interactive tools call run_external (no inline process)."""
        with patch("gui.controllers.tools_controller.ToolRunner") as MockRunner:
            mock_instance = MockRunner.return_value
            ctrl = ToolsController()

            tool = ToolInfo(
                name="Chat",
                filename="ollama_chat.py",
                path="/fake/chat.py",
                interactive=True,
            )
            ctrl.run_tool(tool)

            MockRunner.run_external.assert_called_once_with("/fake/chat.py", None)
            mock_instance.run_inline.assert_not_called()

    def test_inline_tool_runs_via_runner(self, qtbot):
        """TC-07: Non-interactive tools run inline via QProcess."""
        with patch("gui.controllers.tools_controller.ToolRunner") as MockRunner:
            mock_instance = MockRunner.return_value
            mock_instance.is_running.return_value = False

            ctrl = ToolsController()
            tool = ToolInfo(
                name="List Models",
                filename="ollama_list_models.py",
                path="/fake/list.py",
                interactive=False,
            )
            ctrl.run_tool(tool)

            mock_instance.run_inline.assert_called_once_with("/fake/list.py", None)

    def test_cannot_run_two_inline_tools(self, qtbot):
        """Guard: Running a second inline tool while one is active emits error."""
        with patch("gui.controllers.tools_controller.ToolRunner") as MockRunner:
            mock_instance = MockRunner.return_value
            mock_instance.is_running.return_value = True

            ctrl = ToolsController()
            ctrl._active_runner = mock_instance

            errors = []
            ctrl.tool_error.connect(lambda name, msg: errors.append(msg))

            tool = ToolInfo(name="Keys", filename="keys.py", path="/f", interactive=False)
            ctrl.run_tool(tool)

            assert len(errors) == 1
            assert "já está em execução" in errors[0]

    def test_cancel_tool_kills_process(self, qtbot):
        """Cancel kills the active runner."""
        with patch("gui.controllers.tools_controller.ToolRunner") as MockRunner:
            mock_instance = MockRunner.return_value
            mock_instance.is_running.return_value = True

            ctrl = ToolsController()
            ctrl._active_runner = mock_instance
            ctrl.cancel_tool()

            mock_instance.cancel.assert_called_once()
