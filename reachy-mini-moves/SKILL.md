---
name: reachy-mini-moves
description: >
  Play, list, and manage recorded dance moves and emotions on a Reachy Mini
  robot via its local REST API. Use this skill whenever the user wants to make
  the Reachy Mini dance, express an emotion, show a feeling, list available
  moves or emotions, play a specific dance or emotion, or stop any move.
  Trigger on phrases like "make it dance", "play a dance", "list dances",
  "do the robot dance", "stop dancing", "make it happy", "show excitement",
  "express sadness", "play an emotion", "what emotions can it do", or any
  mention of Reachy Mini choreography, expressions, or feelings.
  Always use this skill — even for casual requests like "do something fun",
  "cheer it up", or "show off" — when a Reachy Mini robot is present.
---

# Reachy Mini Moves Skill

Control recorded dance moves and emotions on a Reachy Mini robot using its local REST API.

## Setup

- Daemon must be running (Lite: `http://localhost:8000`, Wireless: `http://reachy-mini.local:8000`)
- Default base URL: `http://127.0.0.1:8000`
- Script: `scripts/dances.py` — use this for all operations
- Two libraries available:
  - `dances` → `pollen-robotics/reachy-mini-dances-library`
  - `emotions` → `pollen-robotics/reachy-mini-emotions-library`

## Workflow

Always follow this order:
1. Determine whether the user wants a **dance** or an **emotion** (or both)
2. If no specific move named, **list first**, then ask or pick one
3. Use the script to execute the action
4. Report back what's happening (move UUID confirms it started)

**Tip**: For emotional/expressive requests ("make it happy", "show sadness") use `emotions`. For performance/entertainment requests ("make it dance", "do something fun") use `dances`.

## Using the Script

```bash
# --- DANCES ---
python scripts/dances.py list dances
python scripts/dances.py play dances <dance_name>
python scripts/dances.py random dances

# --- EMOTIONS ---
python scripts/dances.py list emotions
python scripts/dances.py play emotions <emotion_name>
python scripts/dances.py random emotions

# --- BOTH (lists everything) ---
python scripts/dances.py list all

# --- CONTROL ---
python scripts/dances.py running        # what's currently playing
python scripts/dances.py stop-all       # stop everything

# --- WIRELESS MODE ---
python scripts/dances.py --base-url http://reachy-mini.local:8000 list dances
python scripts/dances.py --base-url http://reachy-mini.local:8000 play emotions happy
```

## API Endpoints Used

| Action | Method | Endpoint |
|---|---|---|
| List dances | GET | `/api/move/recorded-move-datasets/list/pollen-robotics/reachy-mini-dances-library` |
| List emotions | GET | `/api/move/recorded-move-datasets/list/pollen-robotics/reachy-mini-emotions-library` |
| Play dance | POST | `/api/move/play/recorded-move-dataset/pollen-robotics/reachy-mini-dances-library/{name}` |
| Play emotion | POST | `/api/move/play/recorded-move-dataset/pollen-robotics/reachy-mini-emotions-library/{name}` |
| Stop a move | POST | `/api/move/stop` (body: `{"uuid": "..."}`) |
| List running | GET | `/api/move/running` |

## Response Notes

- **Play** returns a `MoveUUID` like `{"uuid": "abc-123-..."}` — confirms the move started
- **Running** returns a list of active move UUIDs — empty list means nothing is playing
- **Stop** requires the UUID from a running move; use `running` first to get it
- Move names are returned as plain strings from the list endpoints

## Example Interactions

**User:** "Make Reachy dance!"
→ `list dances`, pick one (or `random dances`), report which dance is playing

**User:** "Make it look happy"
→ `play emotions happy` (or `list emotions` first to confirm name)

**User:** "What can Reachy Mini express?"
→ `list emotions`, present the names clearly

**User:** "Show me everything it can do"
→ `list all`, present dances and emotions grouped

**User:** "Stop!"
→ `running` to get active UUIDs, then `stop-all`

## Error Handling

- **Connection refused**: Daemon isn't running — ask user to start it
- **404 on move name**: Name might differ slightly — run `list` and fuzzy-match
- **Empty running list**: Nothing is playing, nothing to stop
