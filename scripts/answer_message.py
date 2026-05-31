from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import time
import os
import requests
from get_profile_data import *
from capture_cookies import create_driver


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = "google/gemma-4-31b-it:free"


def create_selenium_session(cookie_file="hh_cookies.json"):
    driver = create_driver()
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


def generate_message(chat_history: list[str], resume: str) -> str:
    """
    Calls OpenRouter to formulate a context-aware response based on the
    previous chat history and the candidate's resume.
    """
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://n8n.io", 
        "X-Title": "hh.ru n8n Job Automation Bot"
    }

    # Format the sequential chat log cleanly for the prompt
    formatted_chat = "\n".join([f"- {msg}" for msg in chat_history])

    prompt = f"""
    Вы выступаете в роли кандидата, общающегося с HR-менеджером на платформе hh.ru.
    Ваша задача — проанализировать историю переписки и резюме кандидата, а затем написать профессиональный, вежливый и краткий ответ на последнее сообщение работодателя от первого лица (я, мне, мой).

    История переписки (от старых сообщений к новым):
    {formatted_chat}

    Резюме кандидата:
    {resume}

    Правила:
    1. Пишите ответ на русском языке.
    2. Будьте вежливы, профессиональны и кратки (не более 3-4 предложений).
    3. Отвечайте строго на вопросы из последнего сообщения, если они есть.
    4. Если какого-то конкретного навыка или технологии из вопроса нет в резюме, не отказывайте прямо. Напишите скромно и обтекаемо в разговорной форме: «Пробовал настраивать...», «Немного работал с...» или «Делал базовые вещи в...».
    5. Если для ответа обязательно требуется опыт, которого нет в резюме, аккуратно придумайте ЕСТЕСТВЕННЫЙ, ПРОСТОЙ и РЕАЛИСТИЧНЫЙ опыт. Пишите его от лица живого человека, без заумных фраз и канцеляризмов (например: "сталкивался с этим на одном из прошлых проектов, базовая логика понятна").
    6. ВАЖНО: Не пишите текст ответа и выведите ровно одно слово SKIP в следующих случаях:
       - Если последнее сообщение в переписке отправлено ВАМИ (кандидатом), а не HR-менеджером.
       - Если последнее сообщение от HR является просто уведомлением, вежливым завершением разговора или автоматическим шаблоном, который НЕ требует ответа (например: "Мы рассмотрим ваше резюме", "Спасибо, хорошего дня", "Передала коллегам").
    7. Выдайте ТОЛЬКО текст сообщения для отправки (или слово SKIP). Без вводных фраз вроде "Вот ваш ответ:" или кавычек.
    """

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.6
    }

    try:
        response = requests.post(OPENROUTER_URL, json=payload, headers=headers, timeout=20)
        if response.status_code == 200:
            ai_message = response.json()["choices"][0]["message"]["content"].strip()
            return ai_message
        else:
            print(f"OpenRouter Error Code {response.status_code}: {response.text}")
    except Exception as e:
        print(f"Failed to generate automated response via OpenRouter: {e}")
    
    return "SKIP"




def determine_what_resume_was_applied_with(session, driver, chat_link) -> dict:
    """
    Extracts resume title and profile text by handling the new browser tab 
    spawned when clicking the applicant's resume link.
    """
    wait = WebDriverWait(driver, 8)
    resume_payload = {"resume_title": "", "resume_text": ""}
    
    base_chat_link = chat_link if chat_link else driver.current_url
    participants_url = base_chat_link.rstrip('/') + "/participants"
    print(f"-> Moving to participants dashboard view: {participants_url}")

    # Track our primary window handle so we can always return to it
    main_window_handle = driver.current_window_handle

    try:
        try:
            driver.switch_to.default_content()
        except:
            pass
            
        driver.get(participants_url)
        time.sleep(1.5)
        
        # Handle unexpected login redirects by synchronizing cookies
        if "account/login" in driver.current_url:
            print("⚠️ Auth Drop Found! Injecting active cookies into WebDriver context...")
            session_cookies = session.cookies.get_dict()
            for cookie_name, cookie_value in session_cookies.items():
                try:
                    driver.add_cookie({
                        'name': cookie_name,
                        'value': cookie_value,
                        'domain': '.hh.ru'
                    })
                except:
                    pass
            driver.get(participants_url)
            time.sleep(2)

        resume_arrow_selector = "[data-qa='open-applicant-resume'], button[data-qa='participant']"
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, resume_arrow_selector)))
        
        # Capture the list of open tabs *before* clicking
        old_handles = driver.window_handles

        try:
            target_arrow = driver.find_element(By.CSS_SELECTOR, "[data-qa='open-applicant-resume']")
            print("🎯 Clicking the resume arrow link (spawns new tab)...")
            driver.execute_script("arguments[0].click();", target_arrow)
        except:
            target_cell = driver.find_element(By.CSS_SELECTOR, "button[data-qa='participant']")
            print("🎯 Target arrow missing. Clicking general participant cell...")
            driver.execute_script("arguments[0].click();", target_cell)
            
        # 1. Wait for the new browser tab handle to appear in the system
        print("⏳ Waiting for the new browser tab to spawn...")
        new_tab_opened = False
        for _ in range(5):
            time.sleep(1)
            if len(driver.window_handles) > len(old_handles):
                new_tab_opened = True
                break

        if new_tab_opened:
            # 2. Switch focus explicitly to the newly spawned tab (always the last handle)
            new_window_handle = driver.window_handles[-1]
            driver.switch_to.window(new_window_handle)
            print(f"🌐 Switched to new tab context. Current URL: {driver.current_url}")
            
            # Wait up to 5 seconds for the resume profile page text content to load
            for _ in range(5):
                if "resume" in driver.current_url:
                    break
                time.sleep(1)

            resume_link = driver.current_url
            print(f"🎯 Discovered underlying active resume destination link: {resume_link}")
            
            # 3. Process the backend API retrieval data while focused on the new link
            if "resume" in resume_link:
                resume_data = process_resume_data(session, resume_link)
                if resume_data:
                    resume_payload["resume_text"] = resume_data.get("resume_text", "")
                    resume_payload["resume_title"] = resume_data.get("resume_title", "")
                    print(f"✅ Metadata compiled successfully -> Title: '{resume_payload['title']}'")
            else:
                print("⚠️ New tab URL did not resolve to a standard resume endpoint.")

            # 4. Clean up: Close the newly opened resume tab to prevent memory leaks
            print("🧹 Closing the temporary resume tab...")
            driver.close()
        else:
            print("❌ Failure: No new browser tab detected within timeout constraints.")

    except Exception as e:
        print(f"❌ Automation runtime error inside participant selection frame: {e}")
        
    finally:
        # --- CRITICAL RECOVERY GUARANTEE ---
        # Explicitly pivot the driver focus back to the master chat loop tab window
        print("🔄 Returning driver window focus to the primary workspace thread...")
        try:
            driver.switch_to.window(main_window_handle)
        except:
            # Emergency recovery: if the main handle was lost, bind to the first available window
            if driver.window_handles:
                driver.switch_to.window(driver.window_handles[0])
                
        if "chat" not in driver.current_url or driver.current_url != base_chat_link:
            print(f"🔄 Restoration Guard: Resetting primary tab link state to: {base_chat_link}")
            driver.get(base_chat_link)
            time.sleep(2)
        
    return resume_payload



def auto_answer_hh(session, driver):
    driver.get("https://hh.ru/chat")
    all_extracted_messages = []
    chat_cells_selector = "a[data-qa^='chatik-open-chat-']"
    # Extract all conversation anchor rows
    chat_cells = driver.find_elements(By.CSS_SELECTOR, chat_cells_selector)
    print(f"Success! Found {len(chat_cells)} chats available to process inside the iframe.")

    for index in range(len(chat_cells)):
        try:
            # Re-fetch elements within the active iframe context to prevent stale references
            current_cells = driver.find_elements(By.CSS_SELECTOR, chat_cells_selector)
            if index >= len(current_cells):
                break
                
            current_cell = current_cells[index]
            
            # Extract names safely using text splits or partial class wildcards
            try:
                vacancy_title = current_cell.find_element(By.CSS_SELECTOR, "[class*='title--']").text
            except:
                vacancy_title = "Unknown Position"
                
            try:
                company_name = current_cell.find_element(By.CSS_SELECTOR, "[class*='subtitle--']").text
            except:
                company_name = "Unknown Company"
            
            # Fast-skip rejections to optimize workflow execution speed
            try:
                last_msg_el = current_cell.find_element(By.CSS_SELECTOR, "[class*='last-message--']")
                if "Отказ" in last_msg_el.text:
                    print(f"Skipping chat {index + 1}: {vacancy_title} ({company_name}) -> Reason: Отказ")
                    continue
            except:
                pass

            print(f"\nOpening conversation {index + 1}: {vacancy_title} ({company_name})")
            driver.execute_script("arguments[0].click();", current_cell)
            
            # Wait for the corresponding chat body history to sync
            print("Fetching dialogue timeline text...")
            time.sleep(2)  
            
            # Scrape active text bubbles inside the current open thread box
            message_elements = driver.find_elements(By.CSS_SELECTOR, "[data-qa='chat-message-text'], [class*='message--']")
            chat_history = [msg.text for msg in message_elements if msg.text.strip()]
            
            print(f"Extracted {len(chat_history)} messages.")

            chat_link = driver.current_url
            resume_data = determine_what_resume_was_applied_with(session, driver, chat_link)
            resume_title = resume_data["resume_title"]
            resume_text = resume_data["resume_text"]
            print(f"Resume {resume_title} fetched")

            # --- GENERATE AND SEND THE AUTOMATED MESSAGE ---
            if chat_history:
                while True:
                    print("Generating automated response via AI...")
                    reply_text = generate_message(chat_history, resume_text)
                    
                    # Check if the AI decided that no response is necessary
                    if reply_text.strip().upper() == "SKIP":
                        print("Skipping submission: Last HR message does not require a reply.")
                        break
                    elif reply_text:
                        print(f"Prepared Message:\n\"{reply_text}\"")
                        
                        # Target hh.ru chat text input element
                        input_area = driver.find_element(By.CSS_SELECTOR, "textarea[data-qa='chatik-new-message-text']")
                        input_area.clear()
                        input_area.send_keys(reply_text)
                        time.sleep(1)

                        last_text_before = chat_history[-1]
                        
                        # Target and click the submit send button
                        send_button = driver.find_element(By.CSS_SELECTOR, "button[data-qa='chatik-do-send-message']")
                        driver.execute_script("arguments[0].click();", send_button)
                        print("Message successfully submitted to candidate chat pipeline.")
                        time.sleep(0.5)

                        # Poll for a new reply every 1 second for a maximum of 10 seconds
                        new_reply_received = False
                        for seconds in range(1, 11):
                            time.sleep(1)
                            current_elements = driver.find_elements(By.CSS_SELECTOR, "[data-qa='chat-message-text'], [class*='message--']")
                            if not current_elements:
                                continue
                                
                            # Inspect the text of the newest message at the bottom
                            current_last_text = current_elements[-1].text.strip()
                            
                            # Condition A: Your message was delivered, and HR already replied with something else
                            # Condition B: HR replied before your message even finished delivering
                            if current_last_text != reply_text.strip() and current_last_text != last_text_before:
                                print(f"Live reply detected from HR: '{current_last_text[:30]}...'")
                                chat_history = [msg.text for msg in current_elements if msg.text.strip()]
                                new_reply_received = True
                                break

                        if not new_reply_received:
                            print("No immediate reply received within 10 seconds. Leaving chat.")
                            break
                 
                        
                    else:
                        print("Skipping submission: AI returned an empty response string.")
                        break

                all_extracted_messages.append({
                    "company": company_name,
                    "vacancy": vacancy_title,
                    "messages": chat_history
                })
            else:
                print("Skipping submission: No conversation timeline history parsed.")
            
            
        except Exception as e:
            print(f"Skipping chat index {index} due to unexpected behavior: {e}")
            continue
        driver.get("https://hh.ru/chat")
    
    return all_extracted_messages

    

if __name__ == "__main__":
    driver = create_selenium_session()
    session = create_authenticated_session()
    print(auto_answer_hh(session, driver))