"""
==============================================================================
Experiment 1: "Personal Assistant" Memory MCP Server
==============================================================================
This MCP (Model Context Protocol) server implements a lightweight personal memory
store backed by a local JSON file (notes.json). It exposes two tools:
  1. `save_note`: Appends a new note with metadata (timestamp, ID, tags).
  2. `search_notes`: Performs case-insensitive search across note content & tags.

Architecture:
  - Uses the official Python MCP SDK (`mcp.server.fastmcp.FastMCP`).
  - Automatically handles file creation, missing files, and malformed JSON.
  - Communicates over standard input/output (stdio) with any MCP client.
==============================================================================
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure UTF-8 streams on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from mcp.server.fastmcp import FastMCP

# Define path to notes.json in the same directory as this server script
NOTES_FILE_PATH = Path(__file__).parent / "notes.json"

# Initialize FastMCP Server with a descriptive server name
# FastMCP uses Python type hints and docstrings to automatically generate
# standard MCP Tool Schemas (JSON Schema format) that LLMs can consume.
mcp = FastMCP("personal-assistant-memory")


def _load_notes() -> List[Dict[str, Any]]:
    """
    Safely load notes from notes.json.
    
    Self-healing design:
    - If the file does not exist, an empty list is returned and written.
    - If the file is empty or corrupted (malformed JSON), it resets gracefully
      without crashing the MCP server.
    """
    if not NOTES_FILE_PATH.exists():
        _save_notes_to_file([])
        return []

    try:
        with open(NOTES_FILE_PATH, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return []
            data = json.loads(content)
            if isinstance(data, list):
                return data
            # If the top-level structure is not a list, wrap or reset
            return []
    except (json.JSONDecodeError, OSError) as e:
        # Log warning to stderr (stdio stdout is reserved for MCP JSON-RPC protocol messages)
        print(f"[Server Warning] Could not parse {NOTES_FILE_PATH.name} ({e}). Resetting to empty list.", file=sys.stderr)
        return []


def _save_notes_to_file(notes: List[Dict[str, Any]]) -> None:
    """
    Safely persist notes list to notes.json with proper indentation.
    """
    try:
        with open(NOTES_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(notes, f, indent=2, ensure_ascii=False)
    except OSError as e:
        print(f"[Server Error] Failed to write to {NOTES_FILE_PATH.name}: {e}", file=sys.stderr)
        raise


# ============================================================================
# MCP TOOL REGISTRATION
# ============================================================================
# The `@mcp.tool()` decorator registers the function as an MCP tool.
# FastMCP inspects function signatures, type annotations, and docstrings to
# generate the inputSchema used by LLM function calling (e.g., Groq / Llama).
# ============================================================================

@mcp.tool()
def save_note(content: str, tags: Optional[List[str]] = None) -> str:
    """
    Save a new note to the personal assistant's persistent memory.

    Args:
        content: The text content of the note to remember.
        tags: Optional list of keyword tags for categorizing the note (e.g. ['work', 'urgent']).

    Returns:
        A confirmation message with the assigned note ID and creation timestamp.
    """
    if not content or not content.strip():
        return "Error: Note content cannot be empty."

    # Normalize tags list
    clean_tags = [str(t).strip().lower() for t in (tags or []) if str(t).strip()]

    # Load existing notes
    notes = _load_notes()

    # Generate an auto-incrementing integer ID
    existing_ids = [n.get("id", 0) for n in notes if isinstance(n.get("id"), int)]
    next_id = (max(existing_ids) + 1) if existing_ids else 1

    # Create timestamp in ISO 8601 format
    timestamp = datetime.now().isoformat()

    new_note: Dict[str, Any] = {
        "id": next_id,
        "content": content.strip(),
        "tags": clean_tags,
        "timestamp": timestamp
    }

    notes.append(new_note)
    _save_notes_to_file(notes)

    tag_str = f" [tags: {', '.join(clean_tags)}]" if clean_tags else ""
    return f"Note #{next_id} successfully saved at {timestamp}{tag_str}: \"{content.strip()}\""


@mcp.tool()
def search_notes(query: str) -> str:
    """
    Search saved notes by keyword or tag. Performs a case-insensitive substring search
    across all note contents and tag lists.

    Args:
        query: The search term or keyword to find relevant notes.

    Returns:
        A formatted list of matching notes with IDs, timestamps, content, and tags,
        or a message indicating no matches were found.
    """
    if not query or not query.strip():
        return "Error: Search query cannot be empty."

    search_term = query.strip().lower()
    notes = _load_notes()

    if not notes:
        return "Memory is currently empty. No notes have been saved yet."

    matches: List[Dict[str, Any]] = []
    for note in notes:
        note_content = str(note.get("content", "")).lower()
        note_tags = [str(t).lower() for t in note.get("tags", [])]

        # Match either in content or in any of the tags
        if search_term in note_content or any(search_term in t for t in note_tags):
            matches.append(note)

    if not matches:
        return f"No notes found matching '{query}'."

    # Format the matched notes for the LLM to read easily
    results = [f"Found {len(matches)} matching note(s) for query '{query}':"]
    for n in matches:
        tags_display = f" (Tags: {', '.join(n.get('tags', []))})" if n.get("tags") else ""
        results.append(
            f"• [ID #{n.get('id')}] [{n.get('timestamp')[:19]}]{tags_display}\n  \"{n.get('content')}\""
        )

    return "\n\n".join(results)


if __name__ == "__main__":
    # Ensure notes file exists on startup
    _load_notes()
    # Run the server using stdio transport (Standard input/output JSON-RPC stream)
    # This enables any MCP client (Python client, Claude Desktop, Antigravity) to spawn
    # this process and communicate over stdin/stdout.
    mcp.run(transport="stdio")
