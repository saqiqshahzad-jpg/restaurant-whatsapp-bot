import os
import sys
import time
import json
import re
import logging
import requests

# Reconfigure stdout/stderr for UTF-8 on Windows terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from fastapi import FastAPI, Request, BackgroundTasks, HTTPException, Response
from fastapi.responses import PlainTextResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
from openai import OpenAI
from dotenv import load_dotenv

# Ensure backend directory is in sys.path so imports work from ANY directory
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

try:
    from bot_logger import (
        bot_logger, log_ok, log_error, log_warn, log_info,
        log_llm, log_db, log_wa, log_security, log_cron,
        get_recent_log_lines
    )
except ImportError:
    from backend.bot_logger import (
        bot_logger, log_ok, log_error, log_warn, log_info,
        log_llm, log_db, log_wa, log_security, log_cron,
        get_recent_log_lines
    )

logger = bot_logger

try:
    from menu_manager import menu_manager
except ImportError:
    from backend.menu_manager import menu_manager

try:
    from language_helper import (
        detect_foreign_language,
        build_language_switch_offer,
        is_smart_language_confirmation,
        LANGUAGES_CONFIG
    )
except ImportError:
    from backend.language_helper import (
        detect_foreign_language,
        build_language_switch_offer,
        is_smart_language_confirmation,
        LANGUAGES_CONFIG
    )

SPEED_OK_GIF_URL = "https://media.giphy.com/media/tsX3YMWYzDPjAARfeg/giphy.gif"

# Load environment variables from .env file
load_dotenv()

# =========================================================================================
# FASTAPI APPLICATION & COMPREHENSIVE LOGGING MIDDLEWARE
# =========================================================================================
app = FastAPI(title="Restaurant Food Ordering WhatsApp Bot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def logging_and_timing_middleware(request: Request, call_next):
    """
    Enterprise HTTP Request/Response logger.
    Logs every single incoming request, headers, method, path, client,
    measures millisecond timing, logs successes as [OK], errors as [ERROR],
    and handles HEAD requests with zero-byte body to prevent cron-job.org aborts.
    """
    start_time = time.time()
    req_path = request.url.path
    req_method = request.method
    client_host = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    # Fast-path for keep-alive HEAD requests (returns 0-byte body immediately)
    if req_method == "HEAD":
        log_cron("PING_HEAD", f"HEAD {req_path} from {client_host} ({user_agent[:50]}) -> 200 OK (0 bytes)")
        return Response(content=b"", status_code=200, media_type="text/plain")

    # Log incoming request
    is_cron = any(bot in user_agent.lower() for bot in ["cron-job", "uptimerobot", "pingdom", "statuscake"])
    if is_cron:
        log_cron("PING_INCOMING", f"{req_method} {req_path} from {client_host} (UA: {user_agent[:50]})")
    else:
        log_info("HTTP_REQUEST", f"{req_method} {req_path} from {client_host} | UA: {user_agent[:60]}")

    try:
        response = await call_next(request)
        elapsed_ms = (time.time() - start_time) * 1000

        if response.status_code < 400:
            if is_cron or req_path in ["/", "/ping", "/health", "/keep-alive"]:
                log_cron("PING_SUCCESS", f"Responded 200 OK to {req_method} {req_path} in {elapsed_ms:.1f}ms")
            else:
                log_ok("HTTP_SUCCESS", f"{response.status_code} {req_method} {req_path} completed in {elapsed_ms:.2f}ms")
        else:
            log_error("HTTP_FAIL", f"{response.status_code} {req_method} {req_path} completed in {elapsed_ms:.2f}ms")

        return response
    except Exception as exc:
        elapsed_ms = (time.time() - start_time) * 1000
        log_error("HTTP_EXCEPTION", f"Unhandled error in {req_method} {req_path} after {elapsed_ms:.2f}ms: {exc}", exc=exc)
        return JSONResponse(status_code=500, content={"error": "Internal Server Error", "message": str(exc)})

# ENVIRONMENT VARIABLES
MY_VERIFY_TOKEN = os.getenv("MY_VERIFY_TOKEN", "restaurant_bot_secret")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
WHATSAPP_API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v21.0")
LLM_CALL_TIMEOUT = 25

# ── API Key Pools ────────────────────────────────────────────────────────────────────────
GROQ_KEYS = [k for k in [os.getenv("GROQ_API_KEY_1"), os.getenv("GROQ_API_KEY_2"), os.getenv("GROQ_API_KEY")] if k]
GEMINI_KEYS = [k for k in [os.getenv("GEMINI_API_KEY_1"), os.getenv("GEMINI_API_KEY_2"), os.getenv("GEMINI_API_KEY")] if k]
OPENROUTER_KEYS = [k for k in [os.getenv("OPENROUTER_API_KEY_1"), os.getenv("OPENROUTER_API_KEY_2"), os.getenv("OPENROUTER_API_KEY")] if k]
COHERE_KEYS = [k for k in [os.getenv("COHERE_API_KEY_1"), os.getenv("COHERE_API_KEY")] if k]
KILO_KEYS = [k for k in [os.getenv("KILO_API_KEY_1"), os.getenv("KILO_API_KEY")] if k]

GROQ_API_KEY = GROQ_KEYS[0] if GROQ_KEYS else None
GEMINI_API_KEY = GEMINI_KEYS[0] if GEMINI_KEYS else None
OPENROUTER_API_KEY = OPENROUTER_KEYS[0] if OPENROUTER_KEYS else None

def _make_groq_clients():
    clients = []
    for k in GROQ_KEYS:
        try:
            clients.append(Groq(api_key=k))
        except Exception:
            pass
    return clients

GROQ_CLIENTS = _make_groq_clients()
groq_client = GROQ_CLIENTS[0] if GROQ_CLIENTS else None

PROCESSED_MSG_IDS = {}

# =========================================================================================
# DYNAMIC AI RESTAURANT MENU & SYSTEM PROMPT (DRIVEN BY backend/menu.json)
# =========================================================================================
# Zero hardcoded menu: all items, prices, variants, delivery fee, categories,
# and system prompts are loaded dynamically from backend/menu.json with microsecond RAM caching.
RESTAURANT_NAME = menu_manager.get_restaurant_name()
DELIVERY_FEE = menu_manager.get_delivery_fee()
RESTAURANT_MENU = menu_manager.get_restaurant_menu_dict()
RESTAURANT_SYSTEM_PROMPT = menu_manager.get_system_prompt()
RESTAURANT_SYSTEM_PROMPT_PLACEHOLDER = RESTAURANT_SYSTEM_PROMPT

# =========================================================================================
# RESTAURANT STATE MACHINE DEFINITIONS
# =========================================================================================
class OrderState:
    BROWSING_MENU = "BROWSING_MENU"
    BUILDING_CART = "BUILDING_CART"
    COLLECTING_DETAILS = "COLLECTING_DETAILS"
    ORDER_CONFIRMED = "ORDER_CONFIRMED"

# =========================================================================================
# STANDARDIZED CART SCHEMA & CALCULATOR
# =========================================================================================
DEFAULT_CUSTOMER_CART = {
    "items": [],
    "subtotal": 0,
    "delivery_fee": 0,
    "grand_total": 0
}

def calculate_cart_totals(cart: dict) -> dict:
    """Standardize customer_cart schema and calculate accurate totals."""
    raw_items = cart.get("items", []) if isinstance(cart, dict) else []
    clean_items = []
    subtotal = 0

    for it in raw_items:
        if not isinstance(it, dict):
            continue
        name = str(it.get("name", "")).strip()
        variant = str(it.get("variant", "Regular")).strip()
        try:
            qty = max(1, int(it.get("qty", 1)))
        except (ValueError, TypeError):
            qty = 1
        try:
            unit_price = int(it.get("unit_price", 0))
        except (ValueError, TypeError):
            unit_price = 0

        line_total = qty * unit_price
        subtotal += line_total

        clean_items.append({
            "name": name,
            "variant": variant,
            "qty": qty,
            "unit_price": unit_price,
            "line_total": line_total,
            "notes": str(it.get("notes", "") or "").strip()
        })

    delivery_fee = menu_manager.get_delivery_fee() if clean_items else 0
    grand_total = subtotal + delivery_fee

    return {
        "items": clean_items,
        "subtotal": subtotal,
        "delivery_fee": delivery_fee,
        "grand_total": grand_total
    }

def add_item_to_cart(cart: dict, name: str, variant: str, qty: int, unit_price: int, notes: str = "") -> dict:
    """Add or increment an item in the cart and recalculate totals."""
    cart_data = calculate_cart_totals(cart)
    items = cart_data["items"]

    found = False
    for it in items:
        if it["name"].lower() == name.lower() and it["variant"].lower() == variant.lower():
            it["qty"] += qty
            if notes and notes not in it["notes"]:
                it["notes"] = f"{it['notes']}, {notes}".strip(", ")
            it["line_total"] = it["qty"] * it["unit_price"]
            found = True
            break

    if not found:
        items.append({
            "name": name,
            "variant": variant,
            "qty": qty,
            "unit_price": unit_price,
            "line_total": qty * unit_price,
            "notes": notes
        })

    return calculate_cart_totals({"items": items})

def remove_item_from_cart(cart: dict, name: str, variant: str = None) -> dict:
    """Remove an item from cart by name and optional variant."""
    cart_data = calculate_cart_totals(cart)
    remaining = []
    for it in cart_data["items"]:
        match_name = it["name"].lower() == name.lower()
        match_variant = (variant is None) or (it["variant"].lower() == variant.lower())
        if not (match_name and match_variant):
            remaining.append(it)
    return calculate_cart_totals({"items": remaining})

# =========================================================================================
# SUPABASE DATABASE LAYER & RESILIENT CACHE FALLBACK
# =========================================================================================
TABLE_RESTAURANT_SESSIONS = "restaurant_sessions"
TABLE_ORDERS = "orders"
TABLE_CHAT_HISTORY = "chat_history"

LOCAL_SESSIONS_PATH = os.path.join(os.path.dirname(__file__), "sessions_cache.json")
LOCAL_ORDERS_PATH = os.path.join(os.path.dirname(__file__), "orders_cache.json")
LOCAL_CHAT_PATH = os.path.join(os.path.dirname(__file__), "chat_history_cache.json")

def _read_local_json(path: str, default: dict) -> dict:
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default

def _write_local_json(path: str, data: dict):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"Local cache write warning ({path}): {e}")

def get_supabase_headers():
    return {
        "apikey": SUPABASE_KEY or "",
        "Authorization": f"Bearer {SUPABASE_KEY or ''}",
        "Content-Type": "application/json"
    }

def get_restaurant_session(phone: str, restaurant_id: str = "default_restaurant") -> dict:
    """Retrieve active session from fast local cache or Supabase."""
    clean_phone = phone.strip()
    default_session = {
        "phone_number": clean_phone,
        "restaurant_id": restaurant_id,
        "order_state": OrderState.BROWSING_MENU,
        "current_language": "Roman Urdu",
        "pending_language": None,
        "customer_cart": calculate_cart_totals({}),
        "customer_details": {
            "customer_name": None,
            "delivery_address": None,
            "contact_phone": clean_phone,
            "payment_method": None
        },
        "active_order_id": None,
        "order_status": None,
        "chat_history": [],
        "last_interaction": time.time()
    }

    # 1. Fast Local Persistent Cache (instant response)
    cached_sessions = _read_local_json(LOCAL_SESSIONS_PATH, {})
    if clean_phone in cached_sessions:
        cached = cached_sessions[clean_phone]
        cached["customer_cart"] = calculate_cart_totals(cached.get("customer_cart", {}))
        merged = {**default_session, **cached}
        log_db("SESSION_CACHE_HIT", f"Session retrieved from fast local cache for {clean_phone} (State: {merged.get('order_state')})")
        return merged

    # 2. Check Supabase if not found in local cache
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            url = f"{SUPABASE_URL}/rest/v1/{TABLE_RESTAURANT_SESSIONS}?phone=eq.{clean_phone}&select=*"
            res = requests.get(url, headers=get_supabase_headers(), timeout=3)
            if res.status_code == 200 and res.json():
                row = res.json()[0]
                saved_state = row.get("order_state") or default_session["order_state"]
                saved_cart = calculate_cart_totals(row.get("customer_cart") or {})
                log_ok("SESSION_SUPABASE_HIT", f"Session retrieved from Supabase for {clean_phone}")
                return {
                    **default_session,
                    "order_state": saved_state,
                    "customer_cart": saved_cart
                }
        except Exception as e:
            log_warn("SESSION_SUPABASE_ERR", f"Supabase fetch warning for {clean_phone}: {e}")

    log_db("SESSION_NEW", f"Initialized fresh session for {clean_phone}")
    return default_session

def _sync_supabase_session_async(clean_phone: str, restaurant_id: str, session: dict):
    """Background helper to sync session to Supabase without blocking user."""
    if not (SUPABASE_URL and SUPABASE_KEY):
        return
    headers = get_supabase_headers()
    headers["Prefer"] = "resolution=merge-duplicates"
    payload = {
        "phone": clean_phone,
        "order_state": session.get("order_state", OrderState.BROWSING_MENU),
        "customer_cart": session.get("customer_cart", DEFAULT_CUSTOMER_CART),
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    try:
        url = f"{SUPABASE_URL}/rest/v1/{TABLE_RESTAURANT_SESSIONS}"
        requests.post(url, headers=headers, json=payload, timeout=4)
        log_ok("SUPABASE_SESSION_SYNC", f"Successfully synced session for {clean_phone} to Supabase")
    except Exception as e:
        log_warn("SUPABASE_SESSION_SYNC_ERR", f"Supabase session save failed: {e}")

def save_restaurant_session(phone: str, restaurant_id: str, session: dict):
    """Save customer session data to local cache immediately and sync to Supabase."""
    clean_phone = phone.strip()
    session["last_interaction"] = time.time()
    session["customer_cart"] = calculate_cart_totals(session.get("customer_cart", {}))

    # Always persist locally first so state is never lost
    cached_sessions = _read_local_json(LOCAL_SESSIONS_PATH, {})
    cached_sessions[clean_phone] = session
    _write_local_json(LOCAL_SESSIONS_PATH, cached_sessions)
    log_db("SESSION_CACHE_SAVE", f"Saved session locally for {clean_phone} (State: {session.get('order_state')})")

    # Sync to Supabase in background
    import threading
    t = threading.Thread(target=_sync_supabase_session_async, args=(clean_phone, restaurant_id, session), daemon=True)
    t.start()

def reset_restaurant_session(phone: str, restaurant_id: str = "default_restaurant") -> dict:
    """Wipe customer session data for testing from scratch."""
    clean_phone = phone.strip()
    cached_sessions = _read_local_json(LOCAL_SESSIONS_PATH, {})
    if clean_phone in cached_sessions:
        del cached_sessions[clean_phone]
        _write_local_json(LOCAL_SESSIONS_PATH, cached_sessions)
        log_info("SESSION_RESET_LOCAL", f"Cleared local session for {clean_phone}")

    if SUPABASE_URL and SUPABASE_KEY:
        for field in ["phone", "phone_number"]:
            try:
                url = f"{SUPABASE_URL}/rest/v1/{TABLE_RESTAURANT_SESSIONS}?{field}=eq.{clean_phone}"
                requests.delete(url, headers=get_supabase_headers(), timeout=5)
            except Exception:
                pass
        log_ok("SESSION_RESET_SUPABASE", f"Reset Supabase session for {clean_phone}")

    return get_restaurant_session(clean_phone, restaurant_id)

def save_order(restaurant_id: str, phone: str, order_data: dict) -> dict:
    """Insert a new confirmed food order into orders table and local storage."""
    clean_phone = phone.strip()
    order_id = order_data.get("order_id") or f"ORD-{int(time.time())}"
    order_data["order_id"] = order_id
    order_data["created_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # Cache locally
    all_orders = _read_local_json(LOCAL_ORDERS_PATH, [])
    if isinstance(all_orders, list):
        all_orders.append(order_data)
        _write_local_json(LOCAL_ORDERS_PATH, all_orders)
        log_ok("ORDER_CACHE_SAVED", f"Order {order_id} cached locally for {clean_phone}")

    # Supabase insert
    if SUPABASE_URL and SUPABASE_KEY:
        headers = get_supabase_headers()
        payloads = [
            {
                "order_id": order_id,
                "phone": clean_phone,
                "cart": order_data.get("cart"),
                "total": order_data.get("cart", {}).get("grand_total", 0),
                "status": "PREPARING",
                "customer": order_data.get("customer")
            },
            {
                "restaurant_id": restaurant_id,
                "phone_number": clean_phone,
                "order_data": order_data,
                "created_at": order_data["created_at"]
            }
        ]
        for p in payloads:
            try:
                url = f"{SUPABASE_URL}/rest/v1/{TABLE_ORDERS}"
                res = requests.post(url, headers=headers, json=p, timeout=5)
                if res.status_code in (200, 201):
                    log_ok("ORDER_SUPABASE_SAVED", f"Order {order_id} recorded in Supabase for {clean_phone}")
                    break
            except Exception as e:
                log_warn("ORDER_SUPABASE_ERR", f"Supabase save order attempt failed: {e}")

    return order_data

def save_chat_history(phone: str, restaurant_id: str, role: str, content: str):
    """Save conversation message to chat history table and local cache."""
    clean_phone = phone.strip()
    entry = {
        "phone": clean_phone,
        "restaurant_id": restaurant_id,
        "role": role,
        "content": content,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

    # Cache locally
    all_chat = _read_local_json(LOCAL_CHAT_PATH, [])
    if isinstance(all_chat, list):
        all_chat.append(entry)
        _write_local_json(LOCAL_CHAT_PATH, all_chat[-200:])

    # Supabase insert
    if SUPABASE_URL and SUPABASE_KEY:
        headers = get_supabase_headers()
        payloads = [
            {"phone": clean_phone, "restaurant_id": restaurant_id, "role": role, "content": content},
            {"phone_number": clean_phone, "restaurant_id": restaurant_id, "role": role, "content": content}
        ]
        for p in payloads:
            try:
                url = f"{SUPABASE_URL}/rest/v1/{TABLE_CHAT_HISTORY}"
                res = requests.post(url, headers=headers, json=p, timeout=5)
                if res.status_code in (200, 201):
                    break
            except Exception:
                pass
    log_db("CHAT_HISTORY_RECORDED", f"Logged {role} turn for {clean_phone} ({len(content)} chars)")

def verify_supabase_tables() -> dict:
    """Verify Supabase connection and tables status."""
    results = {}
    if not SUPABASE_URL or not SUPABASE_KEY:
        return {"status": "unconfigured", "message": "SUPABASE_URL or SUPABASE_KEY missing in .env"}

    headers = get_supabase_headers()
    for table in [TABLE_RESTAURANT_SESSIONS, TABLE_ORDERS, TABLE_CHAT_HISTORY]:
        try:
            url = f"{SUPABASE_URL}/rest/v1/{table}?select=*&limit=1"
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                results[table] = "ONLINE (Read OK)"
            else:
                results[table] = f"HTTP {res.status_code}: {res.text[:100]}"
        except Exception as e:
            results[table] = f"Error: {e}"

    return {"status": "connected", "tables": results}

# =========================================================================================
# WHATSAPP UTILITIES
# =========================================================================================
def send_whatsapp_text(restaurant_id: str, phone: str, text: str, token: str):
    """Send text message via WhatsApp Business Cloud API."""
    url = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{restaurant_id}/messages"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"body": text}
    }
    try:
        log_wa("SEND_TEXT_ATTEMPT", f"Sending WhatsApp text to {phone}: '{text[:60]}...'")
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        res.raise_for_status()
        msg_id = res.json().get("messages", [{}])[0].get("id")
        log_ok("WA_TEXT_SENT", f"WhatsApp text delivered to {phone} (msg_id: {msg_id})")
        return msg_id
    except Exception as e:
        log_error("WA_TEXT_FAILED", f"WhatsApp text send failed to {phone}: {e}", exc=e)
        return None

def send_whatsapp_image(restaurant_id: str, phone: str, image_url: str, caption: str, token: str):
    """Send image message with caption via WhatsApp Business Cloud API."""
    url = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{restaurant_id}/messages"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "image",
        "image": {
            "link": image_url,
            "caption": (caption or "")[:1024]
        }
    }
    try:
        log_wa("SEND_IMAGE_ATTEMPT", f"Sending WhatsApp image/GIF to {phone} (url: {image_url})")
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        res.raise_for_status()
        msg_id = res.json().get("messages", [{}])[0].get("id")
        log_ok("WA_IMAGE_SENT", f"WhatsApp image delivered to {phone} (msg_id: {msg_id})")
        return msg_id
    except Exception as e:
        log_error("WA_IMAGE_FAILED", f"WhatsApp image send failed to {phone}: {e}", exc=e)
        return None

def send_whatsapp_buttons(restaurant_id: str, phone: str, text: str, buttons: list, token: str):
    """Send interactive reply buttons via WhatsApp Business Cloud API."""
    url = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{restaurant_id}/messages"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    actions = []
    for btn in buttons:
        if isinstance(btn, dict):
            btn_id = btn["id"]
            title = btn["title"]
        else:
            clean_title = re.sub(r'[^\w\s]', '', str(btn)).strip()
            btn_id = f"btn_{clean_title.lower().replace(' ', '_')}"
            title = str(btn)
        actions.append({"type": "reply", "reply": {"id": btn_id, "title": title[:20]}})

    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": text},
            "action": {"buttons": actions[:3]}
        }
    }
    try:
        log_wa("SEND_BUTTONS_ATTEMPT", f"Sending {len(actions[:3])} buttons to {phone}: {[a['reply']['title'] for a in actions[:3]]}")
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        res.raise_for_status()
        log_ok("WA_BUTTONS_SENT", f"WhatsApp interactive buttons delivered to {phone}")
    except Exception as e:
        log_error("WA_BUTTONS_FAILED", f"WhatsApp buttons send failed to {phone}: {e}", exc=e)

def download_audio_and_transcribe(audio_id: str, token: str) -> str:
    """Download audio voice note from WhatsApp and transcribe with Whisper."""
    url = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{audio_id}"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        log_wa("AUDIO_DOWNLOAD", f"Downloading voice note {audio_id} from Meta...")
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code != 200:
            log_error("AUDIO_DOWNLOAD_FAIL", f"Meta audio lookup returned HTTP {res.status_code}")
            return None
        media_url = res.json().get("url")
        media_res = requests.get(media_url, headers=headers, timeout=15)

        file_path = os.path.join(os.path.dirname(__file__), f"temp_{audio_id}.ogg")
        with open(file_path, "wb") as f:
            f.write(media_res.content)
        log_ok("AUDIO_DOWNLOAD_OK", f"Downloaded {len(media_res.content)} bytes to {file_path}")

        if groq_client:
            log_llm("WHISPER_START", f"Transcribing audio {audio_id} via Whisper-large-v3...")
            t0 = time.time()
            with open(file_path, "rb") as file:
                transcription = groq_client.audio.transcriptions.create(
                    file=(file_path, file.read()),
                    model="whisper-large-v3",
                    prompt="Urdu and English restaurant food order transcription"
                )
            elapsed = time.time() - t0
            try:
                os.remove(file_path)
            except Exception:
                pass
            text_result = transcription.text.strip()
            log_ok("WHISPER_SUCCESS", f"Audio transcribed in {elapsed:.2f}s: '{text_result}'")
            return text_result
    except Exception as e:
        log_error("AUDIO_TRANSCRIPTION_FAILED", f"Voice note transcription failed: {e}", exc=e)
    return None
    return None

# =========================================================================================
# SANITIZATION UTILITIES
# =========================================================================================
URDU_ABUSES = [
    "kutte", "kutta", "kuttay", "kuttwy", "kutty", "suar", "haramkhor", "harami", "gaandu", "gand",
    "ullu", "bewakoof", "gadha", "saala", "haramzada", "kamina", "kameena",
    "chutiya", "bhenchod", "madarchod", "bhosdike", "mc", "bc", "lund",
    "randi", "kutiya", "bhosdi", "benchod", "maderchod", "behen", "chod",
    "bakwaas"
]

def sanitize_and_extract(text: str) -> tuple:
    """Strip abusive phrases from text while preserving order and dish specifications."""
    words = text.split()
    cleaned_words = []
    had_abuses = False
    for w in words:
        w_lower = w.lower().rstrip('.,!?')
        if w_lower in URDU_ABUSES:
            had_abuses = True
        else:
            cleaned_words.append(w)
    cleaned_text = " ".join(cleaned_words).strip()
    return cleaned_text, had_abuses

# =========================================================================================
# LLM ENGINE & FAILOVER INFRASTRUCTURE
# =========================================================================================
def extract_clean_json(raw_text: str) -> dict:
    """Extract clean JSON dictionary from an LLM response string."""
    if not raw_text:
        return {}
    try:
        return json.loads(raw_text)
    except Exception:
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
    return {}

def _trim_messages(messages: list, max_history: int = 10, max_content_len: int = 800) -> list:
    """Trim message payload to prevent context window or payload size errors."""
    if not messages:
        return []
    system_msg = messages[0] if messages[0].get("role") == "system" else None
    rest = messages[1:] if system_msg else messages

    recent = rest[-max_history:]
    trimmed = []
    for m in recent:
        content = m.get("content", "")
        if isinstance(content, str) and len(content) > max_content_len:
            content = content[:max_content_len] + "... [trimmed]"
        trimmed.append({"role": m.get("role", "user"), "content": content})

    return [system_msg] + trimmed if system_msg else trimmed

def chat_completion_fallback(messages: list) -> str:
    """
    Multi-tier LLM failover architecture:
    Tier 1: OpenRouter (fast, reliable gpt-4o-mini)
    Tier 2: Groq (high-speed LLaMA/Qwen)
    Tier 3: Gemini (gemini-2.0-flash / gemini-3.6-flash)
    Logs every LLM call, token usage, latency, and failovers.
    """
    messages = _trim_messages(messages)

    # TIER 1: OpenRouter (Verified working with fast JSON mode)
    if OPENROUTER_KEYS:
        for idx, key in enumerate(OPENROUTER_KEYS, 1):
            for model_name in ["openai/gpt-4o-mini", "meta-llama/llama-3.3-70b-instruct"]:
                t0 = time.time()
                try:
                    log_llm("T1_OPENROUTER_CALL", f"Key{idx} calling {model_name}...")
                    res = requests.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                        json={
                            "model": model_name,
                            "messages": messages,
                            "temperature": 0.3,
                            "response_format": {"type": "json_object"}
                        },
                        timeout=12
                    )
                    elapsed = time.time() - t0
                    if res.status_code == 200:
                        content = res.json()["choices"][0]["message"]["content"]
                        if content:
                            log_ok("T1_OPENROUTER_OK", f"Model {model_name} responded in {elapsed:.2f}s ({len(content)} chars)")
                            return content
                    else:
                        log_warn("T1_OPENROUTER_FAIL", f"HTTP {res.status_code} from {model_name} in {elapsed:.2f}s: {res.text[:120]}")
                except Exception as e:
                    elapsed = time.time() - t0
                    log_warn("T1_OPENROUTER_ERR", f"Key{idx} on {model_name} failed in {elapsed:.2f}s: {e}")

    # TIER 2: Groq
    if GROQ_CLIENTS:
        for idx, client in enumerate(GROQ_CLIENTS, 1):
            for model_name in ["qwen/qwen3.8-27b", "openai/gpt-oss-120b", "openai/gpt-oss-20b"]:
                t0 = time.time()
                try:
                    log_llm("T2_GROQ_CALL", f"Key{idx} calling {model_name}...")
                    completion = client.chat.completions.create(
                        messages=messages,
                        model=model_name,
                        temperature=0.3,
                        response_format={"type": "json_object"},
                        timeout=10
                    )
                    elapsed = time.time() - t0
                    content = completion.choices[0].message.content
                    if content:
                        log_ok("T2_GROQ_OK", f"Model {model_name} responded in {elapsed:.2f}s ({len(content)} chars)")
                        return content
                except Exception as e:
                    elapsed = time.time() - t0
                    log_warn("T2_GROQ_ERR", f"Key{idx} on {model_name} failed in {elapsed:.2f}s: {e}")

    # TIER 3: Gemini
    if GEMINI_KEYS:
        for idx, gem_key in enumerate(GEMINI_KEYS, 1):
            t0 = time.time()
            try:
                log_llm("T3_GEMINI_CALL", f"Key{idx} calling gemini-3.6-flash...")
                res = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/openai/chat/completions?key={gem_key}",
                    json={
                        "model": "gemini-3.6-flash",
                        "messages": messages,
                        "temperature": 0.3,
                        "response_format": {"type": "json_object"}
                    },
                    timeout=12
                )
                elapsed = time.time() - t0
                if res.status_code == 200:
                    content = res.json()["choices"][0]["message"]["content"]
                    if content:
                        log_ok("T3_GEMINI_OK", f"Gemini responded in {elapsed:.2f}s ({len(content)} chars)")
                        return content
                else:
                    log_warn("T3_GEMINI_FAIL", f"HTTP {res.status_code} in {elapsed:.2f}s: {res.text[:120]}")
            except Exception as e:
                elapsed = time.time() - t0
                log_warn("T3_GEMINI_ERR", f"Key{idx} exception in {elapsed:.2f}s: {e}")

    log_error("ALL_LLMS_EXHAUSTED", "All online LLM tiers timed out or failed. Activating deterministic rule-based taker.")
    return ""

# =========================================================================================
# DETERMINISTIC RULE-BASED RESTAURANT INTENT & CART ENGINE
# =========================================================================================
def format_menu_text() -> str:
    """Format official restaurant menu into a WhatsApp-friendly card directly from menu.json."""
    return menu_manager.get_whatsapp_menu_text()

def can_confirm_order(cart: dict, details: dict) -> tuple:
    """
    Strict server-side gatekeeper: Order CANNOT be confirmed unless:
    1. Cart has items (items count > 0)
    2. Delivery address is provided and at least 5 chars
    3. Customer name is provided and at least 2 chars
    4. Payment method is chosen (Cash on Delivery or Online Transfer)
    Returns: (can_confirm: bool, prompt_text: str, buttons: list)
    """
    items = cart.get("items", []) if isinstance(cart, dict) else []
    if not items:
        return False, "Aapka cart abhi bilkul khali hai ustaad! 🛒 Pehle menu mein se kuch garma garam pasand karein:", ["Menu Dekhein 📋", "Crispy Zinger 🍔", "Loaded Fries 🍟"]
    
    addr = str(details.get("delivery_address") or "").strip()
    if len(addr) < 5:
        return False, "📍 Rider ko aapke ghar pohnchane ke liye apna *Mukammal Delivery Address* share karein (House/Flat #, Gali, Area):", []
        
    name = str(details.get("customer_name") or "").strip()
    if len(name) < 2:
        return False, "Rider ki asani ke liye baraye meharbani apna *Pura Naam* bata dein 👤", []
        
    pm = str(details.get("payment_method") or "").strip()
    if not pm:
        return False, "Payment method select karein: Cash on Delivery ya Online Transfer? 💳", ["Cash on Delivery 💵", "Online Transfer 💳"]
        
    return True, "", []

def rule_based_order_taker(session: dict, msg: str, btn_id: str = None) -> dict:
    """
    Deterministic state machine and rule-based order taker.
    Ensures 100% reliable cart building, calculations, and checkout transitions,
    dynamically synchronized with menu.json with funny, charming street-smart Roman Urdu tone.
    """
    msg_lower = msg.lower().strip()
    current_state = session.get("order_state", OrderState.BROWSING_MENU)
    cart = calculate_cart_totals(session.get("customer_cart", {}))
    details = session.get("customer_details", {})
    r_name = menu_manager.get_restaurant_name()

    # Reset trigger
    if msg_lower in ["/reset", "reset", "clear"]:
        phone = session.get("phone_number", "+923001112233")
        new_session = reset_restaurant_session(phone)
        session.clear()
        session.update(new_session)
        return {
            "reply_text": f"🔄 *Session Reset!* Khush amdeed {r_name} mein ustaad! 🍔 Aaj kya khane ka mood ban raha hai?",
            "buttons": ["Menu Dekhein 📋", "Crispy Zinger 🍔", "Biryani 🍗"],
            "order_state": OrderState.BROWSING_MENU,
            "cart": calculate_cart_totals({})
        }

    # Explicit menu trigger
    if btn_id == "btn_view_menu" or any(w in msg_lower for w in ["menu", "list", "kya hai", "items", "kya mil", "kya hai menu"]):
        return {
            "reply_text": format_menu_text(),
            "buttons": ["Crispy Zinger 🍔", "Biryani 🍗", "Loaded Fries 🍟"],
            "order_state": OrderState.BROWSING_MENU,
            "cart": cart
        }

    # Checkout trigger
    if btn_id == "btn_checkout" or any(w in msg_lower for w in ["checkout", "finalize", "bill", "check out"]):
        if not cart["items"]:
            return {
                "reply_text": "Aapka cart abhi bilkul khali hai jani! 🛒 Pehle menu mein se kuch lazeez pasand karein:",
                "buttons": ["Menu Dekhein 📋", "Crispy Zinger 🍔", "Loaded Fries 🍟"],
                "order_state": OrderState.BROWSING_MENU,
                "cart": cart
            }
        return {
            "reply_text": (
                f"🛒 *Aapka Total Cart:* Rs. {cart['grand_total']} (Delivery Rs. {cart['delivery_fee']} shamil hai).\n\n"
                "Rider ko aapke ghar pohnchane ke liye apna *Mukammal Delivery Address* share karein (House/Flat #, Gali, Area) 📍"
            ),
            "buttons": [],
            "order_state": OrderState.COLLECTING_DETAILS,
            "cart": cart
        }

    # Dynamic Food Item Parser directly driven by menu.json
    parsed_items = menu_manager.parse_items_from_text(msg)
    added_items = []
    if parsed_items:
        for pit in parsed_items:
            cart = add_item_to_cart(cart, pit["name"], pit["variant"], pit["qty"], pit["unit_price"], pit["notes"])
            added_items.append(f"{pit['qty']}x {pit['name']} ({pit['variant']})")

    if added_items:
        items_str = ", ".join(added_items)
        reply = (
            f"✅ Wah ustaad! *{items_str}* cart mein dal diya hai! 🛒🤤\n\n"
            f"💰 *Current Total:* Rs. {cart['subtotal']} (+ Rs. {cart['delivery_fee']} delivery = *Rs. {cart['grand_total']}*)\n\n"
            "Aur kuch shamil karna hai jani, ya seedha Checkout karein?"
        )
        return {
            "reply_text": reply,
            "buttons": ["Checkout Karein 🛒", "Loaded Fries 🍟", "Mint Margarita 🥤"],
            "order_state": OrderState.BUILDING_CART,
            "cart": cart
        }

    # Handling COLLECTING_DETAILS state
    if current_state == OrderState.COLLECTING_DETAILS:
        if not details.get("delivery_address"):
            details["delivery_address"] = msg.strip()
            session["customer_details"] = details
            return {
                "reply_text": "📍 Address note ho gaya ustaad! Rider ki asani ke liye apna *Pura Naam* bata dein 👤",
                "buttons": [],
                "order_state": OrderState.COLLECTING_DETAILS,
                "cart": cart
            }
        elif not details.get("customer_name"):
            details["customer_name"] = msg.strip()
            session["customer_details"] = details
            return {
                "reply_text": (
                    f"Shukriya *{details['customer_name']}* bhai! 🤝\n"
                    "Payment method select karein: Cash on Delivery ya Online Transfer?"
                ),
                "buttons": ["Cash on Delivery 💵", "Online Transfer 💳"],
                "order_state": OrderState.COLLECTING_DETAILS,
                "cart": cart
            }
        elif not details.get("payment_method") or any(w in msg_lower for w in ["cash", "cod", "online", "card", "transfer"]):
            pm = "Cash on Delivery" if any(w in msg_lower for w in ["cash", "cod", "delivery"]) else "Online Transfer"
            details["payment_method"] = pm
            session["customer_details"] = details

            item_lines = "\n".join([f"• {it['qty']}x {it['name']} ({it['variant']}) - Rs. {it['line_total']}" for it in cart["items"]])
            summary = (
                f"📋 *Order Summary Tayar Hai Ustaad:*\n"
                f"{item_lines}\n\n"
                f"Subtotal: Rs. {cart['subtotal']}\n"
                f"Delivery Fee: Rs. {cart['delivery_fee']}\n"
                f"Grand Total: *Rs. {cart['grand_total']}*\n\n"
                f"👤 Name: {details['customer_name']}\n"
                f"📍 Address: {details['delivery_address']}\n"
                f"💳 Payment: {details['payment_method']}\n\n"
                "Ustaad kya main yeh order final kitchen ko bhej du? Confirm karein! 👨‍🍳🔥"
            )
            return {
                "reply_text": summary,
                "buttons": ["Haan, Confirm Karein ✅", "Change Order ✏️"],
                "order_state": OrderState.COLLECTING_DETAILS,
                "cart": cart
            }

    # Handling Confirmation (Strict Non-Premature Gatekeeper)
    is_confirm_signal = (
        btn_id in ["btn_confirm", "btn_haan_confirm_karein", "btn_haan,_confirm_karein_"] or
        any(w in msg_lower for w in ["confirm", "order confirm", "haan confirm", "yes confirm", "haan kardo", "done confirm", "haan, confirm"])
    )
    if is_confirm_signal:
        can_confirm, missing_msg, missing_btns = can_confirm_order(cart, details)
        if not can_confirm:
            return {
                "reply_text": missing_msg,
                "buttons": missing_btns,
                "order_state": OrderState.COLLECTING_DETAILS,
                "cart": cart
            }
        
        # All 4 conditions met! Finalize order!
        order_id = f"ORD-{int(time.time())}"
        order_summary = {
            "order_id": order_id,
            "cart": cart,
            "customer": details,
            "status": "PREPARING",
            "timestamp": time.time()
        }
        save_order(
            restaurant_id=session.get("restaurant_id", "default_restaurant"),
            phone=session.get("phone_number", "+923001112233"),
            order_data=order_summary
        )
        reply = (
            f"🎉 *ORDER CONFIRMED! BHOOM!* 🚀🍔\n\n"
            f"Order ID: *{order_id}*\n"
            f"Status: *Kitchen mein aag lag chuki hai aur khana tayar ho raha hai!* 🔥👨‍🍳\n"
            f"Estimated Delivery: *30-40 Minutes* 🛵\n\n"
            f"Bawarchi Bhai kehta hai: *Speed se delivery pohnche gi ustaad!* 😎\n"
            f"*{RESTAURANT_NAME}* ka intekhab karne ka shukriya! Rider nikalte hi aap ko WhatsApp par live update mil jayegi."
        )
        return {
            "reply_text": reply,
            "buttons": ["Track Order 🛵", "Naya Order 🍔"],
            "order_state": OrderState.ORDER_CONFIRMED,
            "cart": cart,
            "media_url": SPEED_OK_GIF_URL
        }

    # General Greeting / Default Inquiry (Personalized for returning customers!)
    saved_name = details.get("customer_name")
    if saved_name:
        greeting_reply = (
            f"Assalam-o-Alaikum *{saved_name}* bhai! 🍔 Wapis dekh kar dil khush hua!\n"
            "Aaj kya khane ka program hai? Wahi Crispy Zinger mangwayein ya koi naya item try karein ge? 🤤"
        )
    else:
        greeting_reply = (
            f"Assalam-o-Alaikum ustaad! 🍔 *{RESTAURANT_NAME}* mein khush amdeed!\n"
            "Humare paas behtareen Crispy Zingers, Chicken Biryani, Loaded Fries aur Chilled Drinks dastiyab hain.\n\n"
            "Aap kya khana pasand karein ge jani?"
        )
    return {
        "reply_text": greeting_reply,
        "buttons": ["Menu Dekhein 📋", "Crispy Zinger 🍔", "Chicken Biryani 🍗"],
        "order_state": OrderState.BROWSING_MENU,
        "cart": cart
    }

# =========================================================================================
# UNIFIED CUSTOMER MESSAGE PROCESSING PIPELINE
# =========================================================================================
def process_customer_message(
    phone: str,
    incoming_message: str,
    btn_id: str = None,
    restaurant_id: str = "default_restaurant"
) -> dict:
    """
    Main entry point for processing customer messages.
    Used by WhatsApp Webhook, Web Chat Endpoint, and Local CLI Tester.
    """
    clean_phone = phone.strip()
    msg_body = (incoming_message or "").strip()
    msg_lower = msg_body.lower().strip()

    log_info("MSG_RECEIVE", f"Incoming message from {clean_phone} (btn_id: {btn_id}): '{msg_body}'")

    # Fast-path for reset
    if msg_lower in ["/reset", "reset", "clear"] or btn_id == "btn_reset":
        log_info("SESSION_RESET", f"Customer {clean_phone} requested session reset")
        session = reset_restaurant_session(clean_phone, restaurant_id)
        reply = f"🔄 *Session Reset!* Khush amdeed {RESTAURANT_NAME} mein ustaad! 🍔 Aaj kya khane ka program hai?"
        buttons = ["Menu Dekhein 📋", "Crispy Zinger 🍔", "Chicken Biryani 🍗"]
        session["chat_history"].append({"role": "assistant", "content": reply})
        save_restaurant_session(clean_phone, restaurant_id, session)
        log_ok("SESSION_RESET_DONE", f"Session wiped clean and reset greeting returned to {clean_phone}")
        return {
            "reply_text": reply,
            "buttons": buttons,
            "order_state": OrderState.BROWSING_MENU,
            "customer_cart": calculate_cart_totals({}),
            "customer_details": session["customer_details"],
            "media_url": None
        }

    # Fetch active session
    session = get_restaurant_session(clean_phone, restaurant_id)
    current_lang = session.get("current_language", "Roman Urdu")
    pending_lang = session.get("pending_language", None)
    chat_hist = session.get("chat_history", [])
    cart = calculate_cart_totals(session.get("customer_cart", {}))
    details = session.get("customer_details", {})

    # 1. Smart Language Switch Confirmation Check ('1' or Switch Button)
    if pending_lang and is_smart_language_confirmation(msg_body, btn_id, session):
        target_conf = LANGUAGES_CONFIG.get(pending_lang, {})
        session["current_language"] = pending_lang
        session["pending_language"] = None
        welcome_text = target_conf.get("locked_welcome", f"Zabardast! Ab hum {pending_lang} mein baat karein ge! 🍔")
        btn_label = "Menu 📋" if pending_lang != "Roman_Urdu" else "Menu Dekhein 📋"
        switch_buttons = [btn_label, "Crispy Zinger 🍔", "Loaded Fries 🍟"]

        log_ok("LANG_SWITCH_LOCKED", f"Customer {clean_phone} locked language to '{pending_lang}'")
        chat_hist.append({"role": "user", "content": msg_body})
        chat_hist.append({"role": "assistant", "content": welcome_text})
        session["chat_history"] = chat_hist[-20:]
        save_restaurant_session(clean_phone, restaurant_id, session)
        save_chat_history(clean_phone, restaurant_id, "user", msg_body)
        save_chat_history(clean_phone, restaurant_id, "assistant", welcome_text)
        return {
            "reply_text": welcome_text,
            "buttons": switch_buttons,
            "order_state": session.get("order_state", OrderState.BROWSING_MENU),
            "customer_cart": cart,
            "customer_details": details,
            "media_url": None,
            "current_language": pending_lang
        }

    # 2. Admin / Free Food / Zero-Payment Hack Blocker (Code Intercept, 0 LLM Tokens)
    admin_hack_patterns = [
        "admin hu", "admin hoon", "mein admin", "main admin", "owner hu", "malik hu", "restaurant ka malik",
        "developer hu", "zero payment", "payment zero", "payment 0", "free order", "free food", "muft khana",
        "muft do", "bina paise", "baghair paise", "free mein", "100% discount", "discount 100", "bypass payment",
        "i am admin", "i am the admin", "i am owner", "make payment zero", "make order free", "free meal"
    ]
    if any(p in msg_lower for p in admin_hack_patterns):
        log_security("ADMIN_HACK_INTERCEPTED", f"Blocked admin/zero-payment bypass attempt from {clean_phone}: '{msg_body}'")
        if current_lang == "English" and not any(w in msg_lower for w in ["hu", "hoon", "mein", "main", "malik", "karo", "do"]):
            witty_reply = (
                "Haha nice try! Even if you are the owner or the ultimate VIP, the kitchen system doesn't cook without payment! 😜\n\n"
                "Here every customer is royalty, and every bite is delicious! What mouth-watering food are we getting for you today? 🍔🤤"
            )
            buttons = ["Menu 📋", "Crispy Zinger 🍔", "Loaded Fries 🍟"]
        else:
            witty_reply = (
                "Haha ustaad, agar aap restaurant ke malik ya dunya ke sab se bare VIP bhi hain na, "
                "tab bhi yeh software payment ke baghair kitchen ko order nahi bhejta! 😜\n\n"
                "Yahan har customer hamare liye VIP hai aur har bite lazeez! "
                "Chalein shabash, seedhe tareeqay se batayein kya khana hai? 🍔🤤"
            )
            buttons = ["Menu Dekhein 📋", "Crispy Zinger 🍔", "Loaded Fries 🍟"]

        chat_hist.append({"role": "user", "content": msg_body})
        chat_hist.append({"role": "assistant", "content": witty_reply})
        session["chat_history"] = chat_hist[-20:]
        save_restaurant_session(clean_phone, restaurant_id, session)
        save_chat_history(clean_phone, restaurant_id, "user", msg_body)
        save_chat_history(clean_phone, restaurant_id, "assistant", witty_reply)
        return {
            "reply_text": witty_reply,
            "buttons": buttons,
            "order_state": session.get("order_state", OrderState.BROWSING_MENU),
            "customer_cart": cart,
            "customer_details": details,
            "media_url": None,
            "current_language": current_lang
        }

    # 3. Abuse / Profanity Sanitization (Preserve Cart & Memory, Deflect with Food Humor)
    cleaned_body, had_abuse = sanitize_and_extract(msg_body)
    if had_abuse:
        log_warn("ABUSE_SANITIZED", f"Sanitized abusive language from {clean_phone}. Preserving cart ({len(cart['items'])} items) and deflecting with food humor.")
        cooling_reply = (
            "Array ustaad itna ghussa? 😅 Lagta hai bhook bohat tez lagi hai aur dimagh ki batti gul ho rahi hai!\n\n"
            "Ghussa thanda karein, ek garam Crispy Zinger 🍔 ya chilled Mint Margarita 🥤 mangwayein, "
            "tabiyat ek dam fresh ho jayegi! Bataiye kya pack karein? 🤤"
        )
        chat_hist.append({"role": "user", "content": msg_body})
        chat_hist.append({"role": "assistant", "content": cooling_reply})
        session["chat_history"] = chat_hist[-20:]
        save_restaurant_session(clean_phone, restaurant_id, session)
        save_chat_history(clean_phone, restaurant_id, "user", msg_body)
        save_chat_history(clean_phone, restaurant_id, "assistant", cooling_reply)
        return {
            "reply_text": cooling_reply,
            "buttons": ["Menu Dekhein 📋", "Crispy Zinger 🍔", "Loaded Fries 🍟"],
            "order_state": session.get("order_state", OrderState.BROWSING_MENU),
            "customer_cart": cart,
            "customer_details": details,
            "media_url": None,
            "current_language": current_lang
        }
    msg_body = cleaned_body

    # 4. Non-Food Off-Topic Fast Interception (Politics, Coding, Math, Homework)
    off_topic_patterns = [
        "who is prime minister", "imran khan", "nawaz sharif", "write python", "write code",
        "solve this math", "do my homework", "who won the match", "write an essay", "write poem",
        "tell me a joke about politics", "crypto", "bitcoin", "weather forecast"
    ]
    if any(p in msg_lower for p in off_topic_patterns):
        log_info("OFF_TOPIC_DEFLECTED", f"Deflected non-food question from {clean_phone}: '{msg_body}'")
        deflect_reply = (
            "Ustaad humara dimagh sirf Crispy Burgers, Chicken Biryani aur Loaded Fries mein chalta hai! 🍔🤤\n\n"
            "Siyasat, coding aur homework chhoro, pehle pait pooja karein! "
            "Bataiye aaj kya lazeez mangwa rahe hain? 🍟🥤"
        )
        chat_hist.append({"role": "user", "content": msg_body})
        chat_hist.append({"role": "assistant", "content": deflect_reply})
        session["chat_history"] = chat_hist[-20:]
        save_restaurant_session(clean_phone, restaurant_id, session)
        save_chat_history(clean_phone, restaurant_id, "user", msg_body)
        save_chat_history(clean_phone, restaurant_id, "assistant", deflect_reply)
        return {
            "reply_text": deflect_reply,
            "buttons": ["Menu Dekhein 📋", "Crispy Zinger 🍔", "Loaded Fries 🍟"],
            "order_state": session.get("order_state", OrderState.BROWSING_MENU),
            "customer_cart": cart,
            "customer_details": details,
            "media_url": None,
            "current_language": current_lang
        }

    # 5. Smart Language Detection for Foreign Language
    detected_foreign = detect_foreign_language(msg_body, current_lang)
    if detected_foreign and detected_foreign != current_lang:
        offer_text, offer_btns = build_language_switch_offer(detected_foreign)
        if offer_text:
            log_info("LANG_OFFER_DISPATCHED", f"Detected foreign language '{detected_foreign}' from {clean_phone}. Dispatched switch offer.")
            session["pending_language"] = detected_foreign
            chat_hist.append({"role": "user", "content": msg_body})
            chat_hist.append({"role": "assistant", "content": offer_text})
            session["chat_history"] = chat_hist[-20:]
            save_restaurant_session(clean_phone, restaurant_id, session)
            save_chat_history(clean_phone, restaurant_id, "user", msg_body)
            save_chat_history(clean_phone, restaurant_id, "assistant", offer_text)
            return {
                "reply_text": offer_text,
                "buttons": offer_btns,
                "order_state": session.get("order_state", OrderState.BROWSING_MENU),
                "customer_cart": cart,
                "customer_details": details,
                "media_url": None,
                "current_language": current_lang
            }

    # Build AI context
    current_context = {
        "order_state": session.get("order_state", OrderState.BROWSING_MENU),
        "customer_cart": cart,
        "customer_details": details,
        "current_language": current_lang
    }

    ai_reply_text = ""
    ai_buttons = []
    next_state = session.get("order_state", OrderState.BROWSING_MENU)

    # 6. Fast path for pure menu view requests (0ms latency, zero token cost)
    is_pure_menu_inquiry = (btn_id == "btn_view_menu") or (
        any(w in msg_lower for w in ["menu", "list dikhao", "kya items", "kya mil", "show menu"])
        and not any(w in msg_lower for w in ["order", "chahiye", "bhejo", "pack", "add", "kardo", "mangwa"])
    )
    if is_pure_menu_inquiry:
        log_ok("MENU_SERVED", f"Served full menu card to {clean_phone} (0 LLM tokens)")
        menu_card = menu_manager.get_whatsapp_menu_text()
        chat_hist.append({"role": "user", "content": msg_body})
        chat_hist.append({"role": "assistant", "content": menu_card})
        session["chat_history"] = chat_hist[-20:]
        session["order_state"] = OrderState.BROWSING_MENU
        save_restaurant_session(clean_phone, restaurant_id, session)
        return {
            "reply_text": menu_card,
            "buttons": ["Crispy Zinger 🍔", "Biryani 🍗", "Loaded Fries 🍟"],
            "order_state": OrderState.BROWSING_MENU,
            "customer_cart": cart,
            "cart": cart,
            "media_url": None
        }

    # 7. Dynamic LLM Call with Language Directive strictly memorizing live menu.json
    live_sys_prompt = menu_manager.get_system_prompt(current_language=current_lang)
    sys_prompt = f"{live_sys_prompt}\nCURRENT CONTEXT: {json.dumps(current_context, ensure_ascii=False)}"
    llm_messages = [{"role": "system", "content": sys_prompt}]
    for h in chat_hist[-6:]:
        llm_messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
    llm_messages.append({"role": "user", "content": msg_body if not btn_id else f"[Button clicked: {btn_id}] {msg_body}"})

    ai_response_str = chat_completion_fallback(llm_messages)
    parsed = extract_clean_json(ai_response_str)

    if parsed and isinstance(parsed, dict) and "reply_text" in parsed:
        ai_reply_text = parsed.get("reply_text", "")
        ai_buttons = parsed.get("buttons", [])[:3]
        next_state = parsed.get("order_state", next_state)

        # Apply cart updates if provided by LLM
        cart_updates = parsed.get("cart_updates", {})
        action = cart_updates.get("action", "none")
        items_to_update = cart_updates.get("items", [])

        if action == "clear":
            cart = calculate_cart_totals({})
            log_info("CART_CLEARED", f"Cart cleared for {clean_phone}")
        elif action in ["add", "update"] and items_to_update:
            for it in items_to_update:
                raw_name = str(it.get("name", "")).strip()
                raw_variant = str(it.get("variant", "Regular")).strip()
                try:
                    qty = max(1, int(it.get("qty", 1)))
                except (ValueError, TypeError):
                    qty = 1
                try:
                    suggested_price = int(it.get("unit_price", 0))
                except (ValueError, TypeError):
                    suggested_price = 0
                notes = str(it.get("notes", "") or "").strip()

                # Dynamic Anti-Hallucination & Live Pricing Guard
                val_name, val_variant, val_price, is_valid = menu_manager.validate_and_price_item(
                    raw_name, raw_variant, suggested_price
                )
                if is_valid:
                    cart = add_item_to_cart(cart, val_name, val_variant, qty, val_price, notes)
                    log_ok("PRICING_GUARD_OK", f"Added verified {qty}x {val_name} ({val_variant}) @ Rs. {val_price} to cart for {clean_phone}")
                else:
                    log_warn("PRICING_GUARD_REJECT", f"Rejected invalid/hallucinated item '{raw_name}' for {clean_phone}")

        # Apply customer details updates
        details_updates = parsed.get("customer_details_updates", {})
        for k in ["customer_name", "delivery_address", "payment_method"]:
            if details_updates.get(k):
                details[k] = details_updates[k]
                log_info("CUSTOMER_DETAIL_UPDATED", f"Updated {k}='{details[k]}' for {clean_phone}")

    # 8. Rule-based Fallback if AI didn't provide complete answer
    media_url = None
    if not ai_reply_text:
        log_info("RULE_BASED_ACTIVATED", f"AI reply empty for {clean_phone}, running rule_based_order_taker")
        rule_res = rule_based_order_taker(session, msg_body, btn_id=btn_id)
        ai_reply_text = rule_res.get("reply_text", "")
        ai_buttons = rule_res.get("buttons", [])
        next_state = rule_res.get("order_state", next_state)
        cart = rule_res.get("cart", cart)
        media_url = rule_res.get("media_url")

    # 9. Strict Non-Premature Order Confirmation Gatekeeper
    all_details_present = (
        len(cart.get("items", [])) > 0 and
        len(str(details.get("delivery_address") or "").strip()) >= 5 and
        len(str(details.get("customer_name") or "").strip()) >= 2 and
        bool(str(details.get("payment_method") or "").strip())
    )

    is_explicit_confirm = (
        btn_id in ["btn_confirm", "btn_haan_confirm_karein", "btn_haan,_confirm_karein_"] or
        any(w in msg_lower for w in ["confirm", "order confirm", "haan confirm", "yes confirm", "haan kardo", "done confirm", "haan, confirm", "final confirm"])
    )

    # If details just got completed but user hasn't explicitly clicked Confirm yet:
    if all_details_present and not is_explicit_confirm:
        next_state = OrderState.COLLECTING_DETAILS
        item_lines = "\n".join([f"• {it['qty']}x {it['name']} ({it['variant']}) - Rs. {it['line_total']}" for it in cart["items"]])
        ai_reply_text = (
            f"📋 *Order Summary Tayar Hai Ustaad:*\n"
            f"{item_lines}\n\n"
            f"Subtotal: Rs. {cart['subtotal']}\n"
            f"Delivery Fee: Rs. {cart['delivery_fee']}\n"
            f"Grand Total: *Rs. {cart['grand_total']}*\n\n"
            f"👤 Name: {details['customer_name']}\n"
            f"📍 Address: {details['delivery_address']}\n"
            f"💳 Payment: {details['payment_method']}\n\n"
            "Ustaad kya main yeh order final kitchen ko bhej du? Confirm karein! 👨‍🍳🔥"
        )
        ai_buttons = ["Haan, Confirm Karein ✅", "Change Order ✏️"]
        media_url = None
        log_info("ORDER_SUMMARY_PRESENTED", f"Presented complete order summary to {clean_phone}, awaiting explicit confirmation")

    elif next_state == OrderState.ORDER_CONFIRMED or is_explicit_confirm:
        can_confirm, missing_msg, missing_btns = can_confirm_order(cart, details)
        if not can_confirm or not is_explicit_confirm:
            # Overrule premature confirmation!
            log_warn("CONFIRMATION_BLOCKED", f"Blocked premature confirmation for {clean_phone}: {missing_msg or 'Needs explicit confirmation'}")
            next_state = OrderState.COLLECTING_DETAILS
            if missing_msg:
                ai_reply_text = missing_msg
                ai_buttons = missing_btns
            media_url = None
        else:
            next_state = OrderState.ORDER_CONFIRMED
            media_url = SPEED_OK_GIF_URL
            if not session.get("active_order_id"):
                order_id = f"ORD-{int(time.time())}"
                session["active_order_id"] = order_id
                session["order_status"] = "PREPARING"
                order_data = {
                    "order_id": order_id,
                    "cart": cart,
                    "customer": details,
                    "status": "PREPARING",
                    "timestamp": time.time()
                }
                save_order(restaurant_id, clean_phone, order_data)
                ai_reply_text = (
                    f"🎉 *ORDER CONFIRMED! BHOOM!* 🚀🍔\n\n"
                    f"Order ID: *{order_id}*\n"
                    f"Status: *Kitchen mein aag lag chuki hai aur burger grill ho raha hai!* 🔥👨‍🍳\n"
                    f"Estimated Delivery: *30-40 Minutes* 🛵\n\n"
                    f"Bawarchi Bhai kehta hai: *Speed se delivery pohnche gi ustaad!* 😎\n"
                    f"*{RESTAURANT_NAME}* ka intekhab karne ka shukriya! Rider nikalte hi aap ko WhatsApp par live update mil jayegi."
                )
                ai_buttons = ["Track Order 🛵", "Naya Order 🍔"]
                log_ok("ORDER_CONFIRMED_FINAL", f"🎉 ORDER CONFIRMED! ID={order_id}, Phone={clean_phone}, Total=Rs. {cart['grand_total']}, Attached Speed GIF")

    # 10. Intelligent 4K Realistic Food Image Engine
    # Only if not already set (e.g., Speed OK GIF for ORDER_CONFIRMED)
    if not media_url and next_state != OrderState.ORDER_CONFIRMED:
        shown_images = session.setdefault("shown_images", [])
        is_explicit = menu_manager.is_explicit_image_request(msg_body)

        # A) Explicit Image Request: User specifically asked to see photo/pic/dikhao
        if is_explicit:
            # 1. Match item in user message
            target_item = menu_manager.find_item_for_query(msg_body)
            # 2. Or match item currently in cart / discussed
            if not target_item and cart.get("items"):
                target_item = menu_manager.find_item_for_query(cart["items"][-1]["name"])
            # 3. Fallback to bestseller
            if not target_item:
                target_item = menu_manager.find_item_for_query("crispy_zinger")

            if target_item and target_item.get("image") and target_item["image"].startswith("http"):
                media_url = target_item["image"]
                item_name = target_item["name"]
                log_ok("IMAGE_EXPLICIT_DISPATCH", f"Dispatched requested 4K image for '{item_name}' to {clean_phone}")
                if not any(w in ai_reply_text.lower() for w in ["tasveer", "photo", "image", "dekhein"]):
                    ai_reply_text = f"Yeh dekhein ustaad! Hamara garma garam *{item_name}* 🤤🔥\n\n" + ai_reply_text

        # B) Proactive Image Dispatch: User shows interest or adds item, send ONCE
        else:
            interested_item = menu_manager.detect_customer_item_interest(msg_body)
            if not interested_item and items_to_update:
                interested_item = menu_manager.find_item_for_query(items_to_update[0].get("name", ""))

            if interested_item:
                item_id = interested_item.get("id")
                # Frequency capping guard: only send proactively ONCE per item
                if item_id and item_id not in shown_images:
                    if interested_item.get("image") and interested_item["image"].startswith("http"):
                        media_url = interested_item["image"]
                        shown_images.append(item_id)
                        log_ok("IMAGE_PROACTIVE_DISPATCH", f"Proactively dispatched 4K image for '{interested_item['name']}' to {clean_phone} (First time interest)")

    # State transition & Update session
    session["order_state"] = next_state
    session["customer_cart"] = cart
    session["customer_details"] = details

    # Update conversation history
    chat_hist.append({"role": "user", "content": msg_body})
    chat_hist.append({"role": "assistant", "content": ai_reply_text})
    session["chat_history"] = chat_hist[-20:]

    # Save to Supabase and cache
    save_chat_history(clean_phone, restaurant_id, "user", msg_body)
    save_chat_history(clean_phone, restaurant_id, "assistant", ai_reply_text)
    save_restaurant_session(clean_phone, restaurant_id, session)

    return {
        "reply_text": ai_reply_text,
        "buttons": ai_buttons,
        "order_state": session["order_state"],
        "customer_cart": session["customer_cart"],
        "customer_details": session["customer_details"],
        "media_url": media_url,
        "current_language": session.get("current_language", "Roman Urdu")
    }

# =========================================================================================
# WEBHOOK DATA PROCESSING
# =========================================================================================
def process_whatsapp_data(data: dict):
    """Asynchronous background worker processing incoming WhatsApp messages."""
    try:
        entries = data.get("entry") or []
        if not entries:
            log_info("WA_EMPTY_ENTRY", "Received webhook with empty 'entry' list (likely ping/status)")
            return

        entry = entries[0]
        changes = entry.get("changes") or []
        if not changes:
            return

        value = changes[0].get("value") or {}
        metadata = value.get("metadata") or {}
        restaurant_id = metadata.get("phone_number_id") or os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
        wa_token = os.getenv("WHATSAPP_ACCESS_TOKEN", "")

        contacts = value.get("contacts") or []
        default_sender = contacts[0].get("wa_id", "") if contacts else ""

        # Status updates (delivered, read, sent, failed)
        statuses = value.get("statuses") or []
        if statuses:
            for s in statuses:
                st = s.get("status", "unknown")
                recip = s.get("recipient_id", "unknown")
                errs = s.get("errors")
                if st == "failed" or errs:
                    log_error("WA_STATUS_FAILED", f"WhatsApp delivery to {recip} FAILED: status={st}, errors={errs}")
                elif st in ("delivered", "sent", "read"):
                    log_ok("WA_STATUS_OK", f"WhatsApp delivery to {recip} -> {st.upper()}")
                else:
                    log_info("WA_STATUS_UPDATE", f"Status for {recip}: {st}")
            return

        messages = value.get("messages") or []
        if not messages:
            log_info("WA_NO_MESSAGES", f"Webhook received without user messages (change field: {changes[0].get('field')})")
            return

        for msg in messages:
            msg_id = msg.get("id")
            if not msg_id or msg_id in PROCESSED_MSG_IDS:
                continue
            PROCESSED_MSG_IDS[msg_id] = time.time()

            # Evict old message IDs after 1 hour
            now = time.time()
            for old_id, ts in list(PROCESSED_MSG_IDS.items()):
                if now - ts > 3600:
                    PROCESSED_MSG_IDS.pop(old_id, None)

            # Robust sender identification: prioritize msg['from'], fallback to contacts['wa_id']
            from_number = msg.get("from") or default_sender
            if not from_number:
                log_error("WA_NO_SENDER", f"No sender phone found for message {msg_id}")
                continue

            msg_type = msg.get("type")
            msg_body = ""
            btn_id = None

            if msg_type == "text":
                msg_body = msg.get("text", {}).get("body", "").strip()
            elif msg_type == "interactive":
                interactive = msg.get("interactive", {})
                if interactive.get("type") == "button_reply":
                    btn_id = interactive.get("button_reply", {}).get("id")
                    msg_body = interactive.get("button_reply", {}).get("title", "")
            elif msg_type == "audio":
                audio_id = msg.get("audio", {}).get("id")
                if audio_id:
                    transcription = download_audio_and_transcribe(audio_id, wa_token)
                    if transcription:
                        msg_body = transcription.strip()

            if not msg_body and not btn_id:
                log_warn("WA_EMPTY_BODY", f"Ignoring non-text/unhandled payload from {from_number} (type: {msg_type})")
                continue

            log_wa("WA_MSG_INCOMING", f"Processing {msg_type} from {from_number} (msg_id: {msg_id}) | Content: '{msg_body[:60]}'")
            # Process through unified restaurant ordering engine
            result = process_customer_message(from_number, msg_body, btn_id=btn_id, restaurant_id=restaurant_id)
            reply_text = result.get("reply_text", "")
            buttons = result.get("buttons", [])
            media_url = result.get("media_url")

            # Send WhatsApp response
            if media_url:
                send_whatsapp_image(restaurant_id, from_number, media_url, reply_text, wa_token)
                if buttons:
                    send_whatsapp_buttons(restaurant_id, from_number, "Mazay karein! Agla step chunein:", buttons, wa_token)
                log_ok("WA_DELIVERED", f"Dispatched media + buttons to {from_number}")
            elif buttons:
                send_whatsapp_buttons(restaurant_id, from_number, reply_text, buttons, wa_token)
                log_ok("WA_DELIVERED", f"Dispatched interactive buttons to {from_number}")
            else:
                send_whatsapp_text(restaurant_id, from_number, reply_text, wa_token)
                log_ok("WA_DELIVERED", f"Dispatched text response to {from_number}")

    except Exception as e:
        log_error("WA_PROCESS_EXCEPTION", f"Error in background WhatsApp processor: {e}", exc=e)

# =========================================================================================
# WEBHOOK, KEEP-ALIVE & API ENDPOINTS
# =========================================================================================
@app.api_route('/', methods=['GET', 'HEAD'])
def root(request: Request):
    """
    Keep-alive endpoint for cron-job.org and uptime monitors.
    Returns 200 OK with minimal body ('OK' = 2 bytes) or 0-bytes on HEAD,
    completely preventing cron-job.org 'Output too large' errors.
    """
    if request.method == "HEAD":
        return Response(content=b"", status_code=200, media_type="text/plain")
    return PlainTextResponse(content="OK", status_code=200)

@app.api_route('/ping', methods=['GET', 'HEAD'])
def ping_endpoint(request: Request):
    """Dedicated 2-byte ping endpoint for external cron jobs."""
    if request.method == "HEAD":
        return Response(content=b"", status_code=200, media_type="text/plain")
    return PlainTextResponse(content="OK", status_code=200)

@app.api_route('/keep-alive', methods=['GET', 'HEAD'])
def keep_alive_endpoint(request: Request):
    """Keep-alive ping endpoint to keep Render free tier awake."""
    if request.method == "HEAD":
        return Response(content=b"", status_code=200, media_type="text/plain")
    return PlainTextResponse(content="OK", status_code=200)

@app.api_route('/health', methods=['GET', 'HEAD'])
def health(request: Request):
    """Standard health check endpoint."""
    if request.method == "HEAD":
        return Response(content=b"", status_code=200, media_type="text/plain")
    return JSONResponse(content={
        "status": "healthy",
        "service": "restaurant-bot",
        "restaurant": RESTAURANT_NAME,
        "timestamp": time.time()
    })

@app.get('/logs')
def view_system_logs(limit: int = 150):
    """
    Live web log viewer.
    Allows viewing real-time system logs directly in any web browser or via curl.
    """
    lines = get_recent_log_lines(limit)
    return PlainTextResponse(content="\n".join(lines), status_code=200)

@app.get('/supabase/status')
def supabase_status_endpoint():
    """Diagnostic endpoint to inspect Supabase connectivity and tables."""
    return JSONResponse(content=verify_supabase_tables())

@app.get('/meta/status')
def meta_status_endpoint():
    """Diagnostic endpoint to inspect WhatsApp API Configuration & Credentials."""
    wa_token = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    phone_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    verify_token = MY_VERIFY_TOKEN

    info = {
        "phone_number_id_configured": bool(phone_id),
        "phone_number_id": phone_id,
        "access_token_configured": bool(wa_token),
        "access_token_preview": f"{wa_token[:8]}***{wa_token[-6:]}" if len(wa_token) >= 14 else "missing",
        "verify_tokens_accepted": [t for t in [verify_token, os.getenv("WHATSAPP_VERIFY_TOKEN"), "zaiqa_bot_secret_2026", "restaurant_bot_secret", "ALAAUDIN_SECRET_TOKEN"] if t],
        "meta_graph_api_status": "untested"
    }

    if wa_token and phone_id:
        try:
            url = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{phone_id}"
            headers = {"Authorization": f"Bearer {wa_token}"}
            res = requests.get(url, headers=headers, timeout=8)
            if res.status_code == 200:
                data = res.json()
                info["meta_graph_api_status"] = "CONNECTED"
                info["display_phone_number"] = data.get("display_phone_number")
                info["verified_name"] = data.get("verified_name")
                info["quality_rating"] = data.get("quality_rating")
            else:
                info["meta_graph_api_status"] = f"ERROR_{res.status_code}"
                info["meta_error"] = res.json()
        except Exception as e:
            info["meta_graph_api_status"] = "EXCEPTION"
            info["error_details"] = str(e)

    return JSONResponse(content=info)

@app.get('/meta/send-test')
def meta_send_test_endpoint(to: str):
    """
    Diagnostic tool: Attempt to send a WhatsApp message to a specific number
    and return the exact error/success response from Meta Graph API.
    """
    clean_to = re.sub(r'[^0-9]', '', to)
    wa_token = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    phone_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")

    if not wa_token or not phone_id:
        return JSONResponse(status_code=400, content={"error": "WHATSAPP_ACCESS_TOKEN or WHATSAPP_PHONE_NUMBER_ID missing on server"})

    url = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{phone_id}/messages"
    headers = {"Authorization": f"Bearer {wa_token}", "Content-Type": "application/json"}

    # Attempt: Template message (hello_world) - required for sandbox opt-in
    template_payload = {
        "messaging_product": "whatsapp",
        "to": clean_to,
        "type": "template",
        "template": {
            "name": "hello_world",
            "language": {"code": "en_US"}
        }
    }

    try:
        res = requests.post(url, headers=headers, json=template_payload, timeout=10)
        res_data = res.json()
        log_wa("META_TEST_SEND", f"Sent test template to {clean_to} -> HTTP {res.status_code}: {res.text[:150]}")
        return JSONResponse(status_code=res.status_code, content={
            "http_status": res.status_code,
            "target_phone": clean_to,
            "phone_number_id": phone_id,
            "meta_response": res_data,
            "action_taken": "Sent 'hello_world' template message to initiate 24h customer window"
        })
    except Exception as e:
        log_error("META_TEST_SEND_ERR", f"Failed to send test template to {clean_to}: {e}", exc=e)
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get('/webhook')
def verify_webhook(request: Request):
    """WhatsApp Cloud API Webhook Verification."""
    verify_token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    valid_tokens = {
        MY_VERIFY_TOKEN,
        os.getenv("WHATSAPP_VERIFY_TOKEN"),
        "zaiqa_bot_secret_2026",
        "restaurant_bot_secret",
        "ALAAUDIN_SECRET_TOKEN"
    }
    valid_tokens = {t.strip() for t in valid_tokens if t and t.strip()}
    if verify_token in valid_tokens:
        log_ok("WA_WEBHOOK_VERIFY", f"Webhook verification succeeded for token '{verify_token}', challenge={challenge}")
        return PlainTextResponse(content=str(challenge))
    log_error("WA_WEBHOOK_VERIFY", f"Webhook verification failed with token '{verify_token}' (expected one of {list(valid_tokens)})")
    return PlainTextResponse(content="Verification failed", status_code=403)

@app.post('/webhook')
async def receive_webhook(request: Request, bg_tasks: BackgroundTasks):
    """WhatsApp Cloud API Incoming Event Listener."""
    data = await request.json()
    log_wa("WA_PAYLOAD_RECEIVED", f"Incoming WhatsApp webhook payload: {json.dumps(data)[:200]}...")
    bg_tasks.add_task(process_whatsapp_data, data)
    return PlainTextResponse(content="OK")

@app.get('/menu')
def get_menu_endpoint():
    """Returns dynamic restaurant menu, categories, and settings from menu.json."""
    return JSONResponse(content=menu_manager.get_api_menu_payload())

@app.get('/session')
def get_session_endpoint(phone: str = "+923001112233", restaurant_id: str = "default_restaurant"):
    """Get active session details including cart and state."""
    session = get_restaurant_session(phone, restaurant_id)
    return JSONResponse(content=session)

@app.post('/chat')
async def web_chat_endpoint(request: Request):
    """REST API endpoint for web/mobile chat UI and CLI testing."""
    body = await request.json()
    user_msg = body.get("message", "")
    customer_id = body.get("phone") or body.get("email") or "+923001112233"
    restaurant_id = body.get("restaurant_id") or body.get("client_id") or "default_restaurant"
    btn_id = body.get("btn_id")

    log_info("CHAT_ENDPOINT", f"Received message from {customer_id}: '{user_msg}' (btn_id: {btn_id})")
    result = process_customer_message(customer_id, user_msg, btn_id=btn_id, restaurant_id=restaurant_id)
    if "response" not in result and "reply_text" in result:
        result["response"] = result["reply_text"]
    if "cart" not in result and "customer_cart" in result:
        result["cart"] = result["customer_cart"]
    log_ok("CHAT_ENDPOINT_RESPONSE", f"Replied to {customer_id} with state={result.get('order_state')}")
    return JSONResponse(content=result)

@app.post('/reset')
async def reset_session_endpoint(request: Request):
    """Reset customer session for clean testing."""
    body = await request.json()
    phone = body.get("phone", "+923001112233")
    restaurant_id = body.get("restaurant_id", "default_restaurant")
    log_info("RESET_ENDPOINT", f"Resetting session for {phone}")
    session = reset_restaurant_session(phone, restaurant_id)
    log_ok("RESET_ENDPOINT", f"Session reset complete for {phone}")
    return JSONResponse(content={"status": "session_reset", "session": session})

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

