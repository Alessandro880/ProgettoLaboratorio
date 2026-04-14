import sys
import re
from fastapi import FastAPI
from pathlib import Path
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

app = FastAPI()

DIR_CORR = Path(__file__).resolve().parent
if str(DIR_CORR) not in sys.path:
    sys.path.append(str(DIR_CORR))
    
from web_parsing import clean_text

@app.get("/api/parse/{url:path}")
async def parser_page(url: str) -> dict: 
    
    url_search = url
    if not url_search.startswith("http"):
        url_search = "https://" + url_search

    # Configura browser (headless = senza finestra visibile)
    browser_cfg = BrowserConfig(headless=False)

    # Configura richiesta (BYPASS = scarica sempre dalla rete, ignora cache)
    crawler_cfg = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)

    # Apre il browser e lo chiude automaticamente alla fine del blocco
    async with AsyncWebCrawler(config=browser_cfg) as crawler:

        # Visita la pagina e aspetta che il crawler sia completo
        result = await crawler.arun(
            url=url_search,
            config=crawler_cfg,
        )

        # 3. SISTEMA IL DOMINIO: Estrae il testo pulito dalla Regex per evitare l'Errore 500
        pattern = r"https?://(?:www\.)?([^/]+)"
        match = re.search(pattern, url_search)
        domain = match.group(1) if match else "Dominio sconosciuto"

        testo = clean_text(result.html)

        risorsa = {
            "url": url_search,
            "domain": domain,
            "title": testo[0],
            "html_txt": result.html,
            "parsed_txt": testo[1]
        }
        
        return risorsa

    
#asyncio.run(main("https://www.business.reddit.com/blog/publishers-launch"))

#asyncio.run(main("https://en.www.reddit.com/news/#main-content"))

#asyncio.run(main("https://en.wikipedia.org/wiki/BabelNet"))

#asyncio.run(main("https://en.wikipedia.org/wiki/Minerva"))

#asyncio.run(main("https://en.wikipedia.org/wiki/Divine_Comedy"))

#asyncio.run(main("https://www.governo.it/it/i-governi-dal-1943-ad-oggi/i-governi-nelle-legislature/192"))



#https://www.olympics.com

#https://www.governo.it

#https://lospiegone.com