#!/usr/bin/env python3
"""
Reachy Mini Moves — OpenClaw skill script
Controls recorded dances and emotions via the Reachy Mini daemon REST API.

Usage:
  python dances.py list dances
  python dances.py list emotions
  python dances.py list all
  python dances.py play dances <name>
  python dances.py play emotions <name>
  python dances.py random dances
  python dances.py random emotions
  python dances.py running
  python dances.py stop-all
  python dances.py --base-url http://reachy-mini.local:8000 play emotions happy
"""

import argparse
import json
import random
import sys
import urllib.error
import urllib.request

DATASETS = {
    "dances":   "pollen-robotics/reachy-mini-dances-library",
    "emotions": "pollen-robotics/reachy-mini-emotions-library",
}
DEFAULT_BASE_URL = "http://127.0.0.1:8000"


# ── HTTP helpers ─────────────────────────────────────────────────────────────

def _request(base_url: str, method: str, path: str, body: dict = None):
    url = f"{base_url}{path}"
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"ERROR {e.code} from {url}: {e.read().decode()}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(
            f"ERROR: Cannot reach daemon at {base_url} — is it running?\n  {e.reason}",
            file=sys.stderr,
        )
        sys.exit(1)


def _fetch_library(base_url: str, kind: str) -> list[str]:
    dataset = DATASETS[kind]
    return _request(base_url, "GET", f"/api/move/recorded-move-datasets/list/{dataset}")


def _play(base_url: str, kind: str, name: str) -> dict:
    dataset = DATASETS[kind]
    result = _request(
        base_url, "POST",
        f"/api/move/play/recorded-move-dataset/{dataset}/{name}",
    )
    icon = "💃" if kind == "dances" else "😊"
    print(f"{icon} Playing [{kind}]: {name}")
    print(f"  Move UUID: {result.get('uuid', result)}")
    return result


# ── Commands ─────────────────────────────────────────────────────────────────

def cmd_list(base_url: str, kind: str):
    if kind == "all":
        for k in ("dances", "emotions"):
            moves = _fetch_library(base_url, k)
            label = "Dances" if k == "dances" else "Emotions"
            print(f"\n{label} ({len(moves)}):")
            for name in sorted(moves):
                print(f"  • {name}")
    else:
        moves = _fetch_library(base_url, kind)
        if not moves:
            print(f"No {kind} found.")
            return
        print(f"Available {kind} ({len(moves)}):")
        for name in sorted(moves):
            print(f"  • {name}")


def cmd_play(base_url: str, kind: str, name: str):
    # fuzzy-match: if exact name not found, try case-insensitive substring
    moves = _fetch_library(base_url, kind)
    if name not in moves:
        matches = [m for m in moves if name.lower() in m.lower()]
        if len(matches) == 1:
            print(f"  (matched '{name}' → '{matches[0]}')")
            name = matches[0]
        elif len(matches) > 1:
            print(f"Ambiguous name '{name}'. Did you mean one of:")
            for m in matches:
                print(f"  • {m}")
            sys.exit(1)
        else:
            print(f"ERROR: '{name}' not found in {kind} library.", file=sys.stderr)
            print(f"Run: python dances.py list {kind}", file=sys.stderr)
            sys.exit(1)
    _play(base_url, kind, name)


def cmd_random(base_url: str, kind: str):
    moves = _fetch_library(base_url, kind)
    if not moves:
        print(f"No {kind} available.")
        sys.exit(1)
    choice = random.choice(moves)
    print(f"🎲 Randomly selected from {kind}: {choice}")
    _play(base_url, kind, choice)


def cmd_running(base_url: str):
    moves = _request(base_url, "GET", "/api/move/running")
    if not moves:
        print("No moves currently running.")
    else:
        print(f"Running moves ({len(moves)}):")
        for m in moves:
            print(f"  • {m.get('uuid', m)}")
    return moves


def cmd_stop_all(base_url: str):
    moves = _request(base_url, "GET", "/api/move/running")
    if not moves:
        print("Nothing is running — nothing to stop.")
        return
    for m in moves:
        uuid = m.get("uuid") if isinstance(m, dict) else m
        _request(base_url, "POST", "/api/move/stop", {"uuid": uuid})
        print(f"⏹  Stopped: {uuid}")
    print(f"Stopped {len(moves)} move(s).")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Control Reachy Mini dances and emotions via the daemon REST API."
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Daemon base URL (default: {DEFAULT_BASE_URL})",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # list [dances|emotions|all]
    list_p = sub.add_parser("list", help="List available moves")
    list_p.add_argument(
        "kind",
        choices=["dances", "emotions", "all"],
        help="Which library to list",
    )

    # play <dances|emotions> <name>
    play_p = sub.add_parser("play", help="Play a specific move by name")
    play_p.add_argument("kind", choices=["dances", "emotions"])
    play_p.add_argument("name", help="Name of the move to play")

    # random <dances|emotions>
    rand_p = sub.add_parser("random", help="Play a random move")
    rand_p.add_argument("kind", choices=["dances", "emotions"])

    sub.add_parser("running",  help="Show currently running moves")
    sub.add_parser("stop-all", help="Stop all currently running moves")

    args = parser.parse_args()

    if args.command == "list":
        cmd_list(args.base_url, args.kind)
    elif args.command == "play":
        cmd_play(args.base_url, args.kind, args.name)
    elif args.command == "random":
        cmd_random(args.base_url, args.kind)
    elif args.command == "running":
        cmd_running(args.base_url)
    elif args.command == "stop-all":
        cmd_stop_all(args.base_url)


if __name__ == "__main__":
    main()
