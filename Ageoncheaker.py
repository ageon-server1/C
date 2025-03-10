import telebot
import stripe
import random
import datetime
import logging
import uuid
import json
import os
from faker import Faker

# -------------------------------
# CONFIGURATION
# -------------------------------
TELEGRAM_TOKEN = '7559594108:AAErZfPKC7-QkwE8k9R_LgUxL5ql-DnR_-E'  # अपना Bot API key यहाँ डालें
bot = telebot.TeleBot(TELEGRAM_TOKEN)

stripe.api_key = "sk_test_tR3PYbcVNZZ796tH88S4VQ2u"  # अपना Stripe API key (Test Mode) यहाँ डालें

# Owner & Admin configuration
OWNER_ID = 6552242136  # अपने owner का Telegram ID यहाँ डालें
admin_ids = {}  # Owner को automatically admin बनाएं

# Pricing for paid plans (in dollars)
PRICING = {1: 1, 3: 2, 7: 4, 30: 7}

# -------------------------------
# File-based Database Filenames
# -------------------------------
USER_BALANCES_FILE = "user_balances.json"
USER_APPROVALS_FILE = "user_approvals.json"
APPROVAL_KEYS_FILE = "approval_keys.json"

# -------------------------------
# Logging Configuration
# -------------------------------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# -------------------------------
# Helper Functions for File-based DB
# -------------------------------
def load_json(filename):
    if not os.path.exists(filename):
        return {}
    with open(filename, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = {}
    return data

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, default=str, indent=4)

# -------------------------------
# Database Functions using Files
# -------------------------------
def get_user_balance(user_id):
    balances = load_json(USER_BALANCES_FILE)
    return float(balances.get(str(user_id), 0))

def update_user_balance(user_id, new_balance):
    balances = load_json(USER_BALANCES_FILE)
    balances[str(user_id)] = new_balance
    save_json(USER_BALANCES_FILE, balances)

def approve_user_in_db(user_id, valid_until):
    approvals = load_json(USER_APPROVALS_FILE)
    approvals[str(user_id)] = valid_until.isoformat()
    save_json(USER_APPROVALS_FILE, approvals)
    logging.info(f"User {user_id} approved until {valid_until}")

def is_user_approved(user_id):
    approvals = load_json(USER_APPROVALS_FILE)
    valid_until_str = approvals.get(str(user_id))
    if valid_until_str:
        valid_until = datetime.datetime.fromisoformat(valid_until_str)
        if valid_until > datetime.datetime.now():
            return True
    return False

def get_approval_keys():
    return load_json(APPROVAL_KEYS_FILE)

def update_approval_keys(keys):
    save_json(APPROVAL_KEYS_FILE, keys)

def is_user_admin(user_id):
    return user_id in admin_ids

# -------------------------------
# Rate Limiting for Free Commands (45 sec cooldown)
# -------------------------------
FREE_COOLDOWN = 45
last_message_time = {}

def free_rate_limit(func):
    def wrapper(message, *args, **kwargs):
        user_id = message.from_user.id
        now = datetime.datetime.now()
        if user_id in last_message_time:
            elapsed = (now - last_message_time[user_id]).total_seconds()
            if elapsed < FREE_COOLDOWN:
                wait_time = FREE_COOLDOWN - elapsed
                bot.reply_to(message, f"Free users can only use this command every {FREE_COOLDOWN} seconds. Please wait {int(wait_time)} seconds.")
                return
        last_message_time[user_id] = now
        return func(message, *args, **kwargs)
    return wrapper

# -------------------------------
# Luhn Algorithm & Card Generation Functions
# -------------------------------
def luhn_checksum(card_number):
    def digits_of(n):
        return [int(d) for d in str(n)]
    digits = digits_of(card_number)
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    total = sum(odd_digits)
    for d in even_digits:
        total += sum(digits_of(d * 2))
    return total % 10

def generate_card_number(bin_str, length=16):
    num_digits = length - len(bin_str) - 1  # Excluding check digit
    partial_number = bin_str + ''.join(str(random.randint(0, 9)) for _ in range(num_digits))
    for check_digit in range(10):
        candidate = partial_number + str(check_digit)
        if luhn_checksum(candidate) == 0:
            return candidate
    return None

def generate_expiry():
    current_year = datetime.datetime.now().year
    month = random.randint(1, 12)
    year = random.randint(current_year, current_year + 5)
    return f"{month:02d}/{year}"

def generate_cvv():
    return f"{random.randint(0, 999):03d}"

def generate_card_details(bin_str, count=1):
    cards = []
    for _ in range(count):
        card_number = generate_card_number(bin_str)
        expiry = generate_expiry()
        cvv = generate_cvv()
        cards.append({
            "card_number": card_number,
            "expiry": expiry,
            "cvv": cvv
        })
    return cards

# -------------------------------
# Random Address Generation using Faker
# -------------------------------
# Extensive dictionary mapping many country codes to Faker locale codes.
country_locales = {
    'us': 'en_US', 'ca': 'en_CA', 'uk': 'en_GB', 'au': 'en_AU', 'nz': 'en_NZ',
    'ie': 'en_IE', 'za': 'en_ZA', 'in': 'en_IN', 'de': 'de_DE', 'fr': 'fr_FR',
    'it': 'it_IT', 'es': 'es_ES', 'pt': 'pt_PT', 'br': 'pt_BR', 'nl': 'nl_NL',
    'be': 'nl_BE', 'ch': 'de_CH', 'at': 'de_AT', 'se': 'sv_SE', 'no': 'nb_NO',
    'dk': 'da_DK', 'fi': 'fi_FI', 'ru': 'ru_RU', 'ua': 'uk_UA', 'pl': 'pl_PL',
    'cs': 'cs_CZ', 'sk': 'sk_SK', 'hu': 'hu_HU', 'ro': 'ro_RO', 'bg': 'bg_BG',
    'gr': 'el_GR', 'tr': 'tr_TR', 'il': 'he_IL', 'ae': 'en_AE', 'sa': 'ar_SA',
    'eg': 'ar_EG', 'qa': 'ar_QA', 'kw': 'ar_KW', 'lb': 'ar_LB', 'ir': 'fa_IR',
    'jp': 'ja_JP', 'kr': 'ko_KR', 'cn': 'zh_CN', 'tw': 'zh_TW', 'hk': 'zh_HK',
    'sg': 'en_SG', 'my': 'en_MY', 'id': 'id_ID', 'th': 'th_TH', 'vn': 'vi_VN',
    'ph': 'en_PH', 'mx': 'es_MX', 'ar': 'es_AR', 'cl': 'es_CL', 'co': 'es_CO',
    'pe': 'es_PE', 've': 'es_VE', 'ng': 'en_NG', 'ke': 'en_KE', 'gh': 'en_GH',
    'et': 'am_ET', 'ma': 'ar_MA', 'dz': 'ar_DZ', 'tn': 'ar_TN', 'ci': 'fr_CI'
}

@bot.message_handler(commands=['address'])
def handle_address(message):
    try:
        # Expecting: /address <country_code>
        command_text = message.text.split(' ', 1)[1].strip().lower()
    except IndexError:
        bot.reply_to(message, "Please provide a country code. For example: /address us")
        return
    if command_text not in country_locales:
        valid_codes = ", ".join(sorted(country_locales.keys()))
        bot.reply_to(message, f"Invalid country code. Valid codes are: {valid_codes}")
        return
    fake = Faker(country_locales[command_text])
    address = fake.address()
    bot.reply_to(message, f"Random address for {command_text.upper()}:\n{address}")

# -------------------------------
# /start Command: Welcome Message
# -------------------------------
@bot.message_handler(commands=['start'])
def start_handler(message):
    user_name = message.from_user.first_name or "User"
    welcome_text = f"""🔥 **Welcome to AGEON CC CHECKER** 🔥

Hello {user_name},
I am **AGEON CC CHECKER**, your trusted bot for credit card validation, generation, charging & address generation.

🔹 **Features:**
• Validate Credit Cards (/chk)
• Generate Random Cards (/gen)
• Generate Random Addresses (/address)

🔹 **Restricted Commands (Approved/Admin Only):**
• Bulk Card Validation (/bulkchk)
• Bulk Card Generation (/bulkgen)
• Charge a Card ($2 charge) (/charge)

🔹 **Paid Plans:**
• 1 day  : $1
• 3 days : $2
• 7 days : $4
• 30 days: $7

Owner/Admin Commands:
• Add Admin with Balance (/addamin)
• Generate Approval Key (/genkey) – Usage: /genkey <duration> where duration is one of: 1day, 3day, 7day, 30day
• Redeem Approval Key (/redeem)

To generate a random address, use: /address <country_code> (e.g., /address us)

🚀 Send /help to see full command details.
"""
    bot.reply_to(message, welcome_text, parse_mode="Markdown")
    logging.info(f"Sent welcome message to user {message.from_user.id}")

# -------------------------------
# /help Command: Command Guide
# -------------------------------
@bot.message_handler(commands=['help'])
def help_handler(message):
    help_text = """📌 **AGEON CC CHECKER - Command Guide** 📌

🔹 **Free Commands (45 sec cooldown):**
• `/chk card_number|exp_month|exp_year|cvc`
   - Validate a single credit card.
   - Example: `/chk 4242424242424242|12|2028|123`

• `/gen BIN`
   - Generate 10 random valid cards from a BIN.
   - Example: `/gen 527912`

• `/address <country_code>`
   - Generate a random address for the specified country.
   - Example: `/address us`

🔹 **Restricted Commands (For Approved Users/Admins Only):**
• `/bulkchk`
   - Validate multiple cards (each card on a new line in format: card_number|exp_month|exp_year|cvc).
   - Example:
     ```
     /bulkchk
     4242424242424242|12|2028|123
     5555555555554444|11|2027|456
     ```

• `/bulkgen BIN|count`
   - Generate up to 100 cards from a BIN.
   - Example: `/bulkgen 527912|50`

• `/charge card_number|exp_month|exp_year|cvc`
   - Charge $2 on the given credit card.
   - Example: `/charge 4242424242424242|12|2028|123`

🔹 **Owner/Admin Commands:**
• `/addamin user_id|amount`
   - (Owner Only) Add a user as admin and set their balance.
   - Example: `/addamin 987654321|5`

• `/genkey duration`
   - (Admin Only) Generate an approval key for a paid plan.
   - Valid durations: 1day, 3day, 7day, 30day.
   - Example: `/genkey 7day`

• `/redeem key`
   - Redeem an approval key to get approved.
   - Example: `/redeem abcd1234efgh`

💡 **Note:**
- Free users have a 45 sec cooldown on /chk, /gen, and /address.
- /bulkchk, /bulkgen, and /charge are restricted to approved users or admins.
- This bot runs in test mode; use test data only.
- All transactions and operations are simulated.

🔰 Enjoy using AGEON CC CHECKER!
"""
    bot.reply_to(message, help_text, parse_mode="Markdown")
    logging.info(f"Sent help message to user {message.from_user.id}")

# -------------------------------
# /chk Command: Single Card Validation (Free Command)
# -------------------------------
@bot.message_handler(commands=['chk'])
@free_rate_limit
def chk_handler(message):
    try:
        command_text = message.text.split(' ', 1)[1]
        parts = command_text.split('|')
        if len(parts) != 4:
            bot.reply_to(message, "Invalid format.\nUse: /chk card_number|exp_month|exp_year|cvc")
            return
        card_number, exp_month, exp_year, cvc = parts
        exp_month = int(exp_month)
        exp_year = int(exp_year)
    except Exception as e:
        bot.reply_to(message, f"Error parsing input: {e}")
        logging.error(f"/chk parsing error: {e}")
        return

    try:
        token_response = stripe.Token.create(
            card={
                "number": card_number,
                "exp_month": exp_month,
                "exp_year": exp_year,
                "cvc": cvc,
            },
        )
        card_details = token_response.card
        details = (
            f"✅ Card Approved!\n"
            f"Brand: {card_details.get('brand', 'N/A')}\n"
            f"Last 4: {card_details.get('last4', 'N/A')}\n"
            f"Exp: {card_details.get('exp_month', 'N/A')}/{card_details.get('exp_year', 'N/A')}\n"
            f"Funding: {card_details.get('funding', 'N/A')}\n"
            f"Country: {card_details.get('country', 'N/A')}"
        )
        bot.reply_to(message, details)
        logging.info(f"/chk success: card ending with {card_details.get('last4', 'N/A')}")
    except stripe.error.CardError as e:
        err = e.error
        decline_reason = err.get('decline_code', 'N/A')
        bot.reply_to(message, f"❌ Card Declined!\nError: {err.get('message', 'No message')}\nDecline Code: {decline_reason}")
        logging.warning(f"/chk declined: {err.get('message')}")
    except Exception as e:
        bot.reply_to(message, f"Card validation failed: {e}")
        logging.error(f"/chk error: {e}")

# -------------------------------
# /gen Command: Generate 10 Cards from BIN (Free Command)
# -------------------------------
@bot.message_handler(commands=['gen'])
@free_rate_limit
def gen_handler(message):
    try:
        command_text = message.text.split(' ', 1)[1].strip()
        bin_str = command_text.split('|')[0].strip()
        cards = generate_card_details(bin_str, count=10)
        response_lines = [f"{card['card_number']} | Exp: {card['expiry']} | CVV: {card['cvv']}" for card in cards]
        bot.reply_to(message, "\n".join(response_lines))
        logging.info(f"/gen generated 10 cards for BIN {bin_str}")
    except Exception as e:
        bot.reply_to(message, f"Error: {e}")
        logging.error(f"/gen error: {e}")

# -------------------------------
# /bulkchk Command: Bulk Card Validation (Approved/Admin Only)
# -------------------------------
@bot.message_handler(commands=['bulkchk'])
def bulkchk_handler(message):
    if not (is_user_approved(message.from_user.id) or is_user_admin(message.from_user.id)):
        bot.reply_to(message, "This command is restricted to approved users or admins.")
        return
    try:
        command_text = message.text.split('\n', 1)[1]
        card_lines = command_text.strip().split('\n')
        if not card_lines:
            bot.reply_to(message, "Provide card details in format:\ncard_number|exp_month|exp_year|cvc")
            return
        responses = []
        for line in card_lines:
            line = line.strip()
            if not line:
                continue
            parts = line.split('|')
            if len(parts) != 4:
                responses.append(f"❌ Invalid format: {line}")
                continue
            card_number, exp_month, exp_year, cvc = parts
            try:
                exp_month = int(exp_month)
                exp_year = int(exp_year)
            except ValueError:
                responses.append(f"❌ Invalid month/year in: {line}")
                continue
            try:
                token_response = stripe.Token.create(
                    card={
                        "number": card_number,
                        "exp_month": exp_month,
                        "exp_year": exp_year,
                        "cvc": cvc,
                    },
                )
                card_details = token_response.card
                details = (
                    f"✅ Approved: {card_details.get('brand', 'N/A')} - ****{card_details.get('last4', 'N/A')}, "
                    f"Exp: {card_details.get('exp_month', 'N/A')}/{card_details.get('exp_year', 'N/A')}, "
                    f"Funding: {card_details.get('funding', 'N/A')}, Country: {card_details.get('country', 'N/A')}"
                )
                responses.append(details)
            except stripe.error.CardError as e:
                err = e.error
                decline_reason = err.get('decline_code', 'N/A')
                responses.append(f"❌ Declined: {err.get('message', 'No message')} (Code: {decline_reason})")
            except Exception as e:
                responses.append(f"❌ Error processing {line}: {e}")
        bot.reply_to(message, "\n".join(responses))
        logging.info(f"/bulkchk processed {len(card_lines)} lines")
    except Exception as e:
        bot.reply_to(message, f"Error: {e}")
        logging.error(f"/bulkchk error: {e}")

# -------------------------------
# /bulkgen Command: Generate Cards from BIN (Approved/Admin Only)
# -------------------------------
@bot.message_handler(commands=['bulkgen'])
def bulkgen_handler(message):
    if not (is_user_approved(message.from_user.id) or is_user_admin(message.from_user.id)):
        bot.reply_to(message, "This command is restricted to approved users or admins.")
        return
    try:
        command_text = message.text.split(' ', 1)[1].strip()
        parts = command_text.split('|')
        bin_str = parts[0].strip()
        count = 10
        if len(parts) > 1:
            count = int(parts[1].strip())
            if count > 100:
                count = 100
        cards = generate_card_details(bin_str, count=count)
        response_lines = [f"{card['card_number']} | Exp: {card['expiry']} | CVV: {card['cvv']}" for card in cards]
        bot.reply_to(message, "\n".join(response_lines))
        logging.info(f"/bulkgen generated {count} cards for BIN {bin_str}")
    except Exception as e:
        bot.reply_to(message, f"Error: {e}")
        logging.error(f"/bulkgen error: {e}")

# -------------------------------
# /charge Command: Charge $2 on a Card (Approved/Admin Only)
# -------------------------------
@bot.message_handler(commands=['charge'])
def charge_handler(message):
    if not (is_user_approved(message.from_user.id) or is_user_admin(message.from_user.id)):
        bot.reply_to(message, "This command is restricted to approved users or admins.")
        return
    try:
        command_text = message.text.split(' ', 1)[1]
        parts = command_text.split('|')
        if len(parts) != 4:
            bot.reply_to(message, "Invalid format.\nUse: /charge card_number|exp_month|exp_year|cvc")
            return
        card_number, exp_month, exp_year, cvc = parts
        exp_month = int(exp_month)
        exp_year = int(exp_year)
    except Exception as e:
        bot.reply_to(message, f"Error parsing input: {e}")
        logging.error(f"/charge parsing error: {e}")
        return
    try:
        token_response = stripe.Token.create(
            card={
                "number": card_number,
                "exp_month": exp_month,
                "exp_year": exp_year,
                "cvc": cvc,
            },
        )
        token_id = token_response.id
    except Exception as e:
        bot.reply_to(message, f"Card validation failed: {e}")
        logging.error(f"/charge token creation error: {e}")
        return
    try:
        charge = stripe.Charge.create(
            amount=200,  # $2 in cents
            currency="usd",
            source=token_id,
            description="Charge of $2 via AGEON CC CHECKER",
        )
        bot.reply_to(message, f"Charge successful! Charge ID: {charge.id}")
        logging.info(f"/charge successful, Charge ID: {charge.id}")
    except Exception as e:
        bot.reply_to(message, f"Charge failed: {e}")
        logging.error(f"/charge error: {e}")

# -------------------------------
# /addamin Command: Add Admin with Balance (Owner Only)
# -------------------------------
@bot.message_handler(commands=['addamin'])
def addamin_handler(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "Access denied. Only owner can add admins.")
        return
    try:
        command_text = message.text.split(' ', 1)[1].strip()
        parts = command_text.split('|')
        if len(parts) != 2:
            bot.reply_to(message, "Invalid format.\nUsage: /addamin user_id|amount")
            return
        target_user_id = int(parts[0].strip())
        amount = float(parts[1].strip())
    except Exception as e:
        bot.reply_to(message, f"Error parsing input: {e}")
        return
    admin_ids.add(target_user_id)
    current_balance = get_user_balance(target_user_id)
    new_balance = current_balance + amount
    update_user_balance(target_user_id, new_balance)
    bot.reply_to(message, f"User {target_user_id} added as admin with balance ${new_balance:.2f}")
    logging.info(f"/addamin: Added admin {target_user_id} with balance ${new_balance:.2f}")

# -------------------------------
# /genkey Command: Generate Approval Key (Admin Only)
# -------------------------------
@bot.message_handler(commands=['genkey'])
def genkey_handler(message):
    if not is_user_admin(message.from_user.id):
        bot.reply_to(message, "Access denied. This command is for admins only.")
        return
    try:
        # Expected format: /genkey <duration>
        # duration must be one of: 1day, 3day, 7day, 30day
        command_text = message.text.split(' ', 1)[1].strip().lower()
        valid_options = {"1day": 1, "3day": 3, "7day": 7, "30day": 30}
        if command_text not in valid_options:
            bot.reply_to(message, "Invalid duration. Use one of: 1day, 3day, 7day, 30day.")
            return
        days = valid_options[command_text]
        new_key = str(uuid.uuid4()).replace('-', '')[:12]
        keys = get_approval_keys()
        keys[new_key] = {
            "days": days,
            "redeemed": False,
            "generated_by": message.from_user.id,
            "generated_at": datetime.datetime.now().isoformat()
        }
        update_approval_keys(keys)
        bot.reply_to(message, f"Approval key for {days} day(s) generated: {new_key}")
        logging.info(f"/genkey: Key {new_key} for {days} days generated by admin {message.from_user.id}")
    except Exception as e:
        bot.reply_to(message, f"Error generating key: {e}")
        logging.error(f"/genkey error: {e}")

# -------------------------------
# /redeem Command: Redeem Approval Key (User)
# -------------------------------
@bot.message_handler(commands=['redeem'])
def redeem_handler(message):
    try:
        command_text = message.text.split(' ', 1)[1].strip()
        key_to_redeem = command_text
        keys = get_approval_keys()
        if key_to_redeem not in keys:
            bot.reply_to(message, "Invalid key.")
            return
        key_info = keys[key_to_redeem]
        if key_info["redeemed"]:
            bot.reply_to(message, "This key has already been redeemed.")
            return
        days = key_info["days"]
        valid_until = datetime.datetime.now() + datetime.timedelta(days=days)
        approve_user_in_db(message.from_user.id, valid_until)
        key_info["redeemed"] = True
        key_info["redeemed_by"] = message.from_user.id
        key_info["redeemed_at"] = datetime.datetime.now().isoformat()
        keys[key_to_redeem] = key_info
        update_approval_keys(keys)
        bot.reply_to(message, f"Key redeemed! You are approved for {days} day(s) until {valid_until}.")
        logging.info(f"/redeem: User {message.from_user.id} redeemed key {key_to_redeem} for {days} days.")
    except Exception as e:
        bot.reply_to(message, f"Error redeeming key: {e}")
        logging.error(f"/redeem error: {e}")

# -------------------------------
# Bot Polling Start
# -------------------------------
if __name__ == "__main__":
    logging.info("AGEON CC CHECKER bot started.")
    bot.polling(none_stop=True)
