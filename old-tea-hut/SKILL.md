---
name: autopos
description: Order drinks from Old Tea Hut (Changi City Point) via AutoPOS. Handles the full agentic ordering flow — menu lookup, SKU resolution, order submission, payment link, and confirmation polling.
metadata: {"clawdbot":{"emoji":"🧋","requires":{"bins":["python3"]}}}
---

# autopos

Use `autopos` to order drinks from **Old Tea Hut, Changi City Point (#B1-K5)** for the user.

The script is a pure API layer. **You (the LLM) are responsible for all natural language understanding and order resolution.** The script only accepts structured inputs.

Script path: `~/.openclaw/workspace/skills/autopos/autopos.py`

---

## Agentic Flow

### Step 1 — Get the menu
```bash
python3 ~/.openclaw/workspace/skills/autopos/autopos.py menu
```
Returns compact JSON:
- `token` — reuse for `spu` calls in this session
- `confirm_required` — if true, you must confirm with the user before submitting
- `categories[].items[]` — each item has `spuPid`, `name`, `name2`, `priceFrom`, `soldOut`

Match the user's drink request against `name` (e.g. `[GMT] Gula Melaka Milk Tea`), `name2` (Chinese name), or the shortcode inside brackets (e.g. `GMT`, `KO`, `JS`).

### Step 2 — Get SKU detail for each matched item
```bash
python3 ~/.openclaw/workspace/skills/autopos/autopos.py spu <spuPid>
```
Returns full detail for one item:
- `skus[]` — each SKU has `skuPid`, `price`, and `temp` (list of temperature names e.g. `["Iced"]`)
- `featureGroups[]` — required customisations, pick one `attrPid` per group (e.g. Sweetness). Each attr has `attrPid`, `name`, `price`.
- `extraGroups[]` — extra customisations; if `required=true` pick `min` to `max` attrs (e.g. Intensity is required with min=1)

**How to resolve an item:**
1. Pick `skuPid` by matching user's temperature to `skus[].temp[0]` — default to `"Iced"`
2. Pick one `attrPid` from each `featureGroup` — default to first attr (Regular/100%)
3. Pick one `attrPid` from each required `extraGroup` — default to first attr (Regular)
4. Price = `sku.price` + sum of any selected attr prices with non-zero price

Call `spu` once per **unique** item (not per quantity).

### Step 3 — Show summary and get user confirmation
**You must do this before calling submit or confirm.** Show the order clearly:
```
🧋 Order Summary:
  1× [GMT] Gula Melaka Milk Tea — Iced, Siew Dai, Regular — $2.10
  1× [KO] Coffee O — Hot, Kosong, Strong — $1.50
  ──────────────────────
  Total: SGD 3.60
  Pickup: Old Tea Hut, Changi City Point #B1-K5

Confirm order? (yes / no)
```
Wait for an explicit confirmation from the user ("yes", "ok", "confirm", "yep", etc.).
If they say no or want changes, re-resolve and show the summary again.

### Step 4 — Record confirmation (mandatory gate)
Once the user confirms, call `confirm` passing the resolved items and total:
```bash
python3 ~/.openclaw/workspace/skills/autopos/autopos.py confirm '<items_json>' <total>
```
This saves the order to a gate file. **`submit` will be BLOCKED if this is not called first.**

`items_json` is the same JSON array you resolved in Step 2:
```json
[
  {
    "spuPid": "12RwbXhjM5Z5ztnUQKBm3V",
    "skuPid": "12RwbXhjM5ZppQz33wTRXu",
    "qty": 1,
    "featurePidList": ["12RvCAvh1B4YEyHvCLnWRu"],
    "extraList": [
      {"attrPid": "12RwXXv4EL5wskLiVzTxGF", "unitQty": 1}
    ]
  }
]
```

### Step 5 — Submit the order
```bash
python3 ~/.openclaw/workspace/skills/autopos/autopos.py submit
```
**No arguments.** The script reads the order from the gate file written by `confirm`.
This avoids any JSON shell-escaping issues entirely.

`items_json` is a JSON array (must be single-quoted):
```json
[
  {
    "spuPid": "12RwbXhjM5Z5ztnUQKBm3V",
    "skuPid": "12RwbXhjM5ZppQz33wTRXu",
    "qty": 1,
    "featurePidList": ["12RvCAvh1B4YEyHvCLnWRu"],
    "extraList": [
      {"attrPid": "12RwXXv4EL5wskLiVzTxGF", "unitQty": 1}
    ]
  }
]
```
`total` = sum of all item prices, rounded to 2 decimal places.

Returns `orderId`, `paymentUrl`, and `total`.

**Immediately send the `paymentUrl` to the user.** The payment page displays the Pickup Code and Order Number directly after payment — no further polling needed from the agent.

---

## Quick Reference — Common Shortcodes

| Code | Name | From |
|------|------|------|
| GMT | Gula Melaka Milk Tea | $2.10 |
| HTC | Honey Milk Tea | $1.90 |
| K | Coffee (Kopi) | $1.60 |
| KO | Coffee O (Kopi O) | $1.50 |
| KC | Coffee C (Kopi C) | $1.70 |
| YY | Yuan Yang | $1.90 |
| JS | Japanese Sencha | $1.80 |
| HJS | Honey Japanese Sencha | $2.10 |
| OO | Golden Oolong | $2.00 |
| HLe | Honey Lemon | $1.90 |
| AM | Almond Milk | $2.00 |
| M | Milo | $2.10 |

These are starting prices — actual price depends on SKU (temperature variant).

---

## Notes
- Always call `menu` first — the token it returns is needed for `spu` calls
- Never hardcode PIDs — always resolve from live `menu` + `spu` output
- If an item has `soldOut: true`, tell the user and ask for a substitute
- The shop is **pickup only** — no delivery
- If the user asks to browse the menu, format `categories` output in a readable way before asking what they'd like
