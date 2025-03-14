import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

# 🛠 Function to Generate a Valid Test Card Number (Luhn Algorithm)
def generate_test_card(bin_str, total_length=16):
    digits_to_generate = total_length - len(bin_str) - 1
    partial_number = bin_str + ''.join(str(random.randint(0, 9)) for _ in range(digits_to_generate))

    def luhn_checksum(number):
        digits = [int(d) for d in number]
        for i in range(len(digits)-1, -1, -2):
            digits[i] *= 2
            if digits[i] > 9:
                digits[i] -= 9
        return sum(digits) % 10

    check_digit = (10 - luhn_checksum(partial_number + "0")) % 10
    return partial_number + str(check_digit)

# 🏦 Example: Stripe Test BIN (Visa Test BIN 424242)
test_bin = "4900700344884"
test_card_number = generate_test_card(test_bin)
print(f"Generated Test Card: {test_card_number}")

# 🚀 Chrome Headless Mode for VPS
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")

# 🏗 Setup Chrome WebDriver
service = Service("/usr/local/bin/chromedriver")
driver = webdriver.Chrome(service=service, options=chrome_options)

# 🌍 Open Stripe Test Checkout Page (Replace with Your URL)
checkout_url = "https://payments.hostinger.com/account/131/token/03f45dff-d970-474a-858d-7a4398221f29?locale=en_GB"
driver.get(checkout_url)
time.sleep(3)  # Wait for page to load

# 🔹 Find and Fill Card Number Field
try:
    card_number_field = driver.find_element(By.NAME, "cardnumber")
    card_number_field.send_keys(test_card_number)

    # 🔹 Fill Expiry Date (Use Stripe Test Date)
    expiry_field = driver.find_element(By.NAME, "exp-date")
    expiry_field.send_keys("12/34")

    # 🔹 Fill CVC (Use Test CVC)
    cvc_field = driver.find_element(By.NAME, "cvc")
    cvc_field.send_keys("123")

    # 🔹 Click Pay/Submit Button
    pay_button = driver.find_element(By.XPATH, "//button[contains(text(),'Pay')]")
    pay_button.click()
    time.sleep(5)

    print("✅ Payment Test Successfully Triggered")

except Exception as e:
    print(f"❌ Error: {e}")

finally:
    driver.quit()
