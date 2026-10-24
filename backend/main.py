import os
import sys
import time
import json
import re
import logging
import requests
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
from openai import OpenAI
from dotenv import load_dotenv

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
WHATSAPP_API_VERSION = "v25.0"
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
# AI SYSTEM PROMPT PLACEHOLDER
# =========================================================================================
RESTAURANT_SYSTEM_PROMPT_PLACEHOLDER = "RESTAURANT_SYSTEM_PROMPT_PLACEHOLDER"

# =========================================================================================
# RESTAURANT STATE MACHINE DEFINITIONS
# =========================================================================================
class OrderState:
    BROWSING_MENU = "BROWSING_MENU"
    BUILDING_CART = "BUILDING_CART"
    COLLECTING_DETAILS = "COLLECTING_DETAILS"
    ORDER_CONFIRMED = "ORDER_CONFIRMED"

# =========================================================================================
# SUPABASE DATABASE LAYER
# =========================================================================================
TABLE_RESTAURANT_SESSIONS = "restaurant_sessions"
TABLE_ORDERS = "orders"
TABLE_CHAT_HISTORY = "chat_history"

def get_supabase_headers():
    return {
        "apikey": SUPABASE_KEY or "",
        "Authorization": f"Bearer {SUPABASE_KEY or ''}",
        "Content-Type": "application/json"
    }

def get_restaurant_session(phone: str, restaurant_id: str) -> dict:
    """Retrieve or initialize the active customer session from Supabase."""
    default_session = {
        "phone_number": phone,
        "restaurant_id": restaurant_id,
        "order_state": OrderState.BROWSING_MENU,
        "customer_cart": {
            "items": [],
            "total_amount": 0.0,
            "special_instructions": None
        },
        "customer_details": {
            "customer_name": None,
            "delivery_address": None,
            "contact_phone": phone,
            "payment_method": None
        },
        "active_order_id": None,
        "order_status": None,
        "chat_history": [],
        "last_interaction": time.time()
    }
    if not SUPABASE_URL or not SUPABASE_KEY:
        return default_session

    try:
        url = f"{SUPABASE_URL}/rest/v1/{TABLE_RESTAURANT_SESSIONS}?phone_number=eq.{phone}&restaurant_id=eq.{restaurant_id}&select=*"
        res = requests.get(url, headers=get_supabase_headers(), timeout=10)
        if res.status_code == 200 and res.json():
            data = res.json()[0].get("session_data", {})
            return {**default_session, **data}
    except Exception as e:
        logger.error(f"Supabase restaurant session fetch failed: {e}")
    return default_session

def save_restaurant_session(phone: str, restaurant_id: str, session: dict):
    """Save customer session data to Supabase."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return
    session["last_interaction"] = time.time()
    payload = {
        "phone_number": phone,
        "restaurant_id": restaurant_id,
        "session_data": session
    }
    try:
        url = f"{SUPABASE_URL}/rest/v1/{TABLE_RESTAURANT_SESSIONS}"
        headers = get_supabase_headers()
        headers["Prefer"] = "resolution=merge-duplicates"
        requests.post(url, headers=headers, json=payload, timeout=10)
    except Exception as e:
        logger.error(f"Supabase restaurant session save failed: {e}")

def save_order(restaurant_id: str, phone: str, order_data: dict) -> dict:
    """Insert a new confirmed food order into the orders table."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return {"id": f"ORD-{int(time.time())}", **order_data}
    payload = {
        "restaurant_id": restaurant_id,
        "phone_number": phone,
        "order_data": order_data,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    try:
        url = f"{SUPABASE_URL}/rest/v1/{TABLE_ORDERS}"
        headers = get_supabase_headers()
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        if res.status_code in (200, 201):
            return res.json()[0] if isinstance(res.json(), list) and res.json() else payload
    except Exception as e:
        logger.error(f"Supabase save order failed: {e}")
    return payload

def save_chat_history(phone: str, restaurant_id: str, role: str, content: str):
    """Save conversation message to chat history table."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return
    payload = {
        "phone_number": phone,
        "restaurant_id": restaurant_id,
        "role": role,
        "content": content
    }
    try:
        url = f"{SUPABASE_URL}/rest/v1/{TABLE_CHAT_HISTORY}"
        requests.post(url, headers=get_supabase_headers(), json=payload, timeout=10)
    except Exception as e:
        logger.error(f"Supabase chat history save failed: {e}")

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

        file_path = f"/tmp/{audio_id}.ogg"
        with open(file_path, "wb") as f:
            f.write(media_res.content)

        if groq_client:
            with open(file_path, "rb") as file:
                transcription = groq_client.audio.transcriptions.create(
                    file=(file_path, file.read()),
                    model="whisper-large-v3",
                    prompt="The audio is in Urdu or English regarding restaurant food orders, dishes, and menu inquiries. If unintelligible or noise, return empty text."
                )
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
    "ch**d", "bh**d", "m***", "b***", "bakwaas", "ch****", "motherchod", "bhenchod",
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
    try:
        return json.loads(raw_text)
    except Exception:
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
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

def _is_rate_limit_err(err: Exception) -> bool:
    msg = str(err).lower()
    return any(x in msg for x in ["429", "rate limit", "quota", "too many requests", "resource_exhausted"])

def chat_completion_fallback(messages: list) -> str:
    """
    Multi-tier LLM failover architecture:
    Tier 1: Groq (with dual-key rotation)
    Tier 2: OpenRouter (with model/key rotation)
    Tier 3: Gemini (with dual-key rotation)
    Tier 4: Stealth OpenRouter
    Tier 5: Cohere
    Tier 6: Kilo AI
    """
    messages = _trim_messages(messages)

    # TIER 1: Groq
    if GROQ_CLIENTS:
        for idx, client in enumerate(GROQ_CLIENTS, 1):
            for model_name in ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]:
                try:
                    logger.info(f"🔄 [T1-Groq] Key{idx} -> {model_name}")
                    completion = client.chat.completions.create(
                        messages=messages,
                        model=model_name,
                        temperature=0.4,
                        response_format={"type": "json_object"},
                        timeout=LLM_CALL_TIMEOUT
                    )
                    content = completion.choices[0].message.content
                    if content:
                        return content
                except Exception as e:
                    if _is_rate_limit_err(e):
                        logger.warning(f"⚠️ [T1-Groq] Key{idx} rate limit on {model_name}")
                        break
                    logger.warning(f"⚠️ [T1-Groq] Key{idx} error: {e}")

    # TIER 2: OpenRouter
    if OPENROUTER_KEYS:
        for idx, key in enumerate(OPENROUTER_KEYS, 1):
            for model_name in ["openai/gpt-4o-mini", "meta-llama/llama-3.3-70b-instruct"]:
                try:
                    logger.info(f"🔄 [T2-OpenRouter] Key{idx} -> {model_name}")
                    res = requests.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                        json={"model": model_name, "messages": messages, "temperature": 0.4, "response_format": {"type": "json_object"}},
                        timeout=LLM_CALL_TIMEOUT
                    )
                    if res.status_code == 200:
                        return res.json()["choices"][0]["message"]["content"]
                except Exception as e:
                    logger.warning(f"⚠️ [T2-OpenRouter] Key{idx} exception: {e}")

    # TIER 3: Gemini
    if GEMINI_KEYS:
        for idx, gem_key in enumerate(GEMINI_KEYS, 1):
            try:
                logger.info(f"🔄 [T3-Gemini] Key{idx} -> gemini-2.0-flash")
                res = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/openai/chat/completions?key={gem_key}",
                    json={"model": "gemini-2.0-flash", "messages": messages, "temperature": 0.4, "response_format": {"type": "json_object"}},
                    timeout=LLM_CALL_TIMEOUT
                )
                if res.status_code == 200:
                    return res.json()["choices"][0]["message"]["content"]
            except Exception as e:
                logger.warning(f"⚠️ [T3-Gemini] Key{idx} exception: {e}")

    # TIER 4: Stealth OpenRouter
    if OPENROUTER_KEYS:
        for idx, or_key in enumerate(OPENROUTER_KEYS, 1):
            try:
                logger.info(f"🔄 [T4-Stealth] Key{idx} -> stealth/ox-alpha")
                client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=or_key, max_retries=0)
                resp = client.chat.completions.create(
                    model="stealth/ox-alpha",
                    messages=messages,
                    temperature=0.0,
                    timeout=LLM_CALL_TIMEOUT,
                    response_format={"type": "json_object"}
                )
                if resp.choices[0].message.content:
                    return resp.choices[0].message.content
            except Exception as e:
                logger.warning(f"⚠️ [T4-Stealth] Key{idx} error: {e}")

    # TIER 5: Cohere
    if COHERE_KEYS:
        for idx, co_key in enumerate(COHERE_KEYS, 1):
            try:
                logger.info(f"🔄 [T5-Cohere] Key{idx} -> command-r")
                client = OpenAI(base_url="https://api.cohere.com/v2", api_key=co_key, max_retries=0)
                resp = client.chat.completions.create(
                    model="command-r",
                    messages=messages,
                    temperature=0.4,
                    timeout=LLM_CALL_TIMEOUT,
                    response_format={"type": "json_object"}
                )
                if resp.choices[0].message.content:
                    return resp.choices[0].message.content
            except Exception as e:
                logger.warning(f"⚠️ [T5-Cohere] Key{idx} error: {e}")

    # TIER 6: Kilo AI
    if KILO_KEYS:
        for idx, kilo_key in enumerate(KILO_KEYS, 1):
            try:
                logger.info(f"🔄 [T6-Kilo] Key{idx} -> nemotron")
                client = OpenAI(base_url="https://api.kilo.ai/api/gateway", api_key=kilo_key, max_retries=0)
                resp = client.chat.completions.create(
                    model="nvidia/nemotron-3-ultra-550b-a55b:free",
                    messages=messages,
                    temperature=0.4,
                    timeout=LLM_CALL_TIMEOUT,
                    response_format={"type": "json_object"}
                )
                if resp.choices[0].message.content:
                    return resp.choices[0].message.content
            except Exception as e:
                logger.warning(f"⚠️ [T6-Kilo] Key{idx} error: {e}")

    logger.error("All LLM tiers failed. Sending emergency fallback.")
    return json.dumps({
        "reply_text": "Janab, humara server is waqt thora masroof hai. Baraye meharbani kuch lamhay baad dobara rabta karein.",
        "order_state": OrderState.BROWSING_MENU
    })

# =========================================================================================
# RESTAURANT STATE MACHINE SKELETON
# =========================================================================================
def handle_browsing_menu(session: dict, incoming_message: str, btn_id: str = None) -> dict:
    """
    Skeleton handler for BROWSING_MENU state.
    Allows customers to explore categories, view popular dishes, and ask food queries.
    Transitions to BUILDING_CART when an item is selected.
    """
    logger.info(f"State Machine: BROWSING_MENU | Message: '{incoming_message}' | Button: {btn_id}")
    
    # Placeholder: Handle button fast-tracks or keyword triggers
    if btn_id == "btn_view_menu" or "menu" in incoming_message.lower():
        reply = (
            "🍽️ *Humara Menu:*\n\n"
            "1. 🍔 Gourmet Burgers\n"
            "2. 🍕 Cheesy Pizzas\n"
            "3. 🍗 Crispy Fried Chicken\n"
            "4. 🥤 Drinks & Shakes\n\n"
            "Aap kya order karna chahein ge? Naam ya number batayein!"
        )
        return {
            "reply_text": reply,
            "next_state": OrderState.BUILDING_CART,
            "buttons": ["Gourmet Burgers 🍔", "Cheesy Pizza 🍕", "Cold Drinks 🥤"]
        }

    # Transition to building cart if user mentions ordering food items
    return {
        "reply_text": "Khush amdeed! 🍔 Humare pas behtareen burgers, pizzas aur drinks dastiyab hain. Aap kya khana pasand karein ge?",
        "next_state": OrderState.BROWSING_MENU,
        "buttons": ["Menu Dekhein 📋", "Burger Chahiye 🍔", "Pizza Chahiye 🍕"]
    }

def handle_building_cart(session: dict, incoming_message: str, btn_id: str = None) -> dict:
    """
    Skeleton handler for BUILDING_CART state.
    Adds/removes items from customer_cart, calculates total amounts,
    and transitions to COLLECTING_DETAILS when checkout is triggered.
    """
    logger.info(f"State Machine: BUILDING_CART | Message: '{incoming_message}' | Button: {btn_id}")
    
    cart = session.get("customer_cart", {"items": [], "total_amount": 0.0})
    
    if btn_id == "btn_checkout" or "checkout" in incoming_message.lower() or "confirm order" in incoming_message.lower():
        return {
            "reply_text": "Zabardast! Aapka order finalize karne ke liye bas aapka Delivery Address aur Naam darkar hai. 📍 Baraye meharbani apna Mukammal Delivery Address share karein.",
            "next_state": OrderState.COLLECTING_DETAILS,
            "buttons": []
        }

    # Placeholder for item addition into cart
    return {
        "reply_text": "Yeh item aapke cart mein shamil kar diya gaya hai! 🛒 Kya aap mazeed kuch add karna chahein ge ya checkout karein?",
        "next_state": OrderState.BUILDING_CART,
        "buttons": ["Checkout Karein 💳", "Mazeed Items 🍔", "Cart Dekhein 🛒"]
    }

def handle_collecting_details(session: dict, incoming_message: str, btn_id: str = None) -> dict:
    """
    Skeleton handler for COLLECTING_DETAILS state.
    Collects customer name, delivery address, contact info, and payment method.
    Transitions to ORDER_CONFIRMED once details are complete.
    """
    logger.info(f"State Machine: COLLECTING_DETAILS | Message: '{incoming_message}' | Button: {btn_id}")
    
    details = session.get("customer_details", {})
    
    if not details.get("delivery_address"):
        details["delivery_address"] = incoming_message.strip()
        session["customer_details"] = details
        return {
            "reply_text": "Address note ho gaya! 🏡 Baraye meharbani apna Pura Naam bata dein taake rider ko asani ho.",
            "next_state": OrderState.COLLECTING_DETAILS,
            "buttons": []
        }
    
    if not details.get("customer_name"):
        details["customer_name"] = incoming_message.strip()
        session["customer_details"] = details
        return {
            "reply_text": f"Shukriya {details['customer_name']}! Payment method select karein: Cash on Delivery ya Online Card?",
            "next_state": OrderState.COLLECTING_DETAILS,
            "buttons": ["Cash on Delivery 💵", "Online Card 💳"]
        }
    
    # Complete collection and move to confirmed
    details["payment_method"] = incoming_message.strip()
    session["customer_details"] = details
    return {
        "reply_text": "Tamam details mukammal ho chuki hain! Kya main aapka order confirm kar dun?",
        "next_state": OrderState.ORDER_CONFIRMED,
        "buttons": ["Haan, Confirm Karein ✅", "Cancel Karein ❌"]
    }

def handle_order_confirmed(session: dict, incoming_message: str, btn_id: str = None) -> dict:
    """
    Skeleton handler for ORDER_CONFIRMED state.
    Generates order summary receipt, writes order into Supabase 'orders' table,
    and provides status updates.
    """
    logger.info(f"State Machine: ORDER_CONFIRMED | Message: '{incoming_message}' | Button: {btn_id}")
    
    order_id = f"ORD-{int(time.time())}"
    session["active_order_id"] = order_id
    session["order_status"] = "PREPARING"
    
    order_summary = {
        "order_id": order_id,
        "cart": session.get("customer_cart", {}),
        "customer": session.get("customer_details", {}),
        "status": "PREPARING",
        "timestamp": time.time()
    }
    
    save_order(
        restaurant_id=session.get("restaurant_id", "default_restaurant"),
        phone=session.get("phone_number", ""),
        order_data=order_summary
    )
    
    reply = (
        f"🎉 *Order Confirm Ho Gaya!*\n\n"
        f"Order ID: *{order_id}*\n"
        f"Status: *Kitchen mein tayari shuru hai* 👨‍🍳\n"
        f"Estimated Delivery: *30-40 Minutes* 🛵\n\n"
        f"Humare restaurant ka intekhab karne ka shukriya!"
    )
    return {
        "reply_text": reply,
        "next_state": OrderState.ORDER_CONFIRMED,
        "buttons": ["Track Order 🛵", "Naya Order 🍔"]
    }

def handle_order_flow(session: dict, incoming_message: str, btn_id: str = None) -> dict:
    """
    Master state machine dispatcher for restaurant food ordering.
    Routes execution to the active state handler and updates session state.
    """
    current_state = session.get("order_state", OrderState.BROWSING_MENU)

    if current_state == OrderState.BROWSING_MENU:
        result = handle_browsing_menu(session, incoming_message, btn_id)
    elif current_state == OrderState.BUILDING_CART:
        result = handle_building_cart(session, incoming_message, btn_id)
    elif current_state == OrderState.COLLECTING_DETAILS:
        result = handle_collecting_details(session, incoming_message, btn_id)
    elif current_state == OrderState.ORDER_CONFIRMED:
        result = handle_order_confirmed(session, incoming_message, btn_id)
    else:
        session["order_state"] = OrderState.BROWSING_MENU
        result = handle_browsing_menu(session, incoming_message, btn_id)

    if "next_state" in result:
        session["order_state"] = result["next_state"]

    return result

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

            # Sanitize profanity
            cleaned_body, had_abuse = sanitize_and_extract(msg_body)
            if had_abuse:
                warning_text = "Baraye meharbani munasib alfaz ka istemal karein. Hum ek restaurant food ordering service hain."
                send_whatsapp_text(restaurant_id, from_number, warning_text, wa_token)
                continue
            msg_body = cleaned_body

            # Fetch customer session from Supabase
            session = get_restaurant_session(from_number, restaurant_id)
            chat_hist = session.get("chat_history", [])

            # Route through restaurant state machine skeleton
            flow_result = handle_order_flow(session, msg_body, btn_id)
            reply_text = flow_result.get("reply_text", "")
            buttons = flow_result.get("buttons", [])

            # If conversational AI processing is needed, inject placeholder system prompt
            if not reply_text:
                sys_prompt = f"{RESTAURANT_SYSTEM_PROMPT_PLACEHOLDER}\nCURRENT SESSION: {json.dumps(session)}"
                llm_messages = [{"role": "system", "content": sys_prompt}]
                llm_messages.extend(chat_hist[-6:])
                llm_messages.append({"role": "user", "content": msg_body})

                ai_res = chat_completion_fallback(llm_messages)
                parsed = extract_clean_json(ai_res)
                reply_text = parsed.get("reply_text", ai_res)

            # Record chat history
            chat_hist.append({"role": "user", "content": msg_body})
            chat_hist.append({"role": "assistant", "content": reply_text})
            session["chat_history"] = chat_hist[-20:]

            save_chat_history(from_number, restaurant_id, "user", msg_body)
            save_chat_history(from_number, restaurant_id, "assistant", reply_text)
            save_restaurant_session(from_number, restaurant_id, session)

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
    return PlainTextResponse(content="Restaurant Food Ordering WhatsApp Bot is online!")

@app.get('/health')
def health():
    return JSONResponse(content={"status": "healthy", "service": "restaurant-bot", "timestamp": time.time()})

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

@app.post('/chat')
async def web_chat_endpoint(request: Request):
    """REST API endpoint for web/mobile chat UI to interact with Restaurant Bot."""
    body = await request.json()
    user_msg = body.get("message", "")
    customer_id = body.get("email", "guest_user")
    restaurant_id = body.get("client_id", "restaurant_default")

    session = get_restaurant_session(customer_id, restaurant_id)
    flow_result = handle_order_flow(session, user_msg)
    reply_text = flow_result.get("reply_text", "")

    if not reply_text:
        sys_prompt = f"{RESTAURANT_SYSTEM_PROMPT_PLACEHOLDER}\nCURRENT SESSION: {json.dumps(session)}"
        ai_res = chat_completion_fallback([
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_msg}
        ])
        parsed = extract_clean_json(ai_res)
        reply_text = parsed.get("reply_text", ai_res)

    save_restaurant_session(customer_id, restaurant_id, session)
    return JSONResponse(content={"response": reply_text, "order_state": session.get("order_state")})

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
