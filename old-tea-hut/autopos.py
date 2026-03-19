#!/usr/bin/env python3
"""
autopos.py — AutoPOS API layer for OpenClaw
Old Tea Hut, Changi City Point

Pure API layer. Zero NLP. The LLM agent resolves all natural language
and calls this script with structured inputs only.

Commands:
  menu                          Compact menu JSON for LLM (pass 1)
  spu <spuPid>                  Full SKU + attr detail for one item (pass 2)
  confirm <items_json> <total>  Save resolved order + record user confirmation
  submit                        Submit the confirmed order (no args — reads from confirm)
  status [orderId]              Poll order confirmation
  refresh                       Force refresh menu cache
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime

try:
    import requests
except ImportError:
    print(json.dumps({"error": "requests not installed. Run: pip3 install requests"}))
    sys.exit(1)

# ─────────────────────────────────────────────
# CONFIG — edit these
# ─────────────────────────────────────────────

QR_CODE  = "2DbtNuxweU5W6f4NL16D4dHqmpAdVE3qBJdTpUztrdi7BUGhsWAKAeDNHRQKdm"
QR_HASH  = "pq3Cu"
QR_TYPE  = "S"
BASE_URL = "https://autopos.cloud/api/public/ordering"

RECEIVER_NAME  = "OpenClaw"   # ← update to your name
RECEIVER_TEL   = "91112222"   # ← update to your number

CACHE_FILE    = Path(__file__).parent / "cache.json"
CONFIRM_FILE  = Path(__file__).parent / "pending_confirm.json"  # gate file

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Origin": "https://autopos.cloud",
    "Referer": "https://autopos.cloud/h5/qr",
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
}


# ─────────────────────────────────────────────
# HELPERS — all output is JSON so the agent can parse it
# ─────────────────────────────────────────────

def out(data):
    print(json.dumps(data, indent=2, ensure_ascii=False))

def err(msg):
    print(json.dumps({"error": msg}))
    sys.exit(1)

def load_cache():
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text())
        except Exception:
            pass
    return {}

def save_cache(data):
    CACHE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))


# ─────────────────────────────────────────────
# RAW API CALLS
# ─────────────────────────────────────────────

def api_qr():
    r = requests.post(f"{BASE_URL}/qr", headers=HEADERS, json={
        "code": QR_CODE, "hash": QR_HASH, "type": QR_TYPE, "expectTime": None
    }, timeout=15)
    r.raise_for_status()
    d = r.json()
    if d.get("code") != 200:
        err(f"QR API error: {d}")
    return d["data"]

def api_check_sales(token):
    r = requests.post(f"{BASE_URL}/check/sales", headers=HEADERS, json={
        "itemList": [], "deliveryMode": "P",
        "expectTime": None, "checkout": True, "token": token
    }, timeout=10)
    r.raise_for_status()

def api_spu(spu_pid, token):
    r = requests.post(f"{BASE_URL}/spu", headers=HEADERS, json={
        "spuPid": spu_pid, "token": token
    }, timeout=10)
    r.raise_for_status()
    d = r.json()
    if d.get("code") != 200:
        err(f"SPU API error: {d}")
    return d["data"]

def api_submit(token, item_list, total):
    r = requests.post(f"{BASE_URL}/submit", headers=HEADERS, json={
        "deliveryMode": "P",
        "checkoutMethod": "O",
        "memo": "",
        "orderingAmount": total,
        "itemList": item_list,
        "receiverTel": RECEIVER_TEL,
        "receiverName": RECEIVER_NAME,
        "expectTime": None,
        "dueAmount": total,
        "token": token
    }, timeout=15)
    r.raise_for_status()
    d = r.json()
    if d.get("code") != 200:
        err(f"Submit error: {d}")
    return d["data"]

def api_payment_create(order_id, token):
    redirect_url = (
        f"https://autopos.cloud/h5/orderStatus"
        f"?token={token}&orderId={order_id}"
    )
    r = requests.post(f"{BASE_URL}/payment/create", headers=HEADERS, json={
        "orderId": order_id,
        "redirectUrl": redirect_url,
        "token": token
    }, timeout=15)
    r.raise_for_status()
    d = r.json()

    yeahpay_token = None
    if d.get("code") == 200 and d.get("data"):
        pd = d["data"]
        yeahpay_token = (
            pd.get("payToken") or pd.get("token") or
            pd.get("authorization") or pd.get("cashierToken")
        )
        if pd.get("url") and "yeahpay" in str(pd.get("url")):
            return pd["url"]

    # Save session — mirrors browser behaviour
    requests.post(f"{BASE_URL}/session/save", headers=HEADERS, json={
        "session": json.dumps({
            "queryInfo": {"c": QR_CODE, "h": QR_HASH, "t": QR_TYPE},
            "shopInfo": {
                "shopPid": "12SKARQLFQWaYV9zGUWKH2", "shopCode": "10",
                "shopName": "OLD TEA HUT CHANGI CITY POINT",
                "brandPid": "12Rv9PZcACSZHxHW1ccrUf", "country": "SG",
                "deliveryModes": "TP", "deliveryModeDef": "P",
                "orderingMode": "O", "checkoutMethod": "O",
            },
            "langCur": "en", "deliveryModeCur": "P",
            "checkoutMethodCur": "O", "tableNo": "", "carList": [], "remark": ""
        }),
        "token": token
    }, timeout=10)

    if yeahpay_token:
        return (
            f"https://payment.yeahpay.net/checkout/h5/#/checkstand"
            f"?token={yeahpay_token}&lang=en&supportC2P=1&countdown=5"
        )
    return redirect_url  # fallback: AutoPOS order status page also loads cashier

def api_order_status(order_id, token):
    r = requests.get(f"{BASE_URL}/order/info", headers=HEADERS,
                     params={"orderId": order_id, "token": token}, timeout=10)
    r.raise_for_status()
    d = r.json()
    return d.get("data", {}) if d.get("code") == 200 else {}


# ─────────────────────────────────────────────
# COMMANDS
# ─────────────────────────────────────────────

def cmd_menu(force_refresh=False):
    """
    Pass 1 — compact menu for the LLM to resolve the user's order against.

    The LLM should:
    1. Match user's drink names to items using name/name2/shortcode (e.g. [GMT])
    2. For each matched item, call: autopos.py spu <spuPid>
    3. From the spu response, select skuPid, featurePidList, extraList
    4. Call: autopos.py submit '<items_json>' <total>

    If confirm_required is true, show the order summary to the user
    and wait for confirmation before calling submit.
    """
    cache = load_cache()
    qr_data = api_qr()
    new_ver = qr_data.get("dataVer")

    if not force_refresh and cache.get("dataVer") == new_ver and "spuCateList" in cache:
        spu_cate_list = cache["spuCateList"]
    else:
        spu_cate_list = qr_data["spuCateList"]
        cache.update({
            "dataVer": new_ver,
            "spuCateList": spu_cate_list,
            "cachedAt": datetime.utcnow().isoformat(),
        })
        save_cache(cache)

    # Save token for spu lookups in same session
    cache["lastToken"] = qr_data["token"]
    save_cache(cache)

    categories = []
    for cat in spu_cate_list:
        items = []
        for spu in cat.get("spuList", []):
            if spu.get("selloutFlag"):
                continue  # skip sold out items entirely
            items.append({
                "spuPid": spu["spuPid"],
                "name":   spu["spuName"],          # e.g. "[GMT] Gula Melaka Milk Tea"
                "price":  spu.get("priceMin", spu.get("price", 0)),
            })
        if items:
            categories.append({"category": cat["spuCateName"], "items": items})

    out({
        "token":      qr_data["token"],
        "categories": categories,
    })


def cmd_spu(spu_pid):
    """
    Pass 2 — full SKU and customisation detail for one item.

    The LLM uses this to:
    - Pick the correct skuPid based on temperature (iced/warm/hot/less ice)
    - Pick featurePidList entries (one per featureGroup, e.g. sweetness)
    - Pick extraList entries (required: one per required extraGroup e.g. intensity)
    - Calculate the final price from sku.salePrice + any attr prices

    skus[].specs tells you which temperature options map to which skuPid.
    featureGroups are required choices (e.g. sweetness level).
    extraGroups with required=true must have exactly minQty..maxQty attrs chosen.
    """
    cache = load_cache()
    token = cache.get("lastToken")
    if not token:
        qr_data = api_qr()
        token = qr_data["token"]
        cache["lastToken"] = token
        save_cache(cache)

    raw = api_spu(spu_pid, token)

    # Compact SKU list — temp name as simple string, not nested object
    skus = []
    for sku in raw.get("skuList", []):
        spec_pids = set(sku.get("specPidSet", []))
        temp_names = []
        for sg in raw.get("specGroupList", []):
            for spec in sg.get("specList", []):
                if spec["specPid"] in spec_pids:
                    temp_names.append(spec["specName"])
        skus.append({
            "skuPid": sku["skuPid"],
            "price":  sku["salePrice"],
            "temp":   temp_names,  # e.g. ["Iced"] or ["Less Ice"]
        })

    first_sku = raw.get("skuList", [{}])[0] if raw.get("skuList") else {}

    # Feature groups — drop sold-out attrs
    feature_groups = []
    for fg in first_sku.get("featureGroupList", []):
        attrs = [
            {"attrPid": a["attrPid"], "name": a["attrName"], "price": a.get("price", 0)}
            for a in fg.get("attrList", []) if not a.get("selloutFlag")
        ]
        if attrs:
            feature_groups.append({"group": fg["attrGroupName"], "attrs": attrs})

    # Extra groups — drop sold-out attrs
    extra_groups = []
    for eg in first_sku.get("extraGroupList", []):
        attrs = [
            {"attrPid": a["attrPid"], "name": a["attrName"], "price": a.get("price", 0)}
            for a in eg.get("attrList", []) if not a.get("selloutFlag")
        ]
        if attrs:
            extra_groups.append({
                "group":    eg["attrGroupName"],
                "required": eg.get("minQty", 0) > 0,
                "min":      eg.get("minQty", 0),
                "max":      eg.get("maxQty", 1),
                "attrs":    attrs,
            })

    out({
        "spuPid":        raw["spuPid"],
        "name":          raw["spuName"],
        "skus":          skus,
        "featureGroups": feature_groups,
        "extraGroups":   extra_groups,
    })


def cmd_confirm(items_json, total):
    """
    Gate command — MUST be called after showing the order summary to the user
    and receiving their explicit confirmation ("yes", "ok", "confirm", etc.).

    Saves the resolved order to pending_confirm.json.
    After this, call: autopos.py submit  (no arguments needed)
    """
    try:
        items = json.loads(items_json)
        total = round(float(total), 2)
    except Exception as e:
        err(f"Invalid arguments: {e}")

    gate = {
        "confirmed":   True,
        "items":       items,
        "total":       total,
        "confirmedAt": datetime.utcnow().isoformat(),
    }
    CONFIRM_FILE.write_text(json.dumps(gate, indent=2, ensure_ascii=False))

    out({
        "status":  "confirmed",
        "message": "Order confirmed by user. Now call: autopos.py submit",
        "total":   f"SGD {total:.2f}",
    })


def cmd_submit():
    """
    Submit the confirmed order. No arguments — reads from pending_confirm.json
    written by the confirm command. This avoids any JSON shell-escaping issues.

    Will error if confirm has not been called first.
    """
    # ── HARD GATE ─────────────────────────────────────────────────────────
    if not CONFIRM_FILE.exists():
        err(
            "BLOCKED: confirmation required before submit. "
            "Show order summary to user, get confirmation, "
            "then call: autopos.py confirm '<items_json>' <total>"
        )
    try:
        gate = json.loads(CONFIRM_FILE.read_text())
    except Exception:
        err("BLOCKED: pending_confirm.json is corrupted. Call confirm again.")

    if not gate.get("confirmed"):
        err("BLOCKED: confirmation gate not satisfied. Call confirm first.")

    items = gate["items"]
    total = round(float(gate["total"]), 2)

    # Consume the gate — can't be reused
    CONFIRM_FILE.unlink()
    # ──────────────────────────────────────────────────────────────────────

    if not items:
        err("Confirmed items list is empty.")

    # Fresh token for submission
    qr_data = api_qr()
    token   = qr_data["token"]

    api_check_sales(token)

    # Expand qty — API expects unitQty=1 per line
    api_items = []
    for item in items:
        for _ in range(item.get("qty", 1)):
            api_items.append({
                "spuType":        "G",
                "spuPid":         item["spuPid"],
                "skuPid":         item["skuPid"],
                "unitQty":        1,
                "featurePidList": item.get("featurePidList", []),
                "extraList":      item.get("extraList", []),
            })

    order_data = api_submit(token, api_items, total)
    order_id   = (
        order_data.get("orderId") or
        order_data.get("orderPid") or
        order_data.get("id") or
        str(order_data)
    )

    payment_url = api_payment_create(order_id, token)

    # Persist for status polling
    cache = load_cache()
    cache["lastOrder"] = {
        "orderId":   order_id,
        "token":     token,
        "total":     total,
        "createdAt": datetime.utcnow().isoformat(),
    }
    save_cache(cache)

    out({
        "status":     "submitted",
        "orderId":    order_id,
        "total":      f"SGD {total:.2f}",
        "paymentUrl": payment_url,
        "pickup":     "Old Tea Hut, Changi City Point #B1-K5",
        "nextStep":   "Send paymentUrl to user. The payment page shows the Pickup Code and Order Number — no further polling needed.",
    })


def cmd_status(order_id=None):
    """
    Poll for payment confirmation. Runs for up to 3 minutes (18 × 10s).
    Use --once flag to check a single time and return immediately.
    """
    cache = load_cache()

    if not order_id:
        last     = cache.get("lastOrder", {})
        order_id = last.get("orderId")
        token    = last.get("token")
        if not order_id:
            err("No orderId provided and no recent order in cache")
    else:
        qr_data = api_qr()
        token   = qr_data["token"]

    once = "--once" in sys.argv

    for attempt in range(1, 19):
        try:
            data   = api_order_status(order_id, token)
            status = (
                data.get("status") or
                data.get("orderStatus") or
                data.get("payStatus")
            )

            if status in (2, "2", "paid", "confirmed", "PAID", "CONFIRMED", "SUCCESS"):
                order_no = (
                    data.get("orderNo") or data.get("orderCode") or
                    data.get("serialNo") or order_id
                )
                out({
                    "status":  "confirmed",
                    "orderNo": order_no,
                    "orderId": order_id,
                    "message": f"✅ Order confirmed! Order number: {order_no}. Pickup at Changi City Point #B1-K5.",
                })
                return

            if status in ("cancelled", "failed", "expired", "CANCELLED", "FAILED"):
                out({"status": status, "orderId": order_id,
                     "message": f"❌ Order {status}."})
                return

            if once:
                out({"status": status or "pending", "orderId": order_id})
                return

        except Exception as e:
            if once:
                out({"status": "error", "error": str(e)})
                return

        time.sleep(10)

    out({
        "status":   "timeout",
        "orderId":  order_id,
        "message":  "Payment not confirmed after 3 minutes.",
        "checkUrl": f"https://autopos.cloud/h5/orderStatus?orderId={order_id}",
    })


def cmd_refresh():
    qr_data = api_qr()
    spu_list = qr_data["spuCateList"]
    count    = sum(len(c["spuList"]) for c in spu_list)
    cache    = load_cache()
    cache.update({
        "dataVer":     qr_data.get("dataVer"),
        "spuCateList": spu_list,
        "cachedAt":    datetime.utcnow().isoformat(),
    })
    save_cache(cache)
    out({"status": "refreshed", "categories": len(spu_list),
         "items": count, "dataVer": qr_data.get("dataVer")})


# ─────────────────────────────────────────────
# ENTRYPOINT
# ─────────────────────────────────────────────

def main():
    args  = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]

    if not args:
        print(__doc__)
        sys.exit(1)

    cmd = args[0].lower()

    if cmd == "menu":
        cmd_menu(force_refresh="--refresh" in flags)
    elif cmd == "spu":
        if len(args) < 2:
            err("Usage: autopos.py spu <spuPid>")
        cmd_spu(args[1])
    elif cmd == "confirm":
        if len(args) < 3:
            err("Usage: autopos.py confirm '<items_json>' <total>")
        cmd_confirm(args[1], args[2])
    elif cmd == "submit":
        cmd_submit()
    elif cmd == "status":
        cmd_status(args[1] if len(args) > 1 else None)
    elif cmd == "refresh":
        cmd_refresh()
    else:
        err(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
