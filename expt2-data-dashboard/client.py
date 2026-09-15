"""
==============================================================================
Experiment 2: "Data Dashboard" Weather MCP Client (Groq LLM)
==============================================================================
This client connects to the Data Dashboard Weather MCP Server over stdio.
It features a transparent, educational 3-stage visualizer that exposes the full
lifecycle of LLM function calling and MCP tool execution.

Round-Trip Stages Rendered:
  ┌────────────────────────────────────────────────────────┐
  │  Stage 1: 🧠 LLM Decision & Intent (Function + Args)    │
  │  Stage 2: ⚙️  Raw MCP Server Result (Live wttr.in Data)  │
  │  Stage 3: 💬 LLM Final Synthesis (User Answer)         │
  └────────────────────────────────────────────────────────┘

Flow:
  1. Connects to `expt2-data-dashboard/server.py` via `mcp.client.stdio`.
  2. Dynamically pulls tool schema for `get_current_weather`.
  3. Converts MCP JSON Schema into Groq tool definition.
  4. Runs interactive CLI loop prompting for locations / weather inquiries.
==============================================================================
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

# Ensure UTF-8 output on Windows terminals
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Load environment variables from .env file
from dotenv import load_dotenv

# Official MCP Client SDK components
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Official Groq SDK
from groq import Groq

# Optional Rich library for styling (with clean fallback)
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.syntax import Syntax
    console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    console = None


def print_banner():
    """Prints the application banner."""
    title = "🌤️ Experiment 2: Data Dashboard Connector (MCP + Groq + wttr.in)"
    subtitle = "Transparent 3-Stage LLM Round-Trip Visualizer | Protocol: MCP stdio"
    if HAS_RICH:
        console.print(Panel(f"[bold blue]{title}[/bold blue]\n[dim]{subtitle}[/dim]", border_style="blue"))
    else:
        print("\n" + "=" * 75)
        print(title)
        print(subtitle)
        print("=" * 75 + "\n")


def print_stage(number: int, title: str, content: str, color: str = "cyan"):
    """Prints a distinct numbered stage card."""
    header = f"STAGE {number}: {title}"
    if HAS_RICH:
        console.print(Panel(content, title=f"[bold {color}]{header}[/bold {color}]", border_style=color, padding=(1, 2)))
    else:
        print(f"\n[{header}]")
        print(content)
        print("-" * 50)


def convert_mcp_tools_to_groq_format(mcp_tools) -> List[Dict[str, Any]]:
    """
    Transforms MCP tool metadata into the OpenAI/Groq function definition structure.
    """
    groq_tools = []
    for tool in mcp_tools:
        groq_tools.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.inputSchema or {"type": "object", "properties": {}}
            }
        })
    return groq_tools


async def process_weather_query(
    session: ClientSession,
    groq_client: Groq,
    groq_model: str,
    groq_tools: List[Dict[str, Any]],
    user_input: str
) -> None:
    """
    Executes and visibly displays the complete 3-step LLM -> MCP tool round trip.
    """
    # System instruction providing context to the LLM
    messages = [
        {
            "role": "system",
            "content": (
                "You are an AI Weather Data Assistant connected to a live MCP meteorological server. "
                "You have access to the `get_current_weather` tool. When a user asks about weather, temperature, "
                "or atmospheric conditions in any city or location, ALWAYS call `get_current_weather` with the location. "
                "After receiving the tool result, synthesize a helpful, friendly, and structured weather summary for the user."
            )
        },
        {
            "role": "user",
            "content": user_input
        }
    ]

    if HAS_RICH:
        console.print("\n[dim]Sending prompt and MCP tool definitions to Groq LLM...[/dim]")

    # =========================================================================
    # ROUND 1: LLM receives user query + tool schemas
    # =========================================================================
    response = groq_client.chat.completions.create(
        model=groq_model,
        messages=messages,
        tools=groq_tools,
        tool_choice="auto",
        temperature=0.1
    )

    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls

    if not tool_calls:
        # LLM answered directly without calling tool
        print_stage(
            number=1,
            title="Direct LLM Response (No Tool Call Required)",
            content=response_message.content or "(No text)",
            color="green"
        )
        return

    # Iterate through tool calls (standard is single tool call)
    for tool_call in tool_calls:
        tool_name = tool_call.function.name
        raw_args = tool_call.function.arguments

        try:
            parsed_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
        except json.JSONDecodeError:
            parsed_args = {"raw": raw_args}

        # ---------------------------------------------------------------------
        # STAGE 1: Visibly display LLM decision and tool arguments
        # ---------------------------------------------------------------------
        decision_payload = (
            f"⚡ Function Invocation Requested by LLM\n"
            f"• Tool Name : {tool_name}\n"
            f"• Tool Call ID: {tool_call.id}\n"
            f"• Arguments : {json.dumps(parsed_args, indent=2)}"
        )
        print_stage(
            number=1,
            title="🧠 LLM Decision & Intent (Function Call Triggered)",
            content=decision_payload,
            color="yellow"
        )

        # ---------------------------------------------------------------------
        # STAGE 2: Execute tool on MCP Server and show raw response
        # ---------------------------------------------------------------------
        if HAS_RICH:
            console.print(f"[dim]Dispatching JSON-RPC CallToolRequest over stdio to MCP Server...[/dim]")

        try:
            mcp_result = await session.call_tool(tool_name, parsed_args)
            raw_output = ""
            for c in mcp_result.content:
                if hasattr(c, "text"):
                    raw_output += c.text + "\n"
                else:
                    raw_output += str(c) + "\n"
            raw_output = raw_output.strip()
        except Exception as e:
            raw_output = f"MCP Protocol Execution Error: {e}"

        print_stage(
            number=2,
            title="⚙️ Raw MCP Server Tool Execution Result (Live wttr.in Data)",
            content=raw_output,
            color="magenta"
        )

        # Append assistant's call and tool output to conversation messages
        messages.append(response_message)
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "name": tool_name,
            "content": raw_output
        })

    # =========================================================================
    # ROUND 2: LLM receives tool output and synthesizes final response
    # =========================================================================
    if HAS_RICH:
        console.print("[dim]Passing raw server observation back to Groq for final synthesis...[/dim]")

    final_response = groq_client.chat.completions.create(
        model=groq_model,
        messages=messages,
        temperature=0.3
    )

    final_text = final_response.choices[0].message.content or "(Empty response)"

    # ---------------------------------------------------------------------
    # STAGE 3: Final summarized answer from LLM
    # ---------------------------------------------------------------------
    print_stage(
        number=3,
        title="💬 LLM Final Synthesized Response",
        content=final_text,
        color="green"
    )


async def run_client():
    """Main client startup and interactive CLI."""
    # Find .env in project root or current dir
    dotenv_path = Path(__file__).resolve().parent.parent / ".env"
    if dotenv_path.exists():
        load_dotenv(dotenv_path)
    else:
        load_dotenv()

    groq_api_key = os.getenv("GROQ_API_KEY")
    groq_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    print_banner()

    # Check for valid API key
    if not groq_api_key or groq_api_key.strip() == "gsk_your_groq_api_key_here":
        if HAS_RICH:
            console.print("[bold red]⚠️ GROQ_API_KEY not found or using default placeholder![/bold red]")
            console.print("[yellow]Please set your Groq API key in .env or enter it below.[/yellow]\n")
        else:
            print("WARNING: GROQ_API_KEY not configured. Set GROQ_API_KEY in .env or environment.")

        try:
            user_key = input("Enter your Groq API Key (or press Enter to exit): ").strip()
            if not user_key:
                print("Exiting client.")
                return
            groq_api_key = user_key
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            return

    # Initialize Groq Client
    groq_client = Groq(api_key=groq_api_key)

    # Resolve server script path
    server_script = Path(__file__).parent / "server.py"
    if not server_script.exists():
        print(f"Error: server.py not found at {server_script}")
        return

    # Set up Stdio parameters for MCP subprocess
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(server_script)],
        env=dict(os.environ)
    )

    if HAS_RICH:
        console.print(f"[cyan]Connecting to Weather MCP Server: [dim]{server_script.name}[/dim]...[/cyan]")

    # Launch MCP Server as subprocess and establish bidirectional stdio session
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            # Step 1: Initialize MCP Protocol handshake
            await session.initialize()

            # Step 2: Dynamically discover registered tools
            tool_list_response = await session.list_tools()
            mcp_tools = tool_list_response.tools
            groq_tools = convert_mcp_tools_to_groq_format(mcp_tools)

            if HAS_RICH:
                tool_table = Table(title="Discovered Weather MCP Tools", border_style="blue")
                tool_table.add_column("Tool Name", style="bold yellow")
                tool_table.add_column("Description", style="white")
                for t in mcp_tools:
                    tool_table.add_row(t.name, t.description or "")
                console.print(tool_table)
                console.print("\n[bold green]Ready! Type your weather query, or 'exit' / 'quit' to stop.[/bold green]")
                console.print("[dim]Examples:[/dim]")
                console.print("  • [italic]What's the weather in Tokyo right now?[/italic]")
                console.print("  • [italic]Is it raining in Paris today?[/italic]")
                console.print("  • [italic]Give me the current temperature and wind in San Francisco[/italic]\n")
            else:
                print(f"Discovered {len(mcp_tools)} MCP tools: {[t.name for t in mcp_tools]}")
                print("Ready! Type your query, or 'exit' / 'quit' to stop.\n")

            # Interactive loop
            while True:
                try:
                    user_input = input("\nYou > ").strip()
                    if not user_input:
                        continue
                    if user_input.lower() in ("exit", "quit", "q"):
                        print("Goodbye!")
                        break

                    await process_weather_query(
                        session=session,
                        groq_client=groq_client,
                        groq_model=groq_model,
                        groq_tools=groq_tools,
                        user_input=user_input
                    )

                except (KeyboardInterrupt, EOFError):
                    print("\nSession terminated by user. Goodbye!")
                    break
                except Exception as e:
                    if HAS_RICH:
                        console.print(f"[bold red]Error during query execution:[/bold red] {e}")
                    else:
                        print(f"Error: {e}")


def main():
    """Entry point."""
    try:
        asyncio.run(run_client())
    except KeyboardInterrupt:
        print("\nExiting.")


if __name__ == "__main__":
    main()
