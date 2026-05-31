from bs4 import BeautifulSoup


def get_job_description(session, job_link):
    response = session.get(job_link, timeout=15)
    if response.status_code != 200:
        print(f"Failed dashboard load. Status: {response.status_code}")
        if response.status_code == 403:
            print("Hint: HeadHunter blocked the request. Try updating your User-Agent or fresh cookies.")
        return ""

    soup = BeautifulSoup(response.content, "lxml")
    description = soup.find("div", attrs={"data-qa": "vacancy-description"})
    
    if description:
        return description.get_text(separator="\n", strip=True)
    
    return "Description not found"