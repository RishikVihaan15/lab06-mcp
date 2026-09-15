# Experiment Screenshots & Execution Walkthroughs

This folder contains execution logs, sample outputs, and visual demonstration walkthroughs for both Lab 06 MCP experiments.

---

## 📸 Experiment 1: Personal Assistant Memory Server

### Scenario 1: Saving a Note with Tags
**User Prompt:** `Remember that my CS 480 Lab 06 is due on Friday at 11:59 PM #academics #deadline`

```text
╭────────────────────────────────── 🤖 LLM Tool Selection Decision ──────────────────────────────────╮
│ Selected Tool : save_note                                                                          │
│ Arguments     : {                                                                                  │
│   "content": "CS 480 Lab 06 is due on Friday at 11:59 PM",                                         │
│   "tags": [                                                                                        │
│     "academics",                                                                                   │
│     "deadline"                                                                                     │
│   ]                                                                                                │
│ }                                                                                                  │
╰────────────────────────────────────────────────────────────────────────────────────────────────────╯

╭───────────────────────────────────── ⚙️ MCP Server Tool Output ────────────────────────────────────╮
│ Note #4 successfully saved at 2026-09-15T20:18:00.944244 [tags: academics, deadline]: "CS 480 Lab │
│ 06 is due on Friday at 11:59 PM"                                                                   │
╰────────────────────────────────────────────────────────────────────────────────────────────────────╯

╭──────────────────────────────────── 💬 Assistant Final Response ───────────────────────────────────╮
│ I have saved your note with ID #4 and tagged it with `academics` and `deadline`. I will remember   │
│ that your CS 480 Lab 06 is due on Friday at 11:59 PM.                                              │
╰────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### Scenario 2: Searching and Recalling Notes
**User Prompt:** `What do I have scheduled for this Friday?`

```text
╭────────────────────────────────── 🤖 LLM Tool Selection Decision ──────────────────────────────────╮
│ Selected Tool : search_notes                                                                       │
│ Arguments     : {                                                                                  │
│   "query": "Friday"                                                                                │
│ }                                                                                                  │
╰────────────────────────────────────────────────────────────────────────────────────────────────────╯

╭───────────────────────────────────── ⚙️ MCP Server Tool Output ────────────────────────────────────╮
│ Found 2 matching note(s) for query 'Friday':                                                       │
│                                                                                                    │
│ • [ID #1] [2026-09-15T10:00:00] (Tags: lab, deadline, coursework)                                  │
│   "CS 480 Lab 06 submission deadline is Friday at 11:59 PM."                                       │
│                                                                                                    │
│ • [ID #4] [2026-09-15T20:18:00] (Tags: academics, deadline)                                        │
│   "CS 480 Lab 06 is due on Friday at 11:59 PM"                                                     │
╰────────────────────────────────────────────────────────────────────────────────────────────────────╯

╭──────────────────────────────────── 💬 Assistant Final Response ───────────────────────────────────╮
│ You have the following deadline scheduled for Friday:                                              │
│ - **CS 480 Lab 06 Submission Deadline**: Due at **11:59 PM** (Tagged: `lab`, `deadline`,           │
│   `academics`, `coursework`).                                                                      │
╰────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

---

## 📸 Experiment 2: Data Dashboard Weather Connector

### Scenario 1: Tokyo Weather Query
**User Prompt:** `What is the current weather in Tokyo?`

```text
╭────────────────────── STAGE 1: 🧠 LLM Decision & Intent (Function Call Triggered) ──────────────────────╮
│ ⚡ Function Invocation Requested by LLM                                                                │
│ • Tool Name : get_current_weather                                                                      │
│ • Tool Call ID: call_abc123xyz                                                                         │
│ • Arguments : {                                                                                        │
│   "location": "Tokyo"                                                                                  │
│ }                                                                                                      │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────╯

╭──────────────── STAGE 2: ⚙️ Raw MCP Server Tool Execution Result (Live wttr.in Data) ────────────────╮
│ 📍 Location: Shikinejima, Tokyo, Japan                                                                │
│ 🌤️ Condition: Thundery outbreaks in nearby                                                             │
│ 🌡️ Temperature: 27°C (81°F) [Feels like: 31°C / 87°F]                                                 │
│ 💧 Humidity: 88%                                                                                       │
│ 💨 Wind: 15 km/h (9 mph) from SW                                                                       │
│ 🌧️ Precipitation: 0.1 mm                                                                               │
│ ☀️ UV Index: 0 | Visibility: 9 km                                                                      │
│ 🕒 Observation Time: 02:30 PM UTC                                                                      │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────╯

╭──────────────────────────────── STAGE 3: 💬 LLM Final Synthesized Response ────────────────────────────╮
│ Here is the current weather update for **Tokyo, Japan**:                                               │
│                                                                                                        │
│ - **Condition**: Thundery outbreaks nearby 🌤️⚡                                                         │
│ - **Temperature**: **27°C (81°F)** (Feels like **31°C / 87°F**)                                       │
│ - **Humidity**: 88%                                                                                    │
│ - **Wind**: 15 km/h from the Southwest                                                                 │
│ - **Precipitation**: 0.1 mm                                                                            │
│ - **Visibility**: 9 km                                                                                 │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

---

## 🖥️ How to Capture Your Own Terminal Screenshots

1. Configure your `.env` file with your Groq API key (`GROQ_API_KEY=gsk_...`).
2. Run client 1 in terminal:
   ```bash
   cd expt1-personal-assistant
   python client.py
   ```
3. Run client 2 in terminal:
   ```bash
   cd expt2-data-dashboard
   python client.py
   ```
4. Capture a screenshot of the clean styled output cards (`Win + Shift + S` on Windows or `Cmd + Shift + 4` on macOS) and save PNG files directly into this directory (`screenshots/expt1_run.png`, `screenshots/expt2_run.png`).
