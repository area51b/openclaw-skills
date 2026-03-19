# OpenClaw Skills

A small collection of **OpenClaw skills** (agent scripts) that expose structured APIs for external services.

This repository currently contains a single skill:

- **`autopos`** — Order drinks from **Old Tea Hut, Changi City Point** via their AutoPOS API.

---

## ✅ What is an OpenClaw skill?

An OpenClaw skill is a lightweight script + metadata bundle that can be invoked by an LLM-based agent. Skills expose structured commands (JSON input/JSON output) so the LLM handles natural language understanding and the skill handles API calls.

## 🚀 Quick Install (for OpenClaw users)

### 1) Clone this repo (if you haven’t already)

```bash
git clone https://github.com/<your-org>/openclaw-skills.git
cd openclaw-skills
```

### 2) Install the skill into OpenClaw

OpenClaw expects skills to live under your OpenClaw workspace folder.

#### Linux / macOS / WSL

```bash
mkdir -p ~/.openclaw/workspace/skills
cp -r old-tea-hut ~/.openclaw/workspace/skills/autopos
```

#### Windows (PowerShell)

```powershell
$skillDest = "$env:USERPROFILE\.openclaw\workspace\skills\autopos"
New-Item -ItemType Directory -Force -Path $skillDest
Copy-Item -Recurse -Path .\old-tea-hut\* -Destination $skillDest
```

> ✅ Tip: You can also create a symlink instead of copying if you want to keep the repo in sync.

### 3) Install Python dependencies

This skill requires `python3` and the `requests` package.

```bash
python3 -m pip install --user requests
```

## ⚙️ Configure the skill

Open `autopos.py` and set your receiver details:

- `RECEIVER_NAME` — your name (shown in the order)
- `RECEIVER_TEL` — your phone number (used for order contact)

These are at the top of `old-tea-hut/autopos.py`.

---

## 🧋 Using the `autopos` skill

The `autopos` script supports the following commands (the LLM typically drives this flow):

1. **Get the menu**
   ```bash
   python3 ~/.openclaw/workspace/skills/autopos/autopos.py menu
   ```

2. **Get SKU details for an item**
   ```bash
   python3 ~/.openclaw/workspace/skills/autopos/autopos.py spu <spuPid>
   ```

3. **Confirm an order (required before submit)**
   ```bash
   python3 ~/.openclaw/workspace/skills/autopos/autopos.py confirm '<items_json>' <total>
   ```

4. **Submit the confirmed order**
   ```bash
   python3 ~/.openclaw/workspace/skills/autopos/autopos.py submit
   ```

5. **Check order status**
   ```bash
   python3 ~/.openclaw/workspace/skills/autopos/autopos.py status [orderId]
   ```

> 📌 The skill is designed to be driven by an agent. It only accepts structured inputs and returns JSON output so the agent can safely parse it.

---

## 🧠 How this skill works

- `menu` fetches a compact menu and returns a `token` used for subsequent calls.
- `spu <spuPid>` fetches SKU/customisation details for one item.
- `confirm` stores the resolved order and acts as a safety gate before submission.
- `submit` sends the order and returns a payment URL.

---

## 📄 License

This repo is licensed under the terms of the [MIT License](LICENSE).
