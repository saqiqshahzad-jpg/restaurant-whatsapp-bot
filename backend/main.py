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

from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
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
    from menu_manager import menu_manager
except ImportError:
    from backend.menu_manager import menu_manager

# Load environment variables from .env file
load_dotenv()

# =========================================================================================
# CONFIGURATION & LOGGING
# =========================================================================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger("RESTAURANT_ORDER_BOT")

app = FastAPI(title="Restaurant Food Ordering WhatsApp Bot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        return {**default_session, **cached}

    # 2. Check Supabase if not found in local cache
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            url = f"{SUPABASE_URL}/rest/v1/{TABLE_RESTAURANT_SESSIONS}?phone=eq.{clean_phone}&select=*"
            res = requests.get(url, headers=get_supabase_headers(), timeout=3)
            if res.status_code == 200 and res.json():
                row = res.json()[0]
                saved_state = row.get("order_state") or default_session["order_state"]
                saved_cart = calculate_cart_totals(row.get("customer_cart") or {})
                return {
                    **default_session,
                    "order_state": saved_state,
                    "customer_cart": saved_cart
                }
        except Exception as e:
            logger.debug(f"Supabase fetch note: {e}")

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
    except Exception as e:
        logger.debug(f"Supabase session save failed: {e}")

def save_restaurant_session(phone: str, restaurant_id: str, session: dict):
    """Save customer session data to local cache immediately and sync to Supabase."""
    clean_phone = phone.strip()
    session["last_interaction"] = time.time()
    session["customer_cart"] = calculate_cart_totals(session.get("customer_cart", {}))

    # Always persist locally first so state is never lost
    cached_sessions = _read_local_json(LOCAL_SESSIONS_PATH, {})
    cached_sessions[clean_phone] = session
    _write_local_json(LOCAL_SESSIONS_PATH, cached_sessions)

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

    if SUPABASE_URL and SUPABASE_KEY:
        for field in ["phone", "phone_number"]:
            try:
                url = f"{SUPABASE_URL}/rest/v1/{TABLE_RESTAURANT_SESSIONS}?{field}=eq.{clean_phone}"
                requests.delete(url, headers=get_supabase_headers(), timeout=5)
            except Exception:
                pass

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
                    break
            except Exception as e:
                logger.debug(f"Supabase save order attempt failed: {e}")

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
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        res.raise_for_status()
        return res.json().get("messages", [{}])[0].get("id")
    except Exception as e:
        logger.error(f"WhatsApp text send failed: {e}")
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
            "caption": caption
        }
    }
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        res.raise_for_status()
        return res.json().get("messages", [{}])[0].get("id")
    except Exception as e:
        logger.error(f"WhatsApp image send failed: {e}")
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
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        res.raise_for_status()
    except Exception as e:
        logger.error(f"WhatsApp buttons send failed: {e}")

def download_audio_and_transcribe(audio_id: str, token: str) -> str:
    """Download audio voice note from WhatsApp and transcribe with Whisper."""
    url = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{audio_id}"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code != 200:
            return None
        media_url = res.json().get("url")
        media_res = requests.get(media_url, headers=headers, timeout=15)

        file_path = os.path.join(os.path.dirname(__file__), f"temp_{audio_id}.ogg")
        with open(file_path, "wb") as f:
            f.write(media_res.content)

        if groq_client:
            with open(file_path, "rb") as file:
                transcription = groq_client.audio.transcriptions.create(
                    file=(file_path, file.read()),
                    model="whisper-large-v3",
                    prompt="Urdu and English restaurant food order transcription"
                )
            try:
                os.remove(file_path)
            except Exception:
                pass
            return transcription.text
    except Exception as e:
        logger.error(f"Audio transcription failed: {e}")
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
    Tier 3: Gemini (gemini-2.0-flash)
    Tier 4: OpenAI direct
    Tier 5: Cohere / Kilo
    """
    messages = _trim_messages(messages)

    # TIER 1: OpenRouter (Verified working with fast JSON mode)
    if OPENROUTER_KEYS:
        for idx, key in enumerate(OPENROUTER_KEYS, 1):
            for model_name in ["openai/gpt-4o-mini", "meta-llama/llama-3.3-70b-instruct"]:
                try:
                    logger.info(f"🔄 [T1-OpenRouter] Key{idx} -> {model_name}")
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
                    if res.status_code == 200:
                        content = res.json()["choices"][0]["message"]["content"]
                        if content:
                            return content
                except Exception as e:
                    logger.warning(f"⚠️ [T1-OpenRouter] Key{idx} exception: {e}")

    # TIER 2: Groq
    if GROQ_CLIENTS:
        for idx, client in enumerate(GROQ_CLIENTS, 1):
            for model_name in ["qwen/qwen3.8-27b", "openai/gpt-oss-120b", "openai/gpt-oss-20b"]:
                try:
                    logger.info(f"🔄 [T2-Groq] Key{idx} -> {model_name}")
                    completion = client.chat.completions.create(
                        messages=messages,
                        model=model_name,
                        temperature=0.3,
                        response_format={"type": "json_object"},
                        timeout=10
                    )
                    content = completion.choices[0].message.content
                    if content:
                        return content
                except Exception as e:
                    logger.warning(f"⚠️ [T2-Groq] Key{idx} on {model_name}: {e}")

    # TIER 3: Gemini
    if GEMINI_KEYS:
        for idx, gem_key in enumerate(GEMINI_KEYS, 1):
            try:
                logger.info(f"🔄 [T3-Gemini] Key{idx} -> gemini-3.6-flash")
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
                if res.status_code == 200:
                    return res.json()["choices"][0]["message"]["content"]
            except Exception as e:
                logger.warning(f"⚠️ [T3-Gemini] Key{idx} exception: {e}")

    logger.warning("All online LLMs timed out or unavailable. Activating Rule-Based Engine.")
    return ""

# =========================================================================================
# DETERMINISTIC RULE-BASED RESTAURANT INTENT & CART ENGINE
# =========================================================================================
def format_menu_text() -> str:
    """Format official restaurant menu into a WhatsApp-friendly card directly from menu.json."""
    return menu_manager.get_whatsapp_menu_text()

def rule_based_order_taker(session: dict, msg: str, btn_id: str = None) -> dict:
    """
    Deterministic state machine and rule-based order taker.
    Ensures 100% reliable cart building, calculations, and checkout transitions,
    dynamically synchronized with menu.json.
    """
    msg_lower = msg.lower().strip()
    current_state = session.get("order_state", OrderState.BROWSING_MENU)
    cart = calculate_cart_totals(session.get("customer_cart", {}))
    details = session.get("customer_details", {})

    # Reset trigger
    if msg_lower in ["/reset", "reset", "clear"]:
        phone = session.get("phone_number", "+923001112233")
        new_session = reset_restaurant_session(phone)
        session.clear()
        session.update(new_session)
        r_name = menu_manager.get_restaurant_name()
        return {
            "reply_text": f"🔄 *Session Reset!* Khush amdeed {r_name} mein! 🍔 Aap kya order karna chahein ge?",
            "buttons": ["Menu Dekhein 📋", "Crispy Zinger 🍔", "Biryani 🍗"],
            "order_state": OrderState.BROWSING_MENU,
            "cart": calculate_cart_totals({})
        }

    # Explicit menu trigger
    if btn_id == "btn_view_menu" or any(w in msg_lower for w in ["menu", "list", "kya hai", "items", "kya mil"]):
        return {
            "reply_text": format_menu_text(),
            "buttons": ["Crispy Zinger 🍔", "Biryani 🍗", "Loaded Fries 🍟"],
            "order_state": OrderState.BROWSING_MENU,
            "cart": cart
        }

    # Checkout trigger
    if btn_id == "btn_checkout" or any(w in msg_lower for w in ["checkout", "finalize", "bill", "check out", "order confirm"]):
        if not cart["items"]:
            return {
                "reply_text": "Aapka cart abhi khali hai! 🛒 Pehle menu mein se kuch pasand karein:",
                "buttons": ["Menu Dekhein 📋", "Crispy Zinger 🍔", "Loaded Fries 🍟"],
                "order_state": OrderState.BROWSING_MENU,
                "cart": cart
            }
        return {
            "reply_text": (
                f"🛒 *Aapka Cart:* Rs. {cart['grand_total']} (Delivery Rs. {cart['delivery_fee']} shamil hai).\n\n"
                "Order deliver karne ke liye baraye meharbani apna *Mukammal Delivery Address* share karein (House/Flat #, Street, Area) 📍"
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
            f"✅ Zabardast! *{items_str}* aapke cart mein add kar diya gaya hai! 🛒\n\n"
            f"💰 *Current Total:* Rs. {cart['subtotal']} (+ Rs. {cart['delivery_fee']} delivery = *Rs. {cart['grand_total']}*)\n\n"
            "Kya aap mazeed kuch shamil karna chahein ge ya Checkout karein?"
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
                "reply_text": "📍 Address note ho gaya! Baraye meharbani rider ki asani ke liye apna *Pura Naam* bata dein.",
                "buttons": [],
                "order_state": OrderState.COLLECTING_DETAILS,
                "cart": cart
            }
        elif not details.get("customer_name"):
            details["customer_name"] = msg.strip()
            session["customer_details"] = details
            return {
                "reply_text": (
                    f"Shukriya *{details['customer_name']}* sahib! 🤝\n"
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
                f"📋 *Order Summary:*\n"
                f"{item_lines}\n\n"
                f"Subtotal: Rs. {cart['subtotal']}\n"
                f"Delivery Fee: Rs. {cart['delivery_fee']}\n"
                f"Grand Total: *Rs. {cart['grand_total']}*\n\n"
                f"👤 Name: {details['customer_name']}\n"
                f"📍 Address: {details['delivery_address']}\n"
                f"💳 Payment: {details['payment_method']}\n\n"
                "Kya main yeh order confirm kar dun?"
            )
            return {
                "reply_text": summary,
                "buttons": ["Haan, Confirm Karein ✅", "Change Order ✏️"],
                "order_state": OrderState.COLLECTING_DETAILS,
                "cart": cart
            }

    # Handling Confirmation
    if any(w in msg_lower for w in ["confirm", "haan", "yes", "theek hai", "ok", "kardo", "done"]):
        if cart["items"]:
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
                f"🎉 *Order Confirm Ho Gaya!*\n\n"
                f"Order ID: *{order_id}*\n"
                f"Status: *Kitchen mein tayari shuru hai* 👨‍🍳\n"
                f"Estimated Delivery: *30-40 Minutes* 🛵\n\n"
                f"*{RESTAURANT_NAME}* ka intekhab karne ka shukriya! Aapka rider jald pohnch raha hai."
            )
            return {
                "reply_text": reply,
                "buttons": ["Track Order 🛵", "Naya Order 🍔"],
                "order_state": OrderState.ORDER_CONFIRMED,
                "cart": cart
            }

    # General Greeting / Default Inquiry
    greeting_reply = (
        f"Assalam-o-Alaikum! 🍔 *{RESTAURANT_NAME}* mein khush amdeed!\n"
        "Humare paas behtareen Crispy Zingers, Chicken Biryani, Loaded Fries aur Drinks dastiyab hain.\n\n"
        "Aap kya khana pasand karein ge?"
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

    # Fast-path for reset
    if msg_body.lower() == "/reset" or btn_id == "btn_reset":
        session = reset_restaurant_session(clean_phone, restaurant_id)
        reply = f"🔄 *Session Reset!* Khush amdeed {RESTAURANT_NAME} mein! 🍔 Aap kya order karna chahein ge?"
        buttons = ["Menu Dekhein 📋", "Crispy Zinger 🍔", "Chicken Biryani 🍗"]
        session["chat_history"].append({"role": "assistant", "content": reply})
        save_restaurant_session(clean_phone, restaurant_id, session)
        return {
            "reply_text": reply,
            "buttons": buttons,
            "order_state": OrderState.BROWSING_MENU,
            "customer_cart": calculate_cart_totals({}),
            "customer_details": session["customer_details"]
        }

    # Sanitize profanity
    cleaned_body, had_abuse = sanitize_and_extract(msg_body)
    if had_abuse:
        return {
            "reply_text": "Baraye meharbani munasib alfaz ka istemal karein. Hum ek restaurant food ordering service hain 🍔.",
            "buttons": ["Menu Dekhein 📋"],
            "order_state": OrderState.BROWSING_MENU,
            "customer_cart": calculate_cart_totals({}),
            "customer_details": {}
        }
    msg_body = cleaned_body

    # Fetch active session
    session = get_restaurant_session(clean_phone, restaurant_id)
    chat_hist = session.get("chat_history", [])
    cart = calculate_cart_totals(session.get("customer_cart", {}))
    details = session.get("customer_details", {})

    # Build AI context
    current_context = {
        "order_state": session.get("order_state", OrderState.BROWSING_MENU),
        "customer_cart": cart,
        "customer_details": details
    }

    ai_reply_text = ""
    ai_buttons = []
    next_state = session.get("order_state", OrderState.BROWSING_MENU)

    # 1. Fast path for pure menu view requests (0ms latency, zero token cost)
    msg_lower = msg_body.lower().strip()
    is_pure_menu_inquiry = (btn_id == "btn_view_menu") or (
        any(w in msg_lower for w in ["menu", "list dikhao", "kya items", "kya mil", "show menu"])
        and not any(w in msg_lower for w in ["order", "chahiye", "bhejo", "pack", "add", "kardo", "mangwa"])
    )
    if is_pure_menu_inquiry:
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
            "cart": cart
        }

    # 2. Try LLM Call (Dynamic System Prompt strictly memorizing live menu.json)
    live_sys_prompt = menu_manager.get_system_prompt()
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
                else:
                    logger.warning(f"⚠️ [Pricing Guard] Rejected invalid/hallucinated item: '{raw_name}'")

        # Apply customer details updates
        details_updates = parsed.get("customer_details_updates", {})
        for k in ["customer_name", "delivery_address", "payment_method"]:
            if details_updates.get(k):
                details[k] = details_updates[k]

    # 2. Rule-based Fallback if AI didn't provide complete answer
    if not ai_reply_text:
        rule_res = rule_based_order_taker(session, msg_body, btn_id=btn_id)
        ai_reply_text = rule_res.get("reply_text", "")
        ai_buttons = rule_res.get("buttons", [])
        next_state = rule_res.get("order_state", next_state)
        cart = rule_res.get("cart", cart)

    # State transition & Order Confirmation Trigger
    session["order_state"] = next_state
    session["customer_cart"] = cart
    session["customer_details"] = details

    if next_state == OrderState.ORDER_CONFIRMED and not session.get("active_order_id"):
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
        "customer_details": session["customer_details"]
    }

# =========================================================================================
# WEBHOOK DATA PROCESSING
# =========================================================================================
def process_whatsapp_data(data: dict):
    """Asynchronous background worker processing incoming WhatsApp messages."""
    try:
        entry = data.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        metadata = value.get("metadata", {})
        restaurant_id = metadata.get("phone_number_id", "")
        wa_token = os.getenv("WHATSAPP_ACCESS_TOKEN", "")

        contacts = value.get("contacts", [{}])
        from_number = contacts[0].get("wa_id", "") if contacts else ""

        messages = value.get("messages", [])
        if not messages:
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
                continue

            # Process through unified restaurant ordering engine
            result = process_customer_message(from_number, msg_body, btn_id=btn_id, restaurant_id=restaurant_id)
            reply_text = result.get("reply_text", "")
            buttons = result.get("buttons", [])

            # Send WhatsApp response
            if buttons:
                send_whatsapp_buttons(restaurant_id, from_number, reply_text, buttons, wa_token)
            else:
                send_whatsapp_text(restaurant_id, from_number, reply_text, wa_token)

    except Exception as e:
        logger.error(f"Error processing WhatsApp message: {e}", exc_info=True)

# =========================================================================================
# WEBHOOK & API ENDPOINTS
# =========================================================================================
@app.get('/')
def root():
    return PlainTextResponse(content=f"{RESTAURANT_NAME} WhatsApp Bot is online!")

@app.get('/health')
def health():
    return JSONResponse(content={
        "status": "healthy",
        "service": "restaurant-bot",
        "restaurant": RESTAURANT_NAME,
        "timestamp": time.time()
    })

@app.get('/supabase/status')
def supabase_status_endpoint():
    """Diagnostic endpoint to inspect Supabase connectivity and tables."""
    return JSONResponse(content=verify_supabase_tables())

@app.get('/webhook')
def verify_webhook(request: Request):
    """WhatsApp Cloud API Webhook Verification."""
    verify_token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    if verify_token == MY_VERIFY_TOKEN:
        return PlainTextResponse(content=str(challenge))
    return PlainTextResponse(content="Verification failed", status_code=403)

@app.post('/webhook')
async def receive_webhook(request: Request, bg_tasks: BackgroundTasks):
    """WhatsApp Cloud API Incoming Event Listener."""
    data = await request.json()
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

    result = process_customer_message(customer_id, user_msg, btn_id=btn_id, restaurant_id=restaurant_id)
    if "response" not in result and "reply_text" in result:
        result["response"] = result["reply_text"]
    if "cart" not in result and "customer_cart" in result:
        result["cart"] = result["customer_cart"]
    return JSONResponse(content=result)

@app.post('/reset')
async def reset_session_endpoint(request: Request):
    """Reset customer session for clean testing."""
    body = await request.json()
    phone = body.get("phone", "+923001112233")
    restaurant_id = body.get("restaurant_id", "default_restaurant")
    session = reset_restaurant_session(phone, restaurant_id)
    return JSONResponse(content={"status": "session_reset", "session": session})

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

