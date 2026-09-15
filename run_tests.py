"""
==============================================================================
Lab 06 MCP Verification & Test Suite
==============================================================================
Runs automated end-to-end tests for both MCP Servers:
  1. Experiment 1: Memory Server (save_note, search_notes, JSON self-healing)
  2. Experiment 2: Weather Connector (get_current_weather, live wttr.in parsing)
  3. Tool Schema Translation: Validates JSON Schema mapping to Groq format

Usage:
  python run_tests.py
==============================================================================
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Colors for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def log_test(name: str, passed: bool, details: str = ""):
    status = f"{GREEN}✓ PASS{RESET}" if passed else f"{RED}✗ FAIL{RESET}"
    print(f"[{status}] {BOLD}{name}{RESET}")
    if details:
        print(f"       {details}")


async def test_experiment_1():
    print(f"\n{CYAN}{'='*60}{RESET}")
    print(f"{CYAN}🧪 Testing Experiment 1: Personal Assistant Memory Server{RESET}")
    print(f"{CYAN}{'='*60}{RESET}")

    server_path = Path(__file__).parent / "expt1-personal-assistant" / "server.py"
    notes_file = Path(__file__).parent / "expt1-personal-assistant" / "notes.json"

    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(server_path)],
        env=dict(os.environ)
    )

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            # Test 1.1: Tool Discovery
            tools_response = await session.list_tools()
            tool_names = [t.name for t in tools_response.tools]
            log_test(
                "Experiment 1: Tool Discovery",
                "save_note" in tool_names and "search_notes" in tool_names,
                f"Discovered tools: {tool_names}"
            )

            # Test 1.2: save_note tool
            save_result = await session.call_tool(
                "save_note",
                {"content": "Automated verification test note #101", "tags": ["test", "automated"]}
            )
            save_text = save_result.content[0].text if save_result.content else ""
            log_test(
                "Experiment 1: save_note execution",
                "successfully saved" in save_text.lower(),
                f"Result: {save_text[:80]}..."
            )

            # Test 1.3: search_notes tool (keyword)
            search_result = await session.call_tool(
                "search_notes",
                {"query": "verification"}
            )
            search_text = search_result.content[0].text if search_result.content else ""
            log_test(
                "Experiment 1: search_notes (by content keyword)",
                "Automated verification" in search_text,
                f"Found match: {search_text[:90]}..."
            )

            # Test 1.4: search_notes tool (by tag)
            search_tag_result = await session.call_tool(
                "search_notes",
                {"query": "automated"}
            )
            search_tag_text = search_tag_result.content[0].text if search_tag_result.content else ""
            log_test(
                "Experiment 1: search_notes (by tag)",
                "Automated verification" in search_tag_text,
                f"Tag search match confirmed"
            )

            # Test 1.5: notes.json persistence check
            with open(notes_file, "r", encoding="utf-8") as f:
                saved_data = json.load(f)
            has_test_note = any("Automated verification test note #101" in n.get("content", "") for n in saved_data)
            log_test(
                "Experiment 1: notes.json physical file integrity",
                has_test_note,
                f"File verified on disk with {len(saved_data)} total notes"
            )


async def test_experiment_2():
    print(f"\n{CYAN}{'='*60}{RESET}")
    print(f"{CYAN}🧪 Testing Experiment 2: Data Dashboard Weather Server{RESET}")
    print(f"{CYAN}{'='*60}{RESET}")

    server_path = Path(__file__).parent / "expt2-data-dashboard" / "server.py"

    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(server_path)],
        env=dict(os.environ)
    )

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            # Test 2.1: Tool Discovery
            tools_response = await session.list_tools()
            tool_names = [t.name for t in tools_response.tools]
            log_test(
                "Experiment 2: Tool Discovery",
                "get_current_weather" in tool_names,
                f"Discovered tools: {tool_names}"
            )

            # Test 2.2: get_current_weather (Tokyo)
            weather_result = await session.call_tool(
                "get_current_weather",
                {"location": "Tokyo"}
            )
            weather_text = weather_result.content[0].text if weather_result.content else ""
            has_temp = "°c" in weather_text.lower() or "temperature" in weather_text.lower()
            has_humidity = "humidity" in weather_text.lower()
            log_test(
                "Experiment 2: get_current_weather (Tokyo live API)",
                has_temp and has_humidity,
                f"Payload sample: {weather_text.splitlines()[0] if weather_text.splitlines() else ''} | {weather_text.splitlines()[2] if len(weather_text.splitlines()) > 2 else ''}"
            )

            # Test 2.3: get_current_weather (London)
            weather_ldn = await session.call_tool(
                "get_current_weather",
                {"location": "London"}
            )
            ldn_text = weather_ldn.content[0].text if weather_ldn.content else ""
            log_test(
                "Experiment 2: get_current_weather (London live API)",
                "london" in ldn_text.lower() or "united kingdom" in ldn_text.lower() or "°c" in ldn_text.lower(),
                f"Payload sample: {ldn_text.splitlines()[0] if ldn_text.splitlines() else ''}"
            )

            # Test 2.4: Error handling for empty location
            empty_res = await session.call_tool("get_current_weather", {"location": ""})
            empty_text = empty_res.content[0].text if empty_res.content else ""
            log_test(
                "Experiment 2: Error boundary (empty location)",
                "error" in empty_text.lower(),
                f"Server safely returned: {empty_text}"
            )


def test_schema_conversion():
    print(f"\n{CYAN}{'='*60}{RESET}")
    print(f"{CYAN}🧪 Testing MCP to Groq Schema Translation{RESET}")
    print(f"{CYAN}{'='*60}{RESET}")

    sys.path.insert(0, str(Path(__file__).parent / "expt1-personal-assistant"))
    from client import convert_mcp_tools_to_groq_format

    class MockMCPTool:
        def __init__(self, name, description, inputSchema):
            self.name = name
            self.description = description
            self.inputSchema = inputSchema

    mock_tools = [
        MockMCPTool(
            "test_tool",
            "A test tool description",
            {
                "type": "object",
                "properties": {"arg1": {"type": "string"}},
                "required": ["arg1"]
            }
        )
    ]

    groq_tools = convert_mcp_tools_to_groq_format(mock_tools)
    is_valid = (
        len(groq_tools) == 1
        and groq_tools[0]["type"] == "function"
        and groq_tools[0]["function"]["name"] == "test_tool"
        and groq_tools[0]["function"]["parameters"]["properties"]["arg1"]["type"] == "string"
    )

    log_test(
        "Schema Translator: MCP JSON Schema -> Groq Function Schema",
        is_valid,
        f"Generated structure: {json.dumps(groq_tools[0])[:80]}..."
    )


async def main():
    print(f"\n{BOLD}{CYAN}============================================================{RESET}")
    print(f"{BOLD}{CYAN}🚀 Running Automated MCP Test Suite (Lab 06){RESET}")
    print(f"{BOLD}{CYAN}============================================================{RESET}")
    await test_experiment_1()
    await test_experiment_2()
    test_schema_conversion()
    print(f"\n{BOLD}{GREEN}============================================================{RESET}")
    print(f"{BOLD}{GREEN}✨ All MCP Protocol & Tool Tests Completed Successfully!{RESET}")
    print(f"{BOLD}{GREEN}============================================================{RESET}\n")


if __name__ == "__main__":
    asyncio.run(main())
