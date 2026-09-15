"""
==============================================================================
Experiment 1: "Personal Assistant" Memory MCP Client (Groq LLM)
==============================================================================
This client connects to the Personal Assistant Memory MCP Server over standard
I/O (stdio). It dynamically retrieves the server's available tools, maps them
to Groq's tool-calling API, and enables an interactive conversation where the
LLM intelligently chooses between saving notes, searching notes, or answering directly.

Flow:
  1. Spawns `server.py` as a subprocess via MCP `stdio_client`.
  2. Initializes MCP session and fetches tool definitions (`session.list_tools()`).
  3. Converts MCP tool schemas to OpenAI/Groq compatible function-calling format.
  4. In an interactive loop:
     a. Accepts user prompt (e.g., "Remember that dentist appointment is on Monday").
     b. Sends user prompt + tool schemas to Groq (`llama-3.3-70b-versatile`).
     c. If LLM decides to call a tool:
        - Displays LLM tool choice and arguments.
        - Calls the tool on the MCP server via `session.call_tool(...)`.
        - Displays raw tool execution result.
        - Feeds tool result back to Groq for the final synthesized answer.
     d. Displays the final natural-language answer.
==============================================================================
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

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

# Optional Rich library for clean terminal UI (falls back to standard print)
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    console = None


def print_banner():
    """Prints the application banner."""
    title = "🧠 Experiment 1: Personal Assistant Memory (MCP + Groq)"
    subtitle = "Connected to MCP Server via stdio | Model: Groq Llama-3"
    if HAS_RICH:
        console.print(Panel(f"[bold cyan]{title}[/bold cyan]\n[dim]{subtitle}[/dim]", border_style="cyan"))
    else:
        print("\n" + "=" * 70)
        print(title)
        print(subtitle)
        print("=" * 70 + "\n")


def print_step(title: str, content: str, style: str = "cyan"):
    """Prints a styled step for visibility."""
    if HAS_RICH:
        console.print(Panel(content, title=f"[bold {style}]{title}[/bold {style}]", border_style=style))
    else:
        print(f"\n--- {title} ---")
        print(content)
        print("-" * (len(title) + 8))


def convert_mcp_tools_to_groq_format(mcp_tools) -> List[Dict[str, Any]]:
    """
    ============================================================================
    MCP Tool Schema -> Groq Function Schema Converter
    ============================================================================
    MCP tools provide standard JSON Schema definitions in `tool.inputSchema`.
    Groq (and OpenAI) expects tools in the format:
    {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.inputSchema
        }
    }
    ============================================================================
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


async def process_user_query(
    session: ClientSession,
    groq_client: Groq,
    groq_model: str,
    groq_tools: List[Dict[str, Any]],
    user_input: str,
    conversation_history: List[Dict[str, Any]]
) -> None:
    """
    Executes the full LLM function calling loop:
    1. Sends query to Groq with tool definitions.
    2. Inspects model response for tool_calls.
    3. If tool called: executes on MCP server and returns output to model.
    4. Prints final synthesized answer.
    """
    # Append user message to history
    messages = conversation_history.copy()
    messages.append({"role": "user", "content": user_input})

    # System instruction guiding the LLM on tool usage
    system_message = {
        "role": "system",
        "content": (
            "You are an intelligent personal memory assistant connected to a persistent MCP note store. "
            "You have access to two tools: `save_note` and `search_notes`.\n"
            "- If the user asks to save, store, remember, or add information, call `save_note`.\n"
            "- If the user asks a question, requests recall, or searches for past notes, call `search_notes`.\n"
            "- If the user provides a conversational greeting or query unrelated to notes, answer directly.\n"
            "- After receiving tool results, provide a clear, concise, and helpful natural-language response."
        )
    }

    full_payload = [system_message] + messages

    if HAS_RICH:
        console.print("[dim]Thinking and selecting appropriate tool...[/dim]")

    # Step 1: Call Groq LLM with available tools
    response = groq_client.chat.completions.create(
        model=groq_model,
        messages=full_payload,
        tools=groq_tools if groq_tools else None,
        tool_choice="auto" if groq_tools else None,
        temperature=0.2
    )

    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls

    # Case A: LLM decided to call one or more tools
    if tool_calls:
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            raw_arguments = tool_call.function.arguments
            
            try:
                tool_args = json.loads(raw_arguments) if isinstance(raw_arguments, str) else raw_arguments
            except json.JSONDecodeError:
                tool_args = {}

            # Print LLM Decision visibly
            decision_text = f"Selected Tool : {tool_name}\nArguments     : {json.dumps(tool_args, indent=2)}"
            print_step("🤖 LLM Tool Selection Decision", decision_text, style="yellow")

            # Step 2: Execute tool on MCP Server via stdio session
            try:
                mcp_result = await session.call_tool(tool_name, tool_args)
                
                # Extract text content from MCP CallToolResult
                result_text = ""
                for content in mcp_result.content:
                    if hasattr(content, "text"):
                        result_text += content.text + "\n"
                    else:
                        result_text += str(content) + "\n"
                result_text = result_text.strip()
            except Exception as e:
                result_text = f"Error executing tool '{tool_name}' on MCP server: {e}"

            # Print Raw MCP Server Result
            print_step("⚙️ MCP Server Tool Output", result_text, style="magenta")

            # Step 3: Pass tool result back to Groq for final response synthesis
            full_payload.append(response_message)  # Include the assistant's tool_calls message
            full_payload.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": tool_name,
                "content": result_text
            })

        # Generate final answer from Groq with tool context
        final_response = groq_client.chat.completions.create(
            model=groq_model,
            messages=full_payload,
            temperature=0.3
        )
        final_answer = final_response.choices[0].message.content
        print_step("💬 Assistant Final Response", final_answer, style="green")

        # Keep short conversational memory
        conversation_history.append({"role": "user", "content": user_input})
        conversation_history.append({"role": "assistant", "content": final_answer})

    else:
        # Case B: LLM answered directly without tool calling
        direct_answer = response_message.content or "(No response content)"
        print_step("💬 Assistant Response (Direct)", direct_answer, style="green")
        conversation_history.append({"role": "user", "content": user_input})
        conversation_history.append({"role": "assistant", "content": direct_answer})


async def run_client():
    """Main client startup and interactive REPL loop."""
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
            console.print("[yellow]Please create a .env file with your Groq API key: GROQ_API_KEY=gsk_...[/yellow]\n")
        else:
            print("WARNING: GROQ_API_KEY not configured. Set GROQ_API_KEY in .env or environment.")

        # Prompt user interactively if not set in environment
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
        console.print(f"[cyan]Connecting to MCP Server: [dim]{server_script.name}[/dim]...[/cyan]")

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
                tool_table = Table(title="Discovered MCP Tools", border_style="cyan")
                tool_table.add_column("Tool Name", style="bold yellow")
                tool_table.add_column("Description", style="white")
                for t in mcp_tools:
                    tool_table.add_row(t.name, t.description or "")
                console.print(tool_table)
                console.print("\n[bold green]Ready! Type your query, or 'exit' / 'quit' to stop.[/bold green]")
                console.print("[dim]Examples:[/dim]")
                console.print("  • [italic]Remember that my project deadline is next Friday #academic[/italic]")
                console.print("  • [italic]What notes do I have about the project deadline?[/italic]")
                console.print("  • [italic]Find all notes tagged with coursework[/italic]\n")
            else:
                print(f"Discovered {len(mcp_tools)} MCP tools: {[t.name for t in mcp_tools]}")
                print("Ready! Type your query, or 'exit' / 'quit' to stop.\n")

            conversation_history: List[Dict[str, Any]] = []

            # Interactive loop
            while True:
                try:
                    user_input = input("\nYou > ").strip()
                    if not user_input:
                        continue
                    if user_input.lower() in ("exit", "quit", "q"):
                        print("Goodbye!")
                        break

                    await process_user_query(
                        session=session,
                        groq_client=groq_client,
                        groq_model=groq_model,
                        groq_tools=groq_tools,
                        user_input=user_input,
                        conversation_history=conversation_history
                    )

                except (KeyboardInterrupt, EOFError):
                    print("\nSession terminated by user. Goodbye!")
                    break
                except Exception as e:
                    if HAS_RICH:
                        console.print(f"[bold red]Error during interaction:[/bold red] {e}")
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
