import os
import json
import re
import logging
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger("menu_manager")

MENU_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "menu.json")

# Fallback default menu in case menu.json is missing or corrupt
DEFAULT_MENU_FALLBACK = {
    "restaurant_name": "Zaiqa Grill & Fast Food",
    "currency": "PKR",
    "currency_symbol": "Rs.",
    "delivery_fee": 150,
    "upsell_recommendations": ["Loaded Fries", "Mint Margarita"],
    "categories": ["Burgers", "Rice & Biryani", "Sides & Fries", "Beverages"],
    "items": [
        {
            "id": "crispy_zinger",
            "name": "Crispy Zinger Burger",
            "category": "Burgers",
            "tag": "Bestseller 🔥",
            "image": "/images/zinger.jpg",
            "description": "Crispy fried golden chicken fillet oozing with cheese lava sauce in a toasted brioche bun",
            "base_price": 550,
            "variants": {"Regular": 550, "Cheese Lava": 650},
            "keywords": ["zinger", "burger", "crispy", "crispy burger", "cheese lava", "zinger burger", "chicken burger"],
            "is_available": True
        },
        {
            "id": "special_biryani",
            "name": "Special Chicken Biryani",
            "category": "Rice & Biryani",
            "tag": "Chef Special 👑",
            "image": "/images/biryani.jpg",
            "description": "Royal aromatic long-grain basmati rice cooked in clay handi with tender spiced chicken",
            "base_price": 400,
            "variants": {
                "Single": 400,
                "Double": 750,
                "Single Mild": 400,
                "Single Spicy": 400,
                "Double Mild": 750,
                "Double Spicy": 750
            },
            "keywords": ["biryani", "chicken biryani", "chawal", "rice", "single biryani", "double biryani", "spicy biryani"],
            "is_available": True
        },
        {
            "id": "loaded_fries",
            "name": "Loaded Fries",
            "category": "Sides & Fries",
            "tag": "Crispy & Cheesy 🧀",
            "image": "/images/fries.jpg",
            "description": "Golden potato fries loaded with signature sauces and seasonings",
            "base_price": 450,
            "variants": {"Mayo Garlic": 450, "Jalapeno Cheese": 450},
            "keywords": ["fries", "loaded fries", "chips", "finger chips", "mayo garlic", "jalapeno cheese"],
            "is_available": True
        },
        {
            "id": "mint_margarita",
            "name": "Mint Margarita",
            "category": "Beverages",
            "tag": "Refreshing ❄️",
            "image": "/images/margarita.jpg",
            "description": "Chilled electric mint cooler with fresh crushed garden mint leaves and lime wheel garnish",
            "base_price": 150,
            "variants": {"Regular": 150},
            "keywords": ["mint margarita", "margarita", "mint drink", "lemon mint", "cooler"],
            "is_available": True
        },
        {
            "id": "cold_drink",
            "name": "Cold Drink",
            "category": "Beverages",
            "tag": "Chilled 🥤",
            "image": "/images/margarita.jpg",
            "description": "Ice-cold carbonated beverage (Coke, Sprite, Fanta)",
            "base_price": 150,
            "variants": {"Regular": 150, "Coke": 150, "Sprite": 150, "Fanta": 150},
            "keywords": ["drink", "cold drink", "coke", "sprite", "fanta", "pepsi", "soda"],
            "is_available": True
        }
    ]
}


class MenuManager:
    """
    High-performance, zero-latency Menu Manager with hot-reloading.
    Caches menu data in RAM and automatically detects changes to menu.json via file modification time.
    Provides fast lookup, auto-guard pricing, and prompt generation for maximum AI accuracy.
    """
    _instance = None

    def __init__(self, file_path: str = MENU_FILE_PATH):
        self.file_path = file_path
        self._last_mtime: float = -1.0
        self._raw_data: Dict[str, Any] = {}
        self._items_by_id: Dict[str, Dict[str, Any]] = {}
        self._items_by_name_lower: Dict[str, Dict[str, Any]] = {}
        self._keyword_to_item: Dict[str, Dict[str, Any]] = {}
        self._whatsapp_menu_text: str = ""
        self._system_prompt_menu_snippet: str = ""
        self._allowed_items_names: List[str] = []
        self._allowed_items_str: str = ""
        self._upsell_str: str = ""
        self._system_prompt_cache: str = ""
        self._restaurant_menu_dict: Dict[str, Any] = {}

        # Initial load
        self._reload_if_needed()

    @classmethod
    def get_instance(cls) -> "MenuManager":
        if cls._instance is None:
            cls._instance = MenuManager()
        return cls._instance

    def _reload_if_needed(self) -> None:
        """Microsecond check: reload only if file modified on disk."""
        try:
            if not os.path.exists(self.file_path):
                if self._last_mtime == -1:
                    logger.warning(f"menu.json not found at {self.file_path}. Using fallback menu.")
                    self._load_from_dict(DEFAULT_MENU_FALLBACK)
                return

            current_mtime = os.path.getmtime(self.file_path)
            if current_mtime != self._last_mtime:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._load_from_dict(data)
                self._last_mtime = current_mtime
                logger.info(f"⚡ [MenuManager] Loaded live menu from {self.file_path} ({len(self._items_by_id)} items)")
        except Exception as e:
            logger.error(f"Error loading menu.json: {e}")
            if not self._raw_data:
                self._load_from_dict(DEFAULT_MENU_FALLBACK)

    def _load_from_dict(self, data: Dict[str, Any]) -> None:
        """Parse, index, and pre-compute all representations for O(1) lookups."""
        self._raw_data = data
        self._items_by_id.clear()
        self._items_by_name_lower.clear()
        self._keyword_to_item.clear()
        self._restaurant_menu_dict.clear()

        items = data.get("items", [])
        allowed_names = []

        for item in items:
            if not item.get("is_available", True):
                continue
            item_id = item.get("id", "").strip()
            name = item.get("name", "").strip()
            if not name:
                continue

            self._items_by_id[item_id] = item
            name_lower = name.lower()
            self._items_by_name_lower[name_lower] = item
            allowed_names.append(name)

            # Build classic RESTAURANT_MENU dict for backward compatibility
            self._restaurant_menu_dict[name] = {
                "description": item.get("description", ""),
                "base_price": item.get("base_price", 0),
                "variants": item.get("variants", {})
            }

            # Index keywords
            keywords = item.get("keywords", [])
            for kw in keywords:
                kw_clean = kw.lower().strip()
                if kw_clean:
                    self._keyword_to_item[kw_clean] = item

            # Also index normalized words of item name as keywords
            for word in re.findall(r"\b\w{3,}\b", name_lower):
                if word not in ["and", "the", "with", "for"]:
                    self._keyword_to_item.setdefault(word, item)

        self._allowed_items_names = allowed_names
        self._allowed_items_str = ", ".join(allowed_names)

        upsells = data.get("upsell_recommendations", ["Loaded Fries", "Mint Margarita"])
        self._upsell_str = " or ".join(upsells)

        # Pre-build WhatsApp text
        self._build_whatsapp_menu_text()

        # Pre-build System Prompt snippet
        self._build_system_prompt_snippet()

        # Invalidate full system prompt cache
        self._system_prompt_cache = ""

    def _build_whatsapp_menu_text(self) -> None:
        """Pre-format WhatsApp-friendly catalog for 0ms runtime rendering."""
        r_name = self._raw_data.get("restaurant_name", "Zaiqa Grill & Fast Food")
        fee = self._raw_data.get("delivery_fee", 150)
        currency = self._raw_data.get("currency_symbol", "Rs.")
        categories = self._raw_data.get("categories", [])

        # Group items by category
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for it in self._items_by_id.values():
            cat = it.get("category", "General")
            grouped.setdefault(cat, []).append(it)

        lines = [f"🍔 *{r_name} Menu* 🍽️\n"]

        category_emojis = {
            "Burgers": "🍔",
            "Burgers & Sandwiches": "🍔",
            "Rice & Biryani": "🍗",
            "Rice & Biryani Royal": "🍗",
            "Crispy Fried & Broast": "🍗",
            "BBQ & Charcoal Grill": "🍢",
            "Paratha Rolls & Wraps": "🌯",
            "Artisanal Pizza & Calzones": "🍕",
            "Loaded Fries & Starters": "🍟",
            "Sides & Fries": "🍟",
            "Beverages & Chilled Coolers": "🥤",
            "Beverages": "🥤",
            "Drinks": "🥤",
            "Desserts & Sweet Delights": "🍰",
            "Desserts": "🍰",
            "Value Deals & Combos": "✨",
            "Deals & Combos": "✨"
        }

        cat_order = categories if categories else list(grouped.keys())
        idx = 1
        for cat in cat_order:
            cat_items = grouped.get(cat, [])
            if not cat_items:
                continue

            emoji = category_emojis.get(cat, "🍴")
            lines.append(f"{emoji} *{cat}*")

            for item in cat_items:
                name = item["name"]
                tag = f" ({item['tag']})" if item.get("tag") else ""
                variants = item.get("variants", {})

                if len(variants) == 1 and "Regular" in variants:
                    price_str = f"*{currency} {variants['Regular']}*"
                    lines.append(f"  {idx}️⃣ *{name}*{tag}: {price_str}")
                else:
                    lines.append(f"  {idx}️⃣ *{name}*{tag}:")
                    for v_name, v_price in variants.items():
                        lines.append(f"     • {v_name}: *{currency} {v_price}*")
                idx += 1
            lines.append("")

        lines.append(f"🛵 *Delivery Fee:* {currency} {fee} Flat Across City")
        lines.append("\nAap kya order karna pasand karein ge? Item ka naam batayein! 👇")

        self._whatsapp_menu_text = "\n".join(lines)

    def _build_system_prompt_snippet(self) -> None:
        """Pre-format concise, high-density menu catalog for LLM system prompt."""
        currency = self._raw_data.get("currency_symbol", "Rs.")
        fee = self._raw_data.get("delivery_fee", 150)

        lines = ["### OFFICIAL RESTAURANT MENU (Live Database):"]
        idx = 1
        for item in self._items_by_id.values():
            name = item["name"]
            variants = item.get("variants", {})
            v_list = [f"{v_name}: {currency} {v_price}" for v_name, v_price in variants.items()]
            lines.append(f"{idx}. {name} -> {', '.join(v_list)}")
            idx += 1

        lines.append(f"\nDelivery Fee: Flat {currency} {fee} across the city.")
        self._system_prompt_menu_snippet = "\n".join(lines)

    # -------------------------------------------------------------------------
    # Public Getters (Instant, Memory-cached)
    # -------------------------------------------------------------------------
    def get_restaurant_name(self) -> str:
        self._reload_if_needed()
        return self._raw_data.get("restaurant_name", "Zaiqa Grill & Fast Food")

    def get_delivery_fee(self) -> int:
        self._reload_if_needed()
        return int(self._raw_data.get("delivery_fee", 150))

    def get_currency_symbol(self) -> str:
        self._reload_if_needed()
        return self._raw_data.get("currency_symbol", "Rs.")

    def get_all_items(self) -> List[Dict[str, Any]]:
        self._reload_if_needed()
        return list(self._items_by_id.values())

    def get_allowed_item_names(self) -> List[str]:
        self._reload_if_needed()
        return list(self._allowed_items_names)

    def get_restaurant_menu_dict(self) -> Dict[str, Any]:
        """Returns the RESTAURANT_MENU dict for backward compatibility."""
        self._reload_if_needed()
        return dict(self._restaurant_menu_dict)

    def get_whatsapp_menu_text(self) -> str:
        self._reload_if_needed()
        return self._whatsapp_menu_text

    def get_api_menu_payload(self) -> Dict[str, Any]:
        """Provides dynamic JSON payload for frontend /menu endpoint."""
        self._reload_if_needed()
        currency = self.get_currency_symbol()
        items_formatted = []
        for it in self._items_by_id.values():
            variants_list = [{"name": vn, "price": vp} for vn, vp in it.get("variants", {}).items()]
            items_formatted.append({
                "id": it.get("id"),
                "name": it.get("name"),
                "category": it.get("category"),
                "tag": it.get("tag", ""),
                "image": it.get("image", "/images/zinger.jpg"),
                "description": it.get("description", ""),
                "base_price": it.get("base_price", 0),
                "variants": variants_list
            })

        return {
            "restaurant_name": self.get_restaurant_name(),
            "delivery_fee": self.get_delivery_fee(),
            "currency": currency,
            "menu": self._restaurant_menu_dict,
            "categories": self._raw_data.get("categories", []),
            "items": items_formatted
        }

    # -------------------------------------------------------------------------
    # Accuracy Guard: Validate Item and Enforce True Prices
    # -------------------------------------------------------------------------
    def validate_and_price_item(
        self,
        raw_name: str,
        raw_variant: str = "Regular",
        suggested_price: int = 0
    ) -> Tuple[str, str, int, bool]:
        """
        Anti-Hallucination Guard:
        Validates whether an item exists in the live menu.json.
        Enforces 100% correct official pricing from menu.json.
        Returns: (official_name, official_variant, official_unit_price, is_valid_item)
        """
        self._reload_if_needed()
        clean_name = raw_name.strip()
        clean_name_lower = clean_name.lower()

        # 1. Exact match on Item Name
        matched_item = self._items_by_name_lower.get(clean_name_lower)

        # 2. Exact match on Keyword
        if not matched_item:
            matched_item = self._keyword_to_item.get(clean_name_lower)

        # 3. Longest matching keyword (Word boundary search)
        if not matched_item:
            for kw, item in sorted(self._keyword_to_item.items(), key=lambda x: len(x[0]), reverse=True):
                pattern = r"\b" + re.escape(kw) + r"\b"
                if re.search(pattern, clean_name_lower):
                    matched_item = item
                    break

        # 4. Substring match against full names sorted by length descending
        if not matched_item:
            for item_name_lower, item in sorted(self._items_by_name_lower.items(), key=lambda x: len(x[0]), reverse=True):
                if item_name_lower in clean_name_lower or clean_name_lower in item_name_lower:
                    matched_item = item
                    break

        if not matched_item:
            # Item is NOT in menu.json!
            return clean_name, raw_variant, suggested_price, False

        official_name = matched_item["name"]
        variants = matched_item.get("variants", {})

        # Variant resolution
        clean_var = (raw_variant or "Regular").strip()
        matched_var = None
        matched_price = 0

        # Direct variant match (case-insensitive)
        for vn, vp in variants.items():
            if vn.lower() == clean_var.lower():
                matched_var = vn
                matched_price = vp
                break

        # Substring variant match (e.g. "lava" matches "Cheese Lava", "medium" matches "Medium 10-inch")
        if not matched_var:
            for vn, vp in variants.items():
                if clean_var.lower() in vn.lower() or vn.lower() in clean_var.lower():
                    matched_var = vn
                    matched_price = vp
                    break

        # Fallback to "Regular" if available
        if not matched_var and "Regular" in variants:
            matched_var = "Regular"
            matched_price = variants["Regular"]

        # Fallback to first available variant or base_price
        if not matched_var:
            if variants:
                first_var = next(iter(variants.keys()))
                matched_var = first_var
                matched_price = variants[first_var]
            else:
                matched_var = "Regular"
                matched_price = matched_item.get("base_price", 0)

        return official_name, matched_var, matched_price, True

    # -------------------------------------------------------------------------
    # Dynamic Rule-Based Food Parser (Zero-LLM Fast Path & Fallback)
    # -------------------------------------------------------------------------
    def parse_items_from_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Dynamically extracts ordered items, quantities, variants, and notes
        from customer text strictly using items defined in menu.json.
        Uses span-based longest match extraction to avoid double-counting sub-words.
        """
        self._reload_if_needed()
        text_lower = text.lower()
        extracted: List[Dict[str, Any]] = []

        # Find all potential candidate spans in the text
        candidate_spans = []

        for item in self._items_by_id.values():
            name = item["name"]
            keywords = item.get("keywords", [])

            # Check full name match
            name_pattern = r"\b" + re.escape(name.lower()) + r"\b"
            for m in re.finditer(name_pattern, text_lower):
                candidate_spans.append((m.start(), m.end(), item, m.group()))

            # Check keyword matches
            for kw in keywords:
                kw_clean = kw.lower().strip()
                if not kw_clean:
                    continue
                kw_pattern = r"\b" + re.escape(kw_clean) + r"\b"
                for m in re.finditer(kw_pattern, text_lower):
                    candidate_spans.append((m.start(), m.end(), item, m.group()))

        if not candidate_spans:
            return []

        # Sort candidate spans by span length descending (longest phrases take priority)
        candidate_spans.sort(key=lambda s: (s[1] - s[0]), reverse=True)

        accepted_spans = []
        occupied_indices = set()

        for start, end, item, matched_text in candidate_spans:
            span_indices = set(range(start, end))
            # If no overlap with an already accepted longer span
            if not span_indices.intersection(occupied_indices):
                accepted_spans.append((start, end, item, matched_text))
                occupied_indices.update(span_indices)

        # Sort accepted spans by their occurrence in text (left to right)
        accepted_spans.sort(key=lambda s: s[0])

        # Deduplicate same item if multiple keywords matched adjacent in the same phrase (e.g. "deal 1 solo zinger combo")
        filtered_spans = []
        for span in accepted_spans:
            start, end, item, matched_text = span
            is_duplicate = False
            for prev_start, prev_end, prev_item, _ in filtered_spans:
                if prev_item.get("id") == item.get("id") and abs(start - prev_end) < 25:
                    is_duplicate = True
                    break
            if not is_duplicate:
                filtered_spans.append(span)
        accepted_spans = filtered_spans

        # Local quantity extraction helper around a span
        def extract_local_qty(span_start: int, span_end: int) -> int:
            # Check up to 25 chars before the item
            prefix_window = text_lower[max(0, span_start - 25):span_start]
            # Check up to 15 chars after the item
            suffix_window = text_lower[span_end:min(len(text_lower), span_end + 15)]

            for w in ["2x", " 2 ", "2 ", " do ", "do ", " two ", "two "]:
                if w in prefix_window or w in suffix_window:
                    return 2
            for w in ["3x", " 3 ", "3 ", " teen ", "teen ", " three ", "three "]:
                if w in prefix_window or w in suffix_window:
                    return 3
            for w in ["4x", " 4 ", "4 ", " char ", "char ", " four ", "four "]:
                if w in prefix_window or w in suffix_window:
                    return 4
            for w in ["5x", " 5 ", "5 ", " paanch ", "paanch ", " five ", "five "]:
                if w in prefix_window or w in suffix_window:
                    return 5

            digits_prefix = re.findall(r"\b([1-9])\b", prefix_window)
            if digits_prefix:
                return int(digits_prefix[-1])
            digits_suffix = re.findall(r"\b([1-9])\b", suffix_window)
            if digits_suffix:
                return int(digits_suffix[0])

            return 1

        for start, end, item, matched_text in accepted_spans:
            name = item["name"]
            variants = item.get("variants", {})

            # Extract local quantity
            qty = extract_local_qty(start, end)

            # Local context window around this item to detect variant and notes
            window_start = max(0, start - 25)
            window_end = min(len(text_lower), end + 30)
            local_window = text_lower[window_start:window_end]

            chosen_var = "Regular"
            chosen_price = item.get("base_price", 0)

            # Match variant in local window or overall text
            for vn, vp in variants.items():
                vn_lower = vn.lower()
                vn_tokens = [t for t in re.findall(r"\w+", vn_lower) if len(t) > 2]
                if vn_lower in local_window or any(t in local_window for t in vn_tokens):
                    chosen_var = vn
                    chosen_price = vp
                    break

            if chosen_var == "Regular" and "Regular" in variants:
                chosen_price = variants["Regular"]
            elif chosen_var not in variants and variants:
                first_k = next(iter(variants.keys()))
                chosen_var = first_k
                chosen_price = variants[first_k]

            # Detect notes in local window
            notes = []
            if "less spicy" in local_window or "kam mirch" in local_window:
                notes.append("less spicy")
            if "extra spicy" in local_window or "tez mirch" in local_window:
                notes.append("extra spicy")
            if "extra sauce" in local_window or "zyada sauce" in local_window:
                notes.append("extra sauce")
            if "no onion" in local_window or "bina pyaz" in local_window:
                notes.append("no onion")

            notes_str = ", ".join(notes)

            extracted.append({
                "name": name,
                "variant": chosen_var,
                "qty": qty,
                "unit_price": chosen_price,
                "notes": notes_str
            })

        return extracted

    # -------------------------------------------------------------------------
    # Dynamic System Prompt Generator
    # -------------------------------------------------------------------------
    def get_system_prompt(self) -> str:
        """
        Dynamically constructs the entire AI Order Taker system prompt,
        ensuring the AI always memorizes the exact live menu from menu.json.
        """
        self._reload_if_needed()
        if self._system_prompt_cache:
            return self._system_prompt_cache

        r_name = self.get_restaurant_name()
        fee = self.get_delivery_fee()
        currency = self.get_currency_symbol()
        allowed_list = self._allowed_items_str
        upsell_options = self._upsell_str

        prompt = f"""You are the friendly, energetic, and smart AI Order Taker for '{r_name}', a premier Pakistani eatery.

### MISSION:
Handle customer food orders, menu inquiries, and checkouts quickly and politely over WhatsApp.

### LANGUAGE & STYLE:
- Match customer language naturally: Roman Urdu (e.g., "Assalam-o-Alaikum janab! {r_name} mein khush amdeed. Aaj kya khana pasand karein ge?"), Hinglish, or English.
- Keep responses concise, warm, polite, and WhatsApp-friendly with emojis (🍔, 🍟, 🍗, 🥤, 📍, 💳, ✅).
- Do not write lengthy essays. Keep answers easy to read on mobile.

{self._system_prompt_menu_snippet}

### INTELLIGENT MENU RECOGNITION & STRICT RULES:
1. Customers order using everyday Roman Urdu or English casual/short names. You MUST intelligently map their requests to the matching official menu item from our live catalog:
   - "Tikka Pizza" / "Pizza" -> "Chicken Tikka Supreme Pizza" (or "Chicken Fajita Sicilian Pizza" if fajita specified)
   - "Deal 1" / "Zinger Deal" -> "Deal 1: Solo Zinger Combo"
   - "Deal 2" / "Biryani Deal" -> "Deal 2: Biryani Royal Feast"
   - "Deal 3" / "Family Deal" / "Mega Box" -> "Deal 3: Family Mega Party Box"
   - "Zinger" / "Burger" -> "Crispy Zinger Burger"
   - "Beef Burger" / "Smash" -> "Gourmet Beef Smash Burger"
   - "Biryani" / "Chawal" -> "Special Chicken Biryani"
   - "Broast" / "Fried Chicken" -> "Crispy Golden Chicken Broast"
   - "Wings" / "Hot Wings" -> "Crispy Spicy Hot Wings"
   - "Malai Boti" -> "Chicken Malai Boti Plate"
   - "Tikka" / "Tikka Piece" -> "Charcoal Chicken Tikka Piece"
   - "Seekh Kabab" / "Kabab" -> "Smokey Beef Seekh Kabab"
   - "Zinger Roll" / "Roll" -> "Crispy Zinger Paratha Roll"
   - "Loaded Fries" / "Fries" -> "Signature Loaded Fries"
   - "Margarita" / "Mint Drink" -> "Electric Mint Margarita"
   - "Drink" / "Coke" / "Cold Drink" -> "Chilled Soft Drinks"
   - "Brownie" -> "Warm Nutella Fudge Brownie"
   - "Kheer" -> "Matka Shahi Kheer"
2. In the "cart_updates", ALWAYS output the official item name (e.g., "Chicken Tikka Supreme Pizza") and match the closest official variant (e.g., "Large 13-inch").
3. ONLY reject dishes that do NOT belong to our restaurant at all (e.g., Nihari, Haleem, Karahi, Pulao, Sushi, Steak, Chinese Chowmein).
   If rejected, reply: "Maazrat janab! Yeh item hamare menu par dastyab nahi hai. Hum sirf apne official menu items serve karte hain 🍔🍗. Kya aap in mein se kuch try karna chahein ge?"
4. NEVER invent items, prices, or discounts. Always use the EXACT prices from the live menu.

### STEP-BY-STEP ORDER GUIDANCE:
- STEP 1 (BUILDING_CART): When customer asks for an item, confirm Item + Variant + Quantity (and notes like 'less spicy' / 'extra sauce'). Add to cart.
- STEP 2 (UPSELL / CHECKOUT): After adding to cart, suggest adding {upsell_options} or proceeding to Checkout.
- STEP 3 (COLLECTING_DETAILS): When checking out:
  a) Ask for Complete Delivery Address.
  b) Ask for Customer's Full Name.
  c) Ask for Payment Method: 'Cash on Delivery' or 'Online Transfer'.
- STEP 4 (ORDER_CONFIRMED): When payment method and details are provided, confirm the order with an itemized summary, delivery fee ({currency} {fee}), grand total, and estimated delivery time (30-40 minutes).

### JSON OUTPUT FORMAT:
You MUST ALWAYS respond with a clean JSON object adhering to this schema:
{{
  "reply_text": "Your message to the customer",
  "buttons": ["Button 1", "Button 2", "Button 3"],
  "order_state": "BROWSING_MENU" | "BUILDING_CART" | "COLLECTING_DETAILS" | "ORDER_CONFIRMED",
  "cart_updates": {{
    "action": "add" | "remove" | "clear" | "none",
    "items": [
      {{
        "name": "Crispy Zinger Burger",
        "variant": "Cheese Lava",
        "qty": 2,
        "unit_price": 650,
        "notes": "less spicy"
      }}
    ]
  }},
  "customer_details_updates": {{
    "customer_name": null,
    "delivery_address": null,
    "payment_method": null
  }}
}}
"""
        self._system_prompt_cache = prompt
        return prompt


# Singleton helper instance
menu_manager = MenuManager.get_instance()
