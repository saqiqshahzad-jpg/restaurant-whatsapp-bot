import sys
import os

# Set working directory to backend
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import (
    add_item_to_cart,
    calculate_cart_totals,
    is_valid_delivery_address,
    is_valid_customer_name,
    process_customer_message,
    reset_restaurant_session,
    OrderState
)
from language_helper import (
    LANGUAGES_CONFIG,
    get_template,
    get_buttons,
    normalize_lang,
    detect_foreign_language
)

def test_bug_1_multilingual_lock():
    print("\n--- TEST 1: Multilingual Lock (15 Languages) ---")
    test_phone = "+929990001111"
    reset_restaurant_session(test_phone)

    # All 15 languages check
    assert len(LANGUAGES_CONFIG) == 15, f"Expected 15 languages, got {len(LANGUAGES_CONFIG)}"
    for lang_key in LANGUAGES_CONFIG:
        off = get_template("off_topic", lang=lang_key)
        assert len(off) > 10, f"Off-topic template missing or empty for {lang_key}"
        welcome = get_template("locked_welcome", lang=lang_key)
        assert len(welcome) > 10, f"Welcome template missing or empty for {lang_key}"
        pay_btns = get_buttons("payment", lang=lang_key)
        assert len(pay_btns) == 2, f"Payment buttons missing for {lang_key}"
        for b in pay_btns:
            assert len(b) <= 20, f"Button title too long (>20 chars): {b}"

    # Simulate switching to English
    res1 = process_customer_message(test_phone, "hello, can I order?")
    assert "English" in res1["reply_text"] or res1.get("buttons")

    res2 = process_customer_message(test_phone, "1")
    assert res2.get("current_language") == "English"
    assert "English locked in" in res2["reply_text"]

    # Now ask "do you have chinese?" in English
    res3 = process_customer_message(test_phone, "do you have chinese?")
    print("Response to 'do you have chinese?':", res3["reply_text"][:100])
    # Must NOT have Roman Urdu words like "Arey ustaad, Zaiqa Grill mein sirf desi khana hai!"
    assert "Arey ustaad" not in res3["reply_text"]
    assert "Hey foodie" in res3["reply_text"] or "authentic" in res3["reply_text"].lower() or "delicacies" in res3["reply_text"].lower()
    print("✅ Bug 1 Verified: English lock preserved, no Roman Urdu fallback!")

def test_bug_2_duplicate_biryani_refinement():
    print("\n--- TEST 2: Duplicate Biryani Bug (Variant Refinement) ---")
    cart = calculate_cart_totals({})

    # 1. User picks Special Chicken Biryani with default Single variant
    cart = add_item_to_cart(cart, "Special Chicken Biryani", "Single", 1, 400)
    assert len(cart["items"]) == 1
    assert cart["items"][0]["variant"] == "Single"
    assert cart["subtotal"] == 400

    # 2. Bot asks "mild ya spicy?" and user selects "Single Spicy"
    cart = add_item_to_cart(cart, "Special Chicken Biryani", "Single Spicy", 1, 400)
    
    # Must STILL be 1 item with variant updated to "Single Spicy", NOT 2 items!
    assert len(cart["items"]) == 1, f"Expected 1 item, got {len(cart['items'])}: {cart['items']}"
    assert cart["items"][0]["variant"] == "Single Spicy"
    assert cart["items"][0]["qty"] == 1
    assert cart["subtotal"] == 400
    assert cart["grand_total"] == 550  # 400 + 150 delivery
    print("✅ Bug 2 Verified: Variant updated to Single Spicy without duplicating Biryani!")

def test_bug_3_address_and_name_validation_and_no_buttons():
    print("\n--- TEST 3: Address & Name Validation & Strictly NO Buttons ---")
    test_phone = "+929990002222"
    reset_restaurant_session(test_phone)

    # 1. Validator tests
    assert not is_valid_delivery_address("Continue")
    assert not is_valid_delivery_address("btn_continue")
    assert not is_valid_delivery_address("ok")
    assert not is_valid_delivery_address("123")
    assert is_valid_delivery_address("Flat no 22, F-1, Islamabad")

    assert not is_valid_customer_name("Continue")
    assert not is_valid_customer_name("btn_continue")
    assert not is_valid_customer_name("123")
    assert is_valid_customer_name("Qamar")

    # 2. Simulated order flow
    # Add food
    process_customer_message(test_phone, "1 Special Chicken Biryani")
    
    # Trigger checkout
    res_checkout = process_customer_message(test_phone, "Checkout", btn_id="btn_checkout")
    assert res_checkout["order_state"] == OrderState.COLLECTING_DETAILS
    assert res_checkout["buttons"] == [], f"Expected 0 buttons for address request, got {res_checkout['buttons']}"

    # User clicks dummy "Continue" or sends "Continue"
    res_invalid_addr = process_customer_message(test_phone, "Continue", btn_id="btn_continue")
    assert res_invalid_addr["order_state"] == OrderState.COLLECTING_DETAILS
    assert res_invalid_addr["buttons"] == [], f"Expected 0 buttons on invalid address reprompt, got {res_invalid_addr['buttons']}"
    assert "helicopter" in res_invalid_addr["reply_text"].lower() or "address" in res_invalid_addr["reply_text"].lower()

    # User sends real address
    res_valid_addr = process_customer_message(test_phone, "Flat no 22, F-1, Islamabad")
    assert res_valid_addr["order_state"] == OrderState.COLLECTING_DETAILS
    assert res_valid_addr["buttons"] == [], f"Expected 0 buttons for name request, got {res_valid_addr['buttons']}"
    assert "naam" in res_valid_addr["reply_text"].lower() or "name" in res_valid_addr["reply_text"].lower()

    # User clicks dummy "Continue" for name
    res_invalid_name = process_customer_message(test_phone, "Continue", btn_id="btn_continue")
    assert res_invalid_name["order_state"] == OrderState.COLLECTING_DETAILS
    assert res_invalid_name["buttons"] == [], f"Expected 0 buttons on invalid name reprompt, got {res_invalid_name['buttons']}"

    # User sends real name
    res_valid_name = process_customer_message(test_phone, "Qamar")
    assert res_valid_name["order_state"] == OrderState.COLLECTING_DETAILS
    # NOW buttons must appear for payment method!
    assert len(res_valid_name["buttons"]) == 2
    assert "Cash on Delivery" in res_valid_name["buttons"][0]
    print("✅ Bug 3 Verified: No buttons for address/name, funny persuasion on invalid text, payment buttons provided!")

def test_bug_4_cart_preservation_after_confirmation():
    print("\n--- TEST 4: Cart Preservation Post-Confirmation & Tracking ---")
    test_phone = "+929990003333"
    reset_restaurant_session(test_phone)

    # Complete order flow
    process_customer_message(test_phone, "1 Crispy Zinger Burger")
    process_customer_message(test_phone, "Checkout", btn_id="btn_checkout")
    process_customer_message(test_phone, "House 14, Street 9, F-10, Islamabad")
    process_customer_message(test_phone, "Daniyal Khan")
    res_sum = process_customer_message(test_phone, "Cash on Delivery", btn_id="btn_cod")
    assert "Order Summary" in res_sum["reply_text"]

    # Confirm order
    res_conf = process_customer_message(test_phone, "Haan, Confirm Karein", btn_id="btn_confirm")
    assert res_conf["order_state"] == OrderState.ORDER_CONFIRMED
    assert "ORDER CONFIRMED" in res_conf["reply_text"]
    assert "Track Order 🛵" in res_conf["buttons"]

    # User asks: "mera cart kya hai?"
    res_track = process_customer_message(test_phone, "mera cart kya hai?")
    print("Reply to 'mera cart kya hai?':", res_track["reply_text"][:100])
    assert "bilkul khali hai" not in res_track["reply_text"]
    assert "Crispy Zinger" in res_track["reply_text"]
    assert "ORD-" in res_track["reply_text"]
    assert "Track Order 🛵" in res_track["buttons"]

    # User clicks "Naya Order 🍔"
    res_new = process_customer_message(test_phone, "Naya Order", btn_id="btn_naya_order_🍔")
    assert res_new["order_state"] == OrderState.BROWSING_MENU
    assert res_new["customer_cart"]["items"] == []
    print("✅ Bug 4 Verified: Cart preserved after confirmation, tracking works, new order cleanly starts fresh!")

if __name__ == "__main__":
    test_bug_1_multilingual_lock()
    test_bug_2_duplicate_biryani_refinement()
    test_bug_3_address_and_name_validation_and_no_buttons()
    test_bug_4_cart_preservation_after_confirmation()
    print("\n=======================================================")
    print("🎉 ALL 4 CRITICAL BUGS ARE 100% FIXED AND VERIFIED!")
    print("=======================================================\n")

