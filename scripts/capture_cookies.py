from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import json


def save_cookies(driver, cookie_file="hh_cookies.json"):
    link = "https://hh.ru"
    target_url = link.strip().rstrip('/')
    current_url = driver.current_url.strip().rstrip('/')

    if current_url == target_url:
        print(f"Already on page: {link}. Skipping navigation.")
    else:
        driver.get(link)

    wait = WebDriverWait(driver, 300)

    wait.until(
        EC.any_of(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-qa='profileAndResumes-button']")),
            # Fallback URL detection
            EC.url_contains("hh.ru/applicant")
        )
    )
    cookies = driver.get_cookies()
    with open(cookie_file, "w", encoding="utf-8") as file:
        json.dump(cookies, file)


def create_driver():
    # Define browsers to try in order of preference
    browsers = [
        ('Firefox', webdriver.Firefox),
        ('Chrome', webdriver.Chrome),
        ('Edge', webdriver.Edge)
    ]
    
    for name, browser_driver in browsers:
        try:
            print(False, f"Checking for {name}...")
            # Selenium Manager automatically finds the installed binary
            driver = browser_driver()
            print(f"Successfully launched {name}!")
            return driver
        except WebDriverException:
            print(f"{name} is not installed or available.")
            continue
            
    raise RuntimeError("No supported browsers (Chrome, Firefox, Edge) were found on this system.")

if __name__ == "__main__":
    driver = None
    try:
        driver = create_driver()
        driver.maximize_window()

        save_cookies(driver)
    finally:
        if driver is not None:
            driver.quit()
