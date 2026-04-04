import asyncio
import sys
import re
from pathlib import Path
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode


DIR_CORR = Path(__file__).resolve().parent
if str(DIR_CORR) not in sys.path:
    sys.path.append(str(DIR_CORR))\
    
from web_parsing import clean_text


async def main(url_search:str):

    # Configura browser (headless = senza finestra visibile)
    browser_cfg = BrowserConfig(headless=False)

    # Configura richiesta (BYPASS = scarica sempre dalla rete, ignora cache)
    crawler_cfg = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)

    # Apre il browser e lo chiude automaticamente alla fine del blocco
    async with AsyncWebCrawler(config=browser_cfg) as crawler:

        # Visita la pagina e aspetta che il crawler sia completo
        result = await crawler.arun(
            url= url_search,
            #url="https://en.wikipedia.org/wiki/Minerva",
            config=crawler_cfg,
        )

        # result.success        - True se il crawl è andato a buon fine
        #result.error_messagge  - messaggio di errorre se fallito 

        # Alcuni output disponibili :
        #
        #result.markdown        - testo in Markdown
        #result.cleaned_html    - HTML ripulito da script, stili e rumore
        #result.html            - HTML completo della pagina (non pulito)




        pattern = r"https?://(?:www\.)?([^/]+)"

        domain = re.search(pattern, url_search)
        print(domain.group(1))

        testo = clean_text(result.html)
        print(testo[1])

        
asyncio.run(main("https://www.business.reddit.com/blog/publishers-launch"))
#asyncio.run(main("https://en.www.reddit.com/news/#main-content"))
#asyncio.run(main("https://en.wikipedia.org/wiki/BabelNet"))
#asyncio.run(main("https://en.wikipedia.org/wiki/Minerva"))

