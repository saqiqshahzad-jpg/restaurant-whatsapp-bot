import re
import logging
from typing import Tuple, Optional, Dict, Any

logger = logging.getLogger("language_helper")

# Supported language metadata and native templates
LANGUAGES_CONFIG: Dict[str, Dict[str, str]] = {
    "English": {
        "name": "English",
        "native_name": "English",
        "offer_text": "It looks like you want to speak in English! Just reply with '1' and I'll switch to English right away! 😄🍔",
        "locked_welcome": "Boom! English locked in! 🚀 Welcome to Zaiqa Grill, friend! What mouth-watering treat are we getting for you today? A Crispy Zinger, Royal Biryani, or some Loaded Fries? 🍔🍟",
        "btn_text": "1️⃣ Switch to English"
    },
    "Arabic": {
        "name": "Arabic",
        "native_name": "العربية",
        "offer_text": "يبدو أنك تريد التحدث باللغة العربية! أرسل '1' وسأتحدث معك بالعربية فوراً! 😄🍔",
        "locked_welcome": "رائع! تم تفعيل اللغة العربية! 🚀 أهلاً بك في زايقة جريل! ماذا تود أن تطلب اليوم من أشهى المأكولات؟ 🍔🍟",
        "btn_text": "1️⃣ التبديل إلى العربية"
    },
    "Urdu_Script": {
        "name": "Urdu (اردو)",
        "native_name": "اردو",
        "offer_text": "لگتا ہے آپ اردو رسم الخط میں بات کرنا چاہتے ہیں! بس '1' لکھ کر بھیجیں، میں اردو میں بات کروں گا! 😄🍔",
        "locked_welcome": "زبردست! اردو زبان منتخب ہو گئی ہے! 🚀 ذائقہ گرل میں خوش آمدید! آج کیا کھانا پسند کریں گے؟ 🍔🍟",
        "btn_text": "1️⃣ اردو میں بات کریں"
    },
    "Hindi": {
        "name": "Hindi",
        "native_name": "हिन्दी",
        "offer_text": "लगता है आप हिन्दी में बात करना चाहते हैं! बस '1' लिखकर भेजें, मैं हिन्दी में बात करूँगा! 😄🍔",
        "locked_welcome": "शानदार! हिन्दी लॉक हो गई! 🚀 ज़ायका ग्रिल में आपका स्वागत है! आज क्या खाना पसंद करेंगे? 🍔🍟",
        "btn_text": "1️⃣ हिन्दी में बदलें"
    },
    "Spanish": {
        "name": "Spanish",
        "native_name": "Español",
        "offer_text": "¡Parece que quieres hablar en español! ¡Solo responde '1' y cambiaré a español! 😄🍔",
        "locked_welcome": "¡Genial! ¡Español activado! 🚀 ¡Bienvenido a Zaiqa Grill! ¿Qué delicia te gustaría pedir hoy? 🍔🍟",
        "btn_text": "1️⃣ Cambiar a Español"
    },
    "French": {
        "name": "French",
        "native_name": "Français",
        "offer_text": "Il semble que vous souhaitiez parler en français ! Répondez simplement '1' pour passer au français ! 😄🍔",
        "locked_welcome": "Parfait ! Français verrouillé ! 🚀 Bienvenue chez Zaiqa Grill ! Que désirez-vous commander aujourd'hui ? 🍔🍟",
        "btn_text": "1️⃣ Passer au Français"
    },
    "German": {
        "name": "German",
        "native_name": "Deutsch",
        "offer_text": "Es scheint, dass Sie auf Deutsch sprechen möchten! Antworten Sie einfach mit '1', um zu Deutsch zu wechseln! 😄🍔",
        "locked_welcome": "Super! Deutsch aktiviert! 🚀 Willkommen bei Zaiqa Grill! Was darf es heute Leckeres für Sie sein? 🍔🍟",
        "btn_text": "1️⃣ Zu Deutsch wechseln"
    },
    "Turkish": {
        "name": "Turkish",
        "native_name": "Türkçe",
        "offer_text": "Türkçe konuşmak istiyorsunuz gibi görünüyor! Türkçe'ye geçmek için '1' yazmanız yeterli! 😄🍔",
        "locked_welcome": "Harika! Türkçe kilitlendi! 🚀 Zaiqa Grill'e hoş geldiniz! Bugün ne sipariş etmek istersiniz? 🍔🍟",
        "btn_text": "1️⃣ Türkçe'ye geç"
    },
    "Russian": {
        "name": "Russian",
        "native_name": "Русский",
        "offer_text": "Похоже, вы хотите общаться на русском! Просто ответьте '1', и я переключусь на русский язык! 😄🍔",
        "locked_welcome": "Отлично! Русский язык включен! 🚀 Добро пожаловать в Zaiqa Grill! Что вкусненького для вас приготовить? 🍔🍟",
        "btn_text": "1️⃣ Перейти на русский"
    },
    "Chinese": {
        "name": "Chinese",
        "native_name": "中文",
        "offer_text": "看来您想用中文交流！只需回复“1”，我将立即切换为中文！😄🍔",
        "locked_welcome": "太棒了！中文已锁定！🚀 欢迎光临 Zaiqa Grill！今天想吃点什么美味？ 🍔🍟",
        "btn_text": "1️⃣ 切换为中文"
    },
    "Roman_Urdu": {
        "name": "Roman Urdu",
        "native_name": "Roman Urdu",
        "offer_text": "Lagta hai aap wapis Roman Urdu mein baat karna chahte hain! Bas '1' likh kar bhejein! 😄🍔",
        "locked_welcome": "Acha jani! Wapis Roman Urdu par aa gaye hain! 🚀 Aur sunayein, kya khane ka mood hai? Garam Zinger, Biryani ya Loaded Fries? 🍔🍟🤤",
        "btn_text": "1️⃣ Wapis Roman Urdu"
    }
}

ROMAN_URDU_MARKERS = {
    "kya", "hai", "hain", "chahiye", "karo", "kardo", "bhai", "bhejo", "mujhe", "aap",
    "janaab", "janab", "shukriya", "theek", "thik", "acha", "achha", "bohot", "nahi", "ka",
    "ki", "ke", "ko", "se", "mein", "par", "hoga", "karna", "krdo", "mangwa", "lekin",
    "aur", "pe", "yar", "yaar", "jani", "bhejna", "wahi", "wala", "wali", "biryani",
    "khana", "khush", "amdeed", "batao", "batayein", "dein", "do", "lena", "dena", "shuru",
    "haan", "ho", "gaya", "krna", "chah", "raha", "karwado", "pack", "kar", "rakho"
}

ENGLISH_MARKERS = {
    "hello", "hi", "hey", "please", "order", "want", "food", "deliver", "delivery",
    "address", "how", "what", "can", "could", "would", "like", "much", "cost", "price",
    "thanks", "thank", "you", "good", "where", "when", "send", "give", "me", "the",
    "is", "are", "with", "have", "need", "show", "menu", "bring", "serve", "take"
}


def detect_foreign_language(text: str, current_lang: str = "Roman Urdu") -> Optional[str]:
    """
    Detects if the user's message is in a foreign language different from current_lang.
    Returns the key in LANGUAGES_CONFIG (e.g. 'English', 'Arabic', 'Russian') or None.
    """
    clean_text = text.strip()
    if not clean_text:
        return None

    # 1. Non-Latin Script Detection (0ms fast path)
    if re.search(r'[\u0600-\u06FF]', clean_text):
        # Urdu-specific characters
        if re.search(r'[ٹڈڑںئےہ]', clean_text):
            target = "Urdu_Script"
        else:
            target = "Arabic"
        if current_lang != LANGUAGES_CONFIG[target]["name"]:
            return target
        return None

    if re.search(r'[\u0400-\u04FF]', clean_text):
        if current_lang != "Russian":
            return "Russian"
        return None

    if re.search(r'[\u0900-\u097F]', clean_text):
        if current_lang != "Hindi":
            return "Hindi"
        return None

    if re.search(r'[\u4e00-\u9fff]', clean_text):
        if current_lang != "Chinese":
            return "Chinese"
        return None

    # 2. Latin Script Analysis
    tokens = set(re.findall(r'\b[a-zA-Z]{2,}\b', clean_text.lower()))
    if not tokens:
        return None

    ru_matches = tokens.intersection(ROMAN_URDU_MARKERS)
    en_matches = tokens.intersection(ENGLISH_MARKERS)

    # Spanish markers
    es_markers = {"hola", "quiero", "pedido", "comida", "gracias", "por", "favor", "buenas"}
    if len(tokens.intersection(es_markers)) >= 2:
        if current_lang != "Spanish":
            return "Spanish"
        return None

    # French markers
    fr_markers = {"bonjour", "salut", "veux", "commander", "merci", "sil", "vous", "plait"}
    if len(tokens.intersection(fr_markers)) >= 2:
        if current_lang != "French":
            return "French"
        return None

    # German markers
    de_markers = {"hallo", "mochte", "essen", "bestellen", "danke", "bitte", "guten", "tag"}
    if len(tokens.intersection(de_markers)) >= 2:
        if current_lang != "German":
            return "German"
        return None

    # Turkish markers
    tr_markers = {"merhaba", "yemek", "siparis", "istiyorum", "tesekkurler", "lutfen"}
    if len(tokens.intersection(tr_markers)) >= 2:
        if current_lang != "Turkish":
            return "Turkish"
        return None

    # Check English vs Roman Urdu
    # If the user is currently speaking Roman Urdu, and incoming message has strong English markers
    # and no/few Roman Urdu markers, trigger English offer:
    if current_lang == "Roman Urdu":
        if len(en_matches) >= 2 and len(ru_matches) == 0:
            return "English"
        # Explicit English conversational phrases
        if any(phrase in clean_text.lower() for phrase in [
            "hello", "hi there", "can i order", "i want to order", "what is on the menu",
            "show me the menu", "how much is", "can you deliver", "what are your deals"
        ]):
            if len(ru_matches) <= 1:
                return "English"
    elif current_lang == "English":
        # If currently in English and user speaks Roman Urdu:
        if len(ru_matches) >= 2 and len(en_matches) <= 1:
            return "Roman_Urdu"

    return None


def build_language_switch_offer(target_lang_key: str) -> Tuple[str, list]:
    """
    Builds the bilingual language switch prompt:
    Part A: In Roman Urdu
    Part B: In the target language itself
    Returns: (reply_text, buttons_list)
    """
    if target_lang_key == "Roman_Urdu":
        reply = (
            "Lagta hai aap Roman Urdu mein baat karna chahte hain! 🍔\n"
            "Bas mujhe *'1'* likh kar bhejein, main foran Roman Urdu mein shuru ho jaunga 😄\n\n"
            "It seems you want to switch back to Roman Urdu! Just reply with *'1'* and I'll switch back! 🚀"
        )
        buttons = ["1️⃣ Haan Roman Urdu", "Menu Dekhein 📋"]
        return reply, buttons

    cfg = LANGUAGES_CONFIG.get(target_lang_key)
    if not cfg:
        return "", []

    lang_name = cfg["name"]
    native_offer = cfg["offer_text"]
    btn_text = cfg["btn_text"]

    reply = (
        f"Lagta hai aap *{lang_name}* mein baat karna chahte hain! 🍔\n"
        f"Bas mujhe *'1'* likh kar bhejein, main {lang_name} mein shuru ho jaunga 😄\n\n"
        f"{native_offer}"
    )
    buttons = [btn_text, "Menu Dekhein 📋"]
    return reply, buttons


def is_smart_language_confirmation(msg: str, btn_id: str, session: dict) -> bool:
    """
    Smart thinking engine:
    Verifies if the user typing '1' actually meant to accept the pending language switch,
    or if '1' was typed in another context (e.g. quantity '1 burger', or button choice).
    Hidden internal logic that user never sees.
    """
    pending_lang = session.get("pending_language")
    if not pending_lang:
        return False

    msg_clean = msg.strip().lower()

    # If clicked the explicit language button
    if btn_id and any(k in btn_id.lower() for k in ["switch", "lang", "urdu", "english", "arabic", "1"]):
        return True

    # If clicked or sent text matching the button title
    cfg = LANGUAGES_CONFIG.get(pending_lang, {})
    btn_text = cfg.get("btn_text", "").lower()
    if btn_text and (msg_clean == btn_text or btn_text in msg_clean):
        return True

    # Check if input specifically confirms the '1' prompt
    exact_ones = {"1", "1️⃣", "one", "haan 1", "yes 1", "yes", "haan", "ok 1", "1 please", "option 1"}
    if msg_clean in exact_ones:
        return True

    return False
