import os
import sys
import json
import time

# Ensure Windows terminal supports UTF-8 characters and emojis
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add backend directory to sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from main import (
    process_customer_message,
    reset_restaurant_session,
    get_restaurant_session,
    verify_supabase_tables,
    RESTAURANT_NAME,
    DELIVERY_FEE,
    format_menu_text
)

# Terminal ANSI Color codes
GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"

TEST_PHONE = "+923001112233"
DEFAULT_RESTAURANT_ID = "default_restaurant"

def print_banner():
    banner = f"""
{CYAN}================================================================================{RESET}
{BOLD}{GREEN}🍔 {RESTAURANT_NAME.upper()} - LOCAL INTERACTIVE BOT TESTER 🍟{RESET}
{CYAN}================================================================================{RESET}
{YELLOW}Simulating WhatsApp User:{RESET} {BOLD}{TEST_PHONE}{RESET}
{YELLOW}Available Commands:{RESET}
  {BOLD}/reset{RESET}   - Wipe test session and start completely fresh
  {BOLD}/cart{RESET}    - Print current live customer_cart JSON
  {BOLD}/menu{RESET}    - Show restaurant food menu
  {BOLD}/status{RESET}  - Check Supabase database connectivity
  {BOLD}/help{RESET}    - Show this help banner
  {BOLD}/exit{RESET}    - Exit simulator
{CYAN}--------------------------------------------------------------------------------{RESET}
{MAGENTA}Tip: When buttons are shown (e.g. [1], [2]), type the number or button text!{RESET}
{CYAN}================================================================================{RESET}
"""
    print(banner)

def check_supabase():
    print(f"\n{YELLOW}🔍 Verifying Supabase connection and tables...{RESET}")
    status = verify_supabase_tables()
    tables = status.get("tables", {})
    all_ok = True
    for table_name, state in tables.items():
        if "ONLINE" in str(state):
            print(f"  ✅ Table {BOLD}{table_name}{RESET}: {GREEN}{state}{RESET}")
        else:
            print(f"  ⚠️ Table {BOLD}{table_name}{RESET}: {YELLOW}{state}{RESET}")
            all_ok = False

    if all_ok:
        print(f"{GREEN}✨ Supabase connection verified! Tables are active.{RESET}\n")
    else:
        print(f"{CYAN}ℹ️ Note: If Supabase has RLS enabled, local persistent cache handles sessions seamlessly.{RESET}\n")

def display_turn(result: dict):
    reply_text = result.get("reply_text", "")
    buttons = result.get("buttons", [])
    order_state = result.get("order_state", "BROWSING_MENU")
    cart = result.get("customer_cart", {})

    print(f"\n{CYAN}============================= [ BOT RESPONSE ] ============================={RESET}")
    print(f"\n{BOLD}{GREEN}🤖 Bot Reply:{RESET}")
    print(f"{reply_text}\n")

    if buttons:
        print(f"{BOLD}{MAGENTA}🔘 Interactive Buttons:{RESET}")
        btn_display = []
        for i, b in enumerate(buttons, 1):
            btn_display.append(f"{BOLD}[{i}]{RESET} {b}")
        print("   " + "   ".join(btn_display) + "\n")

    print(f"{BOLD}{YELLOW}📊 Order State:{RESET} {BOLD}{order_state}{RESET}")

    print(f"\n{BOLD}{CYAN}🛒 Live customer_cart JSON:{RESET}")
    cart_json_str = json.dumps(cart, indent=2, ensure_ascii=False)
    print(f"{cart_json_str}")
    print(f"{CYAN}============================================================================{RESET}\n")

def main():
    print_banner()

    # Instant welcoming start without initial blocking network call
    session = get_restaurant_session(TEST_PHONE, DEFAULT_RESTAURANT_ID)
    welcome_result = {
        "reply_text": format_menu_text(),
        "buttons": ["Crispy Zinger 🍔", "Chicken Biryani 🍗", "Loaded Fries 🍟"],
        "order_state": session.get("order_state", "BROWSING_MENU"),
        "customer_cart": session.get("customer_cart", {})
    }
    last_buttons = welcome_result["buttons"]
    display_turn(welcome_result)

    while True:
        try:
            prompt_str = f"{BOLD}{YELLOW}Customer ({TEST_PHONE}) > {RESET}"
            user_input = input(prompt_str).strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n\n{GREEN}Exiting simulator. Goodbye! 👋{RESET}")
            break

        if not user_input:
            continue

        cmd = user_input.lower()

        if cmd in ["/exit", "exit", "quit", "q"]:
            print(f"\n{GREEN}Exiting simulator. Have a great day! 👋{RESET}")
            break

        if cmd == "/help":
            print_banner()
            continue

        if cmd == "/status":
            check_supabase()
            continue

        if cmd == "/menu":
            user_input = "menu"

        if cmd == "/cart":
            session = get_restaurant_session(TEST_PHONE, DEFAULT_RESTAURANT_ID)
            cart = session.get("customer_cart", {})
            print(f"\n{BOLD}{CYAN}🛒 Current customer_cart:{RESET}")
            print(json.dumps(cart, indent=2, ensure_ascii=False))
            print()
            continue

        btn_id = None
        # Handle button number shortcuts (e.g. "1", "2", "3")
        if user_input.isdigit() and last_buttons:
            idx = int(user_input) - 1
            if 0 <= idx < len(last_buttons):
                selected_btn = last_buttons[idx]
                print(f"{MAGENTA}[Clicked Button {user_input}: {selected_btn}]{RESET}")
                user_input = selected_btn
                btn_id = f"btn_{idx+1}"

        # Process the message
        print(f"{YELLOW}⏳ Bot is thinking & updating cart...{RESET}")
        t0 = time.time()
        result = process_customer_message(
            phone=TEST_PHONE,
            incoming_message=user_input,
            btn_id=btn_id,
            restaurant_id=DEFAULT_RESTAURANT_ID
        )
        elapsed = time.time() - t0

        last_buttons = result.get("buttons", [])
        display_turn(result)
        print(f"{MAGENTA}⏱️ Response time: {elapsed:.2f}s{RESET}\n")

if __name__ == "__main__":
    main()
