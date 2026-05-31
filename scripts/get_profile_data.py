import os
import json
import re
import urllib.parse
from bs4 import BeautifulSoup
import requests


def create_authenticated_session(cookie_file="hh_cookies.json"):
    """
    Spins up a requests session and injects stored JSON cookies 
    to maintain HeadHunter authorization state.
    """
    session = requests.Session()

    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://hh.ru/"
    })

    if not os.path.exists(cookie_file):
        raise FileNotFoundError(
            f"'{cookie_file}' not found!"
        )

    print("💾 Loading cookies into HTTP session...")
    with open(cookie_file, "r", encoding="utf-8") as file:
        cookies = json.load(file)
        
    for cookie in cookies:
        session.cookies.set(
            name=cookie['name'],
            value=cookie['value'],
            domain=cookie.get('domain', '.hh.ru'),
            path=cookie.get('path', '/')
        )
        
    print("Session populated with auth cookies.")
    return session


def get_resume_links(session):
    """Fetches the applicant resume management hub and parses out user resumes."""
    url = "https://hh.ru/applicant/resumes"
    print(f"\nRequesting resume dashboard: {url}")
    
    response = session.get(url, timeout=15)
    if response.status_code != 200:
        print(f"Failed dashboard load. Status: {response.status_code}")
        if response.status_code == 403:
            print("Hint: HeadHunter blocked the request. Try updating your User-Agent or fresh cookies.")
        return []

    soup = BeautifulSoup(response.content, "lxml")
    saved_links = []

    cards = soup.find_all("a", attrs={"data-qa": re.compile(r"^resume-card-link")})

    for card in cards:
        try:
            href = card.get("href")
            if not href:
                continue
                
            # Build an absolute path if HeadHunter provides a relative address string
            full_url = urllib.parse.urljoin("https://hh.ru", href)
            
            # Extract nested text content cleanly
            title_element = card.find(attrs={"data-qa": "cell-text-content"})
            title = title_element.get_text(strip=True) if title_element else "Untitled Resume"
            
            saved_links.append({
                "title": title,
                "url": full_url
            })
        except Exception as e:
            print(f"Skipped processing a layout card due to structural shifts: {e}")
            
    return saved_links


def process_resume_data(session, resume_link):
    """
    Downloads the resume page once, parses both text elements, 
    and pipes data structural layouts directly to separate data logs.
    """
    print(f"Parsing Resume Details: {resume_link}")
    response = session.get(resume_link, timeout=15)
    if response.status_code != 200:
        print(f"Could not access resume URL. Status: {response.status_code}")
        return

    soup = BeautifulSoup(response.content, "lxml")
    resume_id = resume_link.rstrip('/').split('/')[-1].split("?")[0]

    # extract experience
    exp_container = soup.find("div", attrs={"data-qa": "resume-list-card-experience"})
    if exp_container:
        title_elem = exp_container.find(attrs={"data-qa": "title"})
        if title_elem:
            exp_title = title_elem.get_text(strip=True).replace("Опыт работы:", "").strip()  
        else:
            exp_title = "Experience length not found"
        
        job_cards = exp_container.find_all(attrs={"data-qa": "profile-experience-company-card"})
        jobs_list = []
        
        for index, card in enumerate(job_cards, 1):
            # bs4 get_text(separator="\n") maintains text segment spacings automatically
            raw_job_text = card.get_text(separator="\n", strip=True)
            
            # Strip interactive system strings found on dashboard layouts
            for structural_word in ["Развернуть", "Указать уровни", "Редактировать"]:
                raw_job_text = raw_job_text.replace(structural_word, "")
                
            cleaned_job_text = re.sub(r'\n\s*\n', '\n', raw_job_text).strip()
            jobs_list.append(f"[Job Card #{index}]\n{cleaned_job_text}")
            
        job_description = "\n\n".join(jobs_list) if jobs_list else "No detailed work timeline blocks parsed."
    else:
        exp_title = "Experience block absent"
        job_description = "Job description structural elements not found"


    # extract skills
    skills_container = soup.find("div", attrs={"data-qa": "skills-card"})
    if skills_container:
        raw_skills_text = skills_container.get_text(separator="\n", strip=True)
        for structural_word in ["Развернуть", "Указать уровни", "Редактировать"]:
            raw_skills_text = raw_skills_text.replace(structural_word, "")
            
        cleaned_skills = re.sub(r'-{2,}', '', raw_skills_text)
        cleaned_skills = re.sub(r'\n\s*\n', '\n', cleaned_skills).strip()
    else:
        cleaned_skills = "No skill tags located."


    # extract work format filters
    extracted_formats = []
    formats_container = soup.find("div", attrs={"data-qa": "resume-position-field-workFormats"})
    
    if formats_container:
        raw_formats_text = formats_container.get_text(strip=True).lower()
        
        # Explicitly map HH Russian interface string conditions to your operational parameters
        mapping = {
            "удален": "REMOTE",
            "гибрид": "HYBRID",
            "полный день": "ON_SITE",
            "гибкий график": "REMOTE" # Often safe to group flexible layouts under remote filters
        }
        
        for search_phrase, format_key in mapping.items():
            if search_phrase in raw_formats_text:
                if format_key not in extracted_formats:
                    extracted_formats.append(format_key)
                    
    # Fallback to standard Remote filtering if no specific elements were checked on the profile
    if not extracted_formats:
        extracted_formats = ["REMOTE"]

    # Resume Title
    title_element = soup.find(attrs={"data-qa": "resume-block-title-position"})

    if title_element:
        resume_title = title_element.get_text(strip=True)
        print(f"Extracted resume title: {resume_title}")
    else:
        resume_title = "Unknown Resume Title"
        print("Warning: Could not find the resume title element on the page.")

    # About me section
    about_element = soup.find("div", attrs={"data-qa": "resume-about-card"})
    if about_element:
        about_text = about_element.get_text(separator=" ", strip=True)
        if about_text.startswith("О себе"):
            about_text = about_text.replace("О себе", "", 1).strip()
    else:
        about_text = ""
        print("Notice: 'About me' section is empty or missing.")


    resume_text = f"""
        RESUME TITLE: {resume_title}
        ---   ABOUT ME   ---
        {about_text}
        --------------------
        TOTAL EXPERIENCE: {exp_title}
        --- WORK DETAILS ---
        {job_description}
        --------------------
        Skills:
        {cleaned_skills}
    """
    
    exp_title = exp_title.replace("Опыт работы:", "").strip()
    # Return everything cleanly as a single payload to feed into your n8n output loop

    "resume-block-title-position"

    return {
        "resume_id": resume_id,
        "resume_title": resume_title,
        "resume_text": resume_text,
        "work_formats": extracted_formats,
        "total_experience": exp_title,
    }


if __name__ == "__main__":
    try:
        # Establish authenticated execution scope
        hh_session = create_authenticated_session("hh_cookies.json")
        
        # Scrape targeted dashboard structures
        resumes = get_resume_links(hh_session)
        print(f"Discovered {len(resumes)} profile entries to crawl.")

        for res in resumes:
            print(f"\nTitle Target: {res['title']}")
            process_resume_data(hh_session, res['url'])
            
    except Exception as error:
        print(f"\nScript encountered an error execution halt: {error}")
