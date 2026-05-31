import urllib.parse
import requests
from bs4 import BeautifulSoup
import re


def convert_experience_to_filter(raw_exp_text):
    if not raw_exp_text:
        return "noExperience"
        
    text = str(raw_exp_text).lower()
    
    years = 0
    months = 0
    
    years_match = re.search(r'(\d+)\s*(?:год|лет|лет)', text)
    if years_match:
        years = int(years_match.group(1))
        
    months_match = re.search(r'(\d+)\s*(?:мес|месяц|месяцев)', text)
    if months_match:
        months = int(months_match.group(1))
   
    if months >= 8:
        years += 1
        months = 0

    total_years = years + (months / 12.0)
    
    if total_years == 0.0:
        digits = re.findall(r'\d+', text)
        if digits:
            total_years = float(digits[0])
        else:
            return "noExperience"

    if total_years < 1.0:
        return "noExperience"
    elif 1.0 <= total_years <= 3.0:
        return "between1And3"
    elif 3.0 < total_years <= 6.0:
        return "between3And6"
    else:
        return "moreThan6"


def find_jobs(
    text="", 
    search_fields=None,
    experience=None,
    work_formats=None,
    employment_forms=None,
    salary=None,
    labels=None
):
    """
    Generates a structured search URL for hh.ru based on provided filters.
    
    :param text: str - Search query keyword (e.g., "Java developer")
    :param search_fields: list - Where to look for keywords ('name', 'company_name', 'description')
    :param experience: str - Filter by experience ('noExperience', 'between1And3', 'between3And6', 'moreThan6')
    :param work_formats: list - List of work types ('REMOTE', 'ON_SITE', 'FIELD_WORK', 'HYBRID')
    :param employment_forms: list - List of employment types ('FULL', 'PART', 'PROJECT', 'FLY_IN_FLY_OUT')
    :param salary: int - Minimum requested salary amount
    :param labels: list - Specific functional markers ('internship', 'low_performance', 'with_salary')
    :return: str - Fully parameterized URL string
    """
    base_url = "https://hh.ru/search/vacancy"
    params = []


    if text:
        params.append(("text", text))

    if search_fields:
        for field in search_fields:
            params.append(("search_field", field))

    if experience:
        params.append(("experience", experience))


    if work_formats:
        for fmt in work_formats:
            params.append(("work_format", fmt))


    if employment_forms:
        for emp in employment_forms:
            params.append(("employment_form", emp))

    if salary:
        params.append(("salary", str(salary)))
        params.append(("only_with_salary", "true"))

    if labels:
        for lbl in labels:
            params.append(("label", lbl))

    params.append(("ored_clusters", "true"))

    query_string = urllib.parse.urlencode(params)
    final_url = f"{base_url}?{query_string}"
    
    return final_url


def extract_job_links(search_url):
    """
    Sends an HTTP request to hh.ru and parses out vacancy links.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    
    print(f"Requesting target: {search_url}\n")
    
    try:
        # Make the network request
        response = requests.get(search_url, headers=headers, timeout=10)
        
        # Check if the platform successfully returned 200 OK
        if response.status_code != 200:
            print(f"Failed to access page. Status code: {response.status_code}")
            if response.status_code == 403:
                print("Tip: HeadHunter detected a script. Consider updating headers or using proxies.")
            return []
            
        # Parse the raw HTML structure
        soup = BeautifulSoup(response.text, "html.parser")
        
        job_links = []
        
        # HeadHunter identifies vacancy title links using the data-qa attribute
        selectors = [
            'a[data-qa="vacancy-serp__vacancy-title"]',
            'a[data-qa="serp-item__title"]' # Secondary fallback tag pattern
        ]
        
        for selector in selectors:
            anchors = soup.select(selector)
            if anchors:
                for anchor in anchors:
                    href = anchor.get("href")
                    if href:
                        # Clean tracking parameters off the URLs if present
                        clean_url = href.split("?")[0]
                        job_links.append(clean_url)
                break # Stop if links are found using the primary selector
                
        return job_links

    except requests.exceptions.RequestException as e:
        print(f"An error occurred during the request: {e}")
        return []


if __name__ == "__main__":
    target_search_url = find_jobs(
        text="Java developer",
        search_fields=["name"],
        experience="between1And3",
        work_formats=["REMOTE"],
        employment_forms=["FULL"]
    )
    
    # Process the extraction pipeline
    extracted_vacancies = extract_job_links(target_search_url)
    
    # Output total results
    print(f"Successfully found {len(extracted_vacancies)} job links:")
    for idx, link in enumerate(extracted_vacancies, start=1):
        print(f"{idx}. {link}")
