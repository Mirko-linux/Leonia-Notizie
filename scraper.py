import requests
from bs4 import BeautifulSoup

def scrape_ansa():
    try:
        res = requests.get("https://www.ansa.it/sito/notizie/topnews/index.shtml", timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        notizie = []
        for h3 in soup.find_all('h3', limit=5):
            a_tag = h3.find('a', href=True)
            if a_tag:
                titolo = a_tag.get_text(strip=True)
                link = a_tag['href']
                if not link.startswith('http'): link = "https://www.ansa.it" + link
                notizie.append(f"Fonte: ANSA | Titolo: {titolo} | Link: {link}")
        return notizie
    except: return []

def scrape_tgcom24():
    try:
        res = requests.get("https://www.tgcom24.mediaset.it/ultimissime/", timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        notizie = []
        # TGCom24 usa spesso h3 per i titoli nelle liste
        for h3 in soup.find_all('h3', limit=5):
            a_tag = h3.find('a', href=True)
            if a_tag:
                titolo = a_tag.get_text(strip=True)
                link = a_tag['href']
                if not link.startswith('http'): link = "https://www.tgcom24.mediaset.it" + link
                notizie.append(f"Fonte: TGCom24 | Titolo: {titolo} | Link: {link}")
        return notizie
    except: return []

def scrape_rainews():
    try:
        res = requests.get("https://www.rainews.it/notizie/ultimo-ora", timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        notizie = []
        # RaiNews usa spesso h2 o tag con classi specifiche
        for h2 in soup.find_all('h2', limit=5):
            a_tag = h2.find_parent('a', href=True) or h2.find('a', href=True)
            if a_tag:
                titolo = h2.get_text(strip=True)
                link = a_tag['href']
                if not link.startswith('http'): link = "https://www.rainews.it" + link
                notizie.append(f"Fonte: RaiNews | Titolo: {titolo} | Link: {link}")
        return notizie
    except: return []

def scrape_repubblica():
    try:
        res = requests.get("https://www.repubblica.it/lastminute/", timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        notizie = []
        for h2 in soup.find_all('h2', limit=5):
            a_tag = h2.find('a', href=True)
            if a_tag:
                titolo = a_tag.get_text(strip=True)
                link = a_tag['href']
                if not link.startswith('http'): link = link # Repubblica usa spesso URL assoluti
                notizie.append(f"Fonte: Repubblica | Titolo: {titolo} | Link: {link}")
        return notizie
    except: return []

def scrape_corriere():
    try:
        res = requests.get("https://www.corriere.it/notizie-ultima-ora/", timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        notizie = []
        for h4 in soup.find_all('h4', limit=5):
            a_tag = h4.find('a', href=True)
            if a_tag:
                titolo = a_tag.get_text(strip=True)
                link = a_tag['href']
                if not link.startswith('http'): link = link
                notizie.append(f"Fonte: Corriere | Titolo: {titolo} | Link: {link}")
        return notizie
    except: return []

def get_all_news():
    """Raccoglie le notizie da tutte e 5 le fonti e le unisce."""
    tutte_le_notizie = []
    
    tutte_le_notizie.extend(scrape_ansa())
    tutte_le_notizie.extend(scrape_tgcom24())
    tutte_le_notizie.extend(scrape_rainews())
    tutte_le_notizie.extend(scrape_repubblica())
    tutte_le_notizie.extend(scrape_corriere())
    
    # Rimuove duplicati basandosi sul testo e filtra stringhe corte
    return list(set([n for n in tutte_le_notizie if len(n) > 20]))