import re
import json
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import os
import time


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = "google/gemma-4-31b-it:free"


def generate_cover_letter(job_description: str, resume: str) -> str:
    """
    Calls OpenRouter on-the-fly ONLY if Playwright detects a letter is required.
    """
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://n8n.io", 
        "X-Title": "hh.ru n8n Job Automation Bot"
    }

    prompt = f"""
        Ты — обычный человек, который помогает написать живое сопроводительное письмо. Никакого ИИ-стиля.

        Правила:
        1. Письмо — сплошной текст без списков, звездочек, тире, заголовков. Только один единый абзац.
        2. Формат:
        - Начинается строго с «Здравствуйте,» (без восклицательного знака)
        - Затем через пробел продолжается текст письма (одним абзацем)
        3. Запрещено использовать ЛЮБЫЕ имена, вымышленные подписи (например, «Сергей», «Алексей» и т.д.) или плейсхолдеры в скобках. Письмо должно заканчиваться точкой на последнем предложении, без подписи автора в конце.
        4. Никаких ИИ-фраз и шаблонов. Запрещены:
        - «рад возможности», «внимательно изучил требования», «команда профессионалов»
        - «давайте обсудим», «открыт к диалогу», «буду полезен», «уверен, что принесу пользу»
        - «синергия», «релевантный опыт», «компетенции»
        - «если интересно — напишите» или «буду рад ответить»
        - восклицательные знаки, смайлики, многоточия
        - местоимение «я» в каждом предложении
        - «ищу возможность», «хочу работать», «интересуюсь», «рад откликнуться»
        - «потому что», «так как» (в контексте объяснения своих желаний)
        - «разрабатывал backend», «настраивал CI/CD», «писал запросы» (замени на конкретные действия: «коммерческий опыт...», «автоматизировал...», «оптимизировал...»)
        - Любые имена, подписи, плейсхолдеры и контакты в конце. Письмо должно заканчиваться точкой на фразе о резюме.
        5. Пиши развернуто и по делу (строго 6–7 предложений):
        - Предложение 1: Конкретный коммерческий или профессиональный опыт в годах по ключевым требованиям из вакансии (если в резюме чуть меньше лет, округли в большую сторону под вакансию).
        - Предложение 2: Описание выполнения главной, самой крупной обязанности или задачи из требований вакансии.
        - Предложение 3: Измеримый рабочий результат, цифра или метрика из резюме, которая напрямую бьется с требованиями (например, «Увеличил...», «Сократил...», «Оптимизировал...», «Выполнил...»).
        - Предложение 4: Опыт работы со второстепенными, смежными инструментами или обязанностями из вакансии. (Если этого навыка нет в резюме, напиши скромно: «Пробовал настраивать...», «Немного работал с...», «Делал базовые вещи в...»).
        - Предложение 5: Опыт решения сопутствующих, организационных или отчетных задач, критичных для этой позиции. (Если этого навыка нет в резюме, напиши скромно: «Копался в...», «Немного занимался...»).
        - Предложение 6: Сопоставление своего опыта с самой сложной или специфической задачей из описания вакансии. (Если этого навыка нет в резюме, напиши скромно: «У вас указана сложная задача с... — как раз поверхностно сталкивался с аналогичным процессом.»).
        - Предложение 7: Финал строго такой: «Детали и полный стек расписал в резюме.»


        Описание вакансии:
        {job_description}

        Резюме кандидата:
        {resume}

        Пример хорошего письма:
        Здравствуйте, откликаюсь на вакансию бэкенд-разработчика. В резюме видно, что последние два года писал микросервисы на FastAPI и поднимал их в Docker с CI/CD на GitLab. У вас в описании похожие задачи. Посмотрите, пожалуйста, резюме — там детально расписан стек.

        Напиши только письмо — без подписей, без имен в конце, без пояснений, без кавычек, без лишних слов.
    """


    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }

    try:
        response = requests.post(OPENROUTER_URL, json=payload, headers=headers, timeout=20)
        if response.status_code == 200:
            ai_message = response.json()["choices"][0]["message"]["content"].strip()
            return ai_message
        else:
            print(f"OpenRouter Error Code {response.status_code}: {response.text}")
    except Exception as e:
        print(f"Failed to generate cover letter via OpenRouter: {e}")
    

    return "Здравствуйте! Меня заинтересовала ваша вакансия. Моё актуальное резюме прикреплено к отклику."
    


def create_selenium_session(cookie_file: str = "hh_cookies.json") -> webdriver.Chrome:
    """
    Initializes a headless Chromium instance
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (X11; Linux x86_64; rv:151.0) Gecko/20100101 Firefox/151.0")
    chrome_options.binary_location = "/usr/bin/chromium"

    service = Service(executable_path="/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        print("Initializing session environment at domain root...")
        driver.get("https://hh.ru")
        
        with open(cookie_file, 'r') as f:
            cookies = json.load(f)
            for cookie in cookies:
                if 'domain' in cookie and not cookie['domain'].startswith('.'):
                    cookie['domain'] = f".{cookie['domain']}"
                try:
                    driver.add_cookie(cookie)
                except Exception:
                    pass
        print("Successfully injected session cookies.")
        return driver

    except Exception as e:
        print(f"Failed to set up authenticated browser session: {str(e)}")
        try:
            driver.quit()
        except:
            pass
        raise e




def apply_to_job(driver, job_link: str, job_description: str, resume_title: str, resume: str) -> dict:
    """Automates applying to a HeadHunter vacancy with improved robustness."""
    
    match = re.search(r'/vacancy/(\d+)', job_link)
    if not match:
        return {"success": False, "reason": "Invalid job link configuration"}

    vacancy_id = match.group(1)
    status_log = {
        "vacancy_id": vacancy_id,
        "success": False,
        "generated_letter": "",
        "letter_sent": False,
        "reason": ""
    }

    print(f"Processing Vacancy ID: {vacancy_id}")

    try:
        driver.get(job_link)
        wait = WebDriverWait(driver, 12)

        # === Click main "Apply" button ===
        try:
            apply_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-qa="vacancy-response-link-top"]')))
            driver.execute_script("arguments[0].click();", apply_btn)
            print("Apply button clicked.")
        except TimeoutException:
            return {**status_log, "reason": "Apply button not found or not clickable"}

        # === Resume selection ===
        try:
            toggle_selector = 'div[class*="magritte-itemRight"]'
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, toggle_selector)))
                toggle_buttons = driver.find_elements(By.CSS_SELECTOR, toggle_selector)
                
                for btn in toggle_buttons:
                    if btn.is_displayed():
                        driver.execute_script("arguments[0].click();", btn)
                        print("The resume list has been successfully expanded.")
                        time.sleep(0.5)
                        break
            except Exception as e:
                print(f"Failed to click on the drop-down arrow: {e}")



            # Wait for the resume items to render
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-qa="resume-title"]')))
            
            resume_selected = False
            for card in driver.find_elements(By.CSS_SELECTOR, '[class*="magritte-card"]'):
                title_el = card.find_elements(By.CSS_SELECTOR, '[data-qa="resume-title"]')
                print(title_el)
                if title_el and resume_title.lower() in title_el[0].text.lower():
                    # Click the card to select it
                    driver.execute_script("arguments[0].click();", card)
                    print(f"Resume '{resume_title}' selected.")
                    resume_selected = True
                    time.sleep(0.5)  # Let the selection animation complete
                    break
            
            if not resume_selected:
                return {**status_log, "reason": f"Resume matching '{resume_title}' not found"}
            
    
            print("Collapsing the resume list to reveal the cover letter form...")    
            selector = '.magritte-itemRight___MG688_7-2-20'
            try:
                toggle_btn = driver.find_elements(By.CSS_SELECTOR, selector)
                for btn in toggle_btn:
                    if btn.is_displayed():
                        driver.execute_script("arguments[0].click();", btn)
                        print(f"Collapsed menu using selector: {selector}")
                        break
            except Exception:
                pass
            
        except Exception as e:
            print(f"Resume selection warning: {e} (possibly single resume)")


        # === Cover Letter ===
        cover_letter_field = None
        
        # Try to open cover letter field
        try:
            toggle = wait.until(EC.element_to_be_clickable((
                By.CSS_SELECTOR, 
                '[data-qa="vacancy-response-letter-toggle"], [data-qa="add-cover-letter"]'
            )))
            driver.execute_script("arguments[0].click();", toggle)
            time.sleep(0.8)
        except:
            pass  # Field might already be open

        # Find textarea
        try:
            print("Waiting for the active cover letter input field...")
            cover_letter_field = wait.until(EC.presence_of_element_located((
                By.CSS_SELECTOR, 
                '[data-qa="vacancy-response-popup-form-letter-input"], [data-qa*="letter-input"], textarea'
            )))
            
            # 1. Force scroll it into view and wait for all dropdown closing animations to completely stop
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", cover_letter_field)
            time.sleep(1.0)  # Essential delay to let the dropdown menu completely slide out of the way
            
            # 2. Initialize focus programmatically to unlock the element state
            driver.execute_script("arguments[0].focus();", cover_letter_field)
            driver.execute_script("arguments[0].click();", cover_letter_field)
            time.sleep(0.2)
            
            # 3. Generate the clean, professional text payload
            cover_letter = generate_cover_letter(job_description, resume_title)
            status_log["generated_letter"] = cover_letter
            
            # 4. Use JavaScript value-setting to completely bypass InvalidElementStateException
            # This acts like a clipboard paste, completely ignoring layout restrictions or read-only states
            driver.execute_script("arguments[0].value = arguments[1];", cover_letter_field, cover_letter)
            
            # 5. Dispatch native input events so HeadHunter's React/Vue framework detects that text was typed
            driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", cover_letter_field)
            driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", cover_letter_field)
            
            # 6. VERIFICATION STEP: Verify if the text actually appeared in the DOM
            current_value = driver.execute_script("return arguments[0].value;", cover_letter_field)
            
            if not current_value or current_value.strip() == "":
                print("JS injection failed or was wiped by framework. Attempting native fallback...")
                cover_letter_field.clear()
                cover_letter_field.send_keys(cover_letter)
                # Re-verify after native typing
                current_value = cover_letter_field.get_attribute('value')

            if current_value and current_value.strip() != "":
                status_log["letter_sent"] = True
                print("Cover letter successfully injected and validated.")
            else:
                raise ValueError("Textarea remains empty after both JS and native entry methods.")
            
        except TimeoutException:
            print("Cover letter field not found - continuing without it.")
        except Exception as fill_err:
            print(f"Bypassing cover letter insertion step due to execution failure: {str(fill_err)}")

  
        # === Submit ===
        time.sleep(1.2)  # Let DOM settle

        submit_button = None
        submit_selectors = [
            'button[data-qa="vacancy-response-submit-popup"]',
            '[data-qa="vacancy-response-submit-popup"]',
            'button.magritte-button_mode-primary',
            'button[type="submit"]',
        ]

        for selector in submit_selectors:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for el in elements:
                if el.is_displayed() and ("отклик" in el.text.lower() or el.get_attribute("data-qa") == "vacancy-response-submit-popup"):
                    submit_button = el
                    break
            if submit_button:
                break

        if not submit_button:
            try:
                submit_button = driver.find_element(By.XPATH, 
                    "//button[contains(translate(text(), 'ОТКЛИКНУТЬСЯ', 'откликнуться'), 'откликнуться')]")
            except:
                pass

        if submit_button:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_button)
            time.sleep(0.6)
            driver.execute_script("arguments[0].click();", submit_button)
            
            status_log["success"] = True
            status_log["reason"] = "Application submitted successfully!"
            print("Application submitted!")
        else:
            status_log["reason"] = "Could not find submit button"

    except Exception as e:
        status_log["reason"] = f"Unexpected error: {type(e).__name__}: {str(e)}"
        print(f"Error during application: {e}")

    return status_log