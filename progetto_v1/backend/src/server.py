import sys
import re
import json
from fastapi import FastAPI, Request, HTTPException
from pathlib import Path
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from pydantic import BaseModel

app = FastAPI()

class DatiInput(BaseModel):
    parsed_text: str
    gold_text: str

class PaginaWebRequest(BaseModel):
    url: str
    html_text: str

cartella_script = Path(__file__).parent.resolve()
cartella_radice = cartella_script.parent.parent

DIR_CORR = Path(__file__).resolve().parent
if str(DIR_CORR) not in sys.path:
    sys.path.append(str(DIR_CORR))
# from web_parsing import clean_text, clean_olympics_text, rimuovi_markdown, clean_wikipedia_text, clean_governo_text, clean_lospiegone_text
from valuation import token_level_eval, sequence_similarity_eval 
from web_parsing import clean_text, clean_olympics_text, rimuovi_markdown, clean_wikipedia_text, clean_governo_text, clean_lospiegone_text

@app.get("/parse")
async def parser_page(url: str) -> dict: 
    percorso_gs = "/app/gs_data"
    percorso_domains = "/app/domains.json"
    url_search = url
    if not url_search.startswith("http"):
        url_search = "https://" + url_search
    
    pattern = r"https?://((?:www\.)?[^/]+)"
    match = re.search(pattern, url)
    if not match:
        raise HTTPException(status_code=400, detail="URL non valido")
    domain = match.group(1) 
    
    try:
        with open(percorso_domains, "r", encoding="utf-8") as f:
            dati_json = json.load(f)
            if isinstance(dati_json, dict) and "domains" in dati_json:
                domini = dati_json["domains"] 
            elif isinstance(dati_json, list):
                domini = dati_json 
            else:
                domini = []
    except FileNotFoundError:
        domini = []
    
    domain = domain.lower()
    if domain not in domini: 
        raise HTTPException(status_code=400, detail="Dominio non supportato!")
    
    browser_cfg = BrowserConfig(headless=True)
    crawler_cfg = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)

    try:
        async with AsyncWebCrawler(config=browser_cfg) as crawler:
            result = await crawler.arun(url=url_search, config=crawler_cfg)
            
            # IL FIX E' QUI: Se non c'è HTML, ci fermiamo e lanciamo 400!
            if not result.html:
                raise HTTPException(status_code=400, detail="URL irraggiungibile o pagina vuota")

            if domain == "en.wikipedia.org":
                testo = clean_wikipedia_text(result.html)
            elif domain == "www.olympics.com":
                testo = clean_olympics_text(result.html)
            elif domain == "www.governo.it":
                testo = clean_governo_text(result.html)
            elif domain == "lospiegone.com":
                testo = clean_lospiegone_text(result.html)
            else:
                testo = clean_text(result.html)

            # Estrazione sicura per evitare null
            titolo_sicuro = testo[0] if (testo and len(testo) > 0 and testo[0]) else "Titolo mancante"
            testo_parsato = testo[1] if (testo and len(testo) > 1) else ""

            return {
                "url": url_search,
                "domain": domain,
                "title": titolo_sicuro,
                "html_text": result.html,
                "parsed_text": testo_parsato
            }
            
    # Propaga l'HTTPException del blocco if not result.html
    except HTTPException:
        raise
    except Exception as e:
        # Se il crawler va in errore di rete, FERMIAMO IL BACKEND CON 400
        raise HTTPException(status_code=400, detail="URL irraggiungibile")

@app.post("/parse")
def parser_post(page: PaginaWebRequest):
    percorso_gs = "/app/gs_data"
    percorso_domains = "/app/domains.json"
    url_search = page.url
    if not url_search.startswith("http"):
        url_search = "https://" + url_search
    
    pattern = r"https?://((?:www\.)?[^/]+)"
    match = re.search(pattern, page.url)
    if not match:
        raise HTTPException(status_code=400, detail="URL non valido")
    domain = match.group(1) 
    
    try:
        with open(percorso_domains, "r", encoding="utf-8") as f:
            dati_json = json.load(f)
            if isinstance(dati_json, dict) and "domains" in dati_json:
                domini = dati_json["domains"] 
            elif isinstance(dati_json, list):
                domini = dati_json 
            else:
                domini = []
    except FileNotFoundError:
        domini = []
    
    domain = domain.lower()
    if domain not in domini: 
        raise HTTPException(status_code=400, detail="Dominio non supportato!")
      
    if domain == "en.wikipedia.org":
        testo = clean_wikipedia_text(page.html_text)
    elif domain == "www.olympics.com":
        testo = clean_olympics_text(page.html_text)
    elif domain == "www.governo.it":
        testo = clean_governo_text(page.html_text)
    elif domain == "lospiegone.com":
        testo = clean_lospiegone_text(page.html_text)
    else:
        testo = clean_text(page.html_text)
        
    titolo_sicuro = testo[0] if (testo and len(testo) > 0 and testo[0]) else "Titolo mancante"
    testo_parsato = testo[1] if (testo and len(testo) > 1) else ""

    return {
        "url": url_search,
        "domain": domain,
        "title": titolo_sicuro,
        "html_text": page.html_text,
        "parsed_text": testo_parsato
    }

@app.post("/evaluate")
def evaluate(dati: DatiInput):
    parsed_pulito = rimuovi_markdown(dati.parsed_text)
    gold_pulito = rimuovi_markdown(dati.gold_text)
    
    w_token_eval = token_level_eval(parsed_pulito, gold_pulito)
    w_sequence_sim = sequence_similarity_eval(parsed_pulito, gold_pulito)
    
    return {
        "token_level_eval": {
            "precision": w_token_eval["precision"],
            "recall": w_token_eval["recall"],
            "f1": w_token_eval["f1"]
        },
        "sequence_similarity_eval": {
            "sequence_similarity_ratio": w_sequence_sim["sequence_similarity_ratio"],
            "longest_contiguous_match_chars": w_sequence_sim["longest_contiguous_match_chars"],
            "is_perfect_match": w_sequence_sim["is_perfect_match"]
        }
    }

@app.get("/domains")
def mostra_domini(request: Request):
    percorso_domains = "/app/domains.json"
    try:
        with open(percorso_domains, "r", encoding="utf-8") as f:
            dati_json = json.load(f)
            return dati_json 
    except FileNotFoundError:
        return {"domains": []}

@app.get("/gold_standard")
def mostra_gold_standard(url: str):
    percorso_gs = "/app/gs_data"
    percorso_domains = "/app/domains.json"
    
    pattern = r"https?://((?:www\.)?[^/]+)"
    match = re.search(pattern, url)
    if not match:
        raise HTTPException(status_code=400, detail="URL non valido")
    domain = match.group(1)

    try:
        with open(percorso_domains, "r", encoding="utf-8") as f:
            dati_json = json.load(f)
            if isinstance(dati_json, dict) and "domains" in dati_json:
                domini = dati_json["domains"] 
            elif isinstance(dati_json, list):
                domini = dati_json 
            else:
                domini = []
    except FileNotFoundError:
        domini = []
        
    if domain not in domini: 
        raise HTTPException(status_code=400, detail="Dominio non supportato!")
    
    file = f"{percorso_gs}/{domain}.json"
    try:
        with open(file, "r", encoding="utf-8") as f:
            dati_json = json.load(f)
            lista_pagine = dati_json.get("gold_standard", [])
            for pagina in lista_pagine:
                if pagina.get('url') == url:
                    return pagina
                
            raise HTTPException(status_code=404, detail="URL non nel GS")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Errore apertura file in gs")

@app.get("/full_gold_standard")
def mostra_full_gold_standard(domain: str):
    percorso_gs = "/app/gs_data"
    percorso_domains = "/app/domains.json"

    try:
        with open(percorso_domains, "r", encoding="utf-8") as f:
            dati_json = json.load(f)
            if isinstance(dati_json, dict) and "domains" in dati_json:
                domini = dati_json["domains"] 
            elif isinstance(dati_json, list):
                domini = dati_json 
            else:
                domini = []
    except FileNotFoundError:
        domini = []
        
    if domain not in domini: 
        raise HTTPException(status_code=400, detail="Dominio non supportato!")
    
    file = f"{percorso_gs}/{domain}.json"
    try:
        with open(file, "r", encoding="utf-8") as f:
            dati_json = json.load(f)
            return dati_json
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Problema apertura {domain}.json") 

@app.get("/full_gs_eval")
def full_gs_eval(domain: str):
    percorso_gs = "/app/gs_data"
    percorso_domains = "/app/domains.json"

    try:
        with open(percorso_domains, "r", encoding="utf-8") as f:
            dati_json = json.load(f)
            if isinstance(dati_json, dict) and "domains" in dati_json:
                domini = dati_json["domains"] 
            elif isinstance(dati_json, list):
                domini = dati_json 
            else:
                domini = []
    except FileNotFoundError:
        domini = []
        
    if domain not in domini: 
        raise HTTPException(status_code=404, detail="Dominio non supportato!")

    file = f"{percorso_gs}/{domain}.json"
    try:
        with open(file, "r", encoding="utf-8") as f:
            dati_json = json.load(f)
            
            result = {
                "token_level_eval": {"precision": 0.0, "recall": 0.0, "f1": 0.0},
                "sequence_similarity_eval": {"sequence_similarity_ratio": 0.0, "longest_contiguous_match_chars": 0.0, "is_perfect_match": True}
            }
            
            pagine = dati_json.get("gold_standard", [])
            numero_pagine = len(pagine)
            if numero_pagine == 0:
                raise HTTPException(status_code=404, detail="Il file GS è vuoto")

            for page in pagine:
                html = page.get("html_text", "")
                gold = page.get("gold_text", "")
                
                if domain == "en.wikipedia.org":
                    testo_md = clean_wikipedia_text(html)[1] if clean_wikipedia_text(html) else ""
                elif domain == "www.olympics.com":
                    testo_md = clean_olympics_text(html)[1] if clean_olympics_text(html) else ""
                elif domain == "www.governo.it":
                    testo_md = clean_governo_text(html)[1] if clean_governo_text(html) else ""
                elif domain == "lospiegone.com":
                    testo_md = clean_lospiegone_text(html)[1] if clean_lospiegone_text(html) else ""
                else:
                    testo_md = clean_text(html)[1] if clean_text(html) else ""
                
                parsed_pulito = rimuovi_markdown(testo_md)
                gold_pulito = rimuovi_markdown(gold)

                # IL FIX È QUI: Ora confronta parsed_pulito con gold_pulito! 
                w_token_eval = token_level_eval(parsed_pulito, gold_pulito)
                w_sequence_sim = sequence_similarity_eval(parsed_pulito, gold_pulito)

                result["token_level_eval"]["precision"] += w_token_eval.get("precision", 0)
                result["token_level_eval"]["recall"] += w_token_eval.get("recall", 0)
                result["token_level_eval"]["f1"] += w_token_eval.get("f1", 0)

                result["sequence_similarity_eval"]["sequence_similarity_ratio"] += w_sequence_sim.get("sequence_similarity_ratio", 0)
                result["sequence_similarity_eval"]["longest_contiguous_match_chars"] += w_sequence_sim.get("longest_contiguous_match_chars", 0)
                
                if not w_sequence_sim.get("is_perfect_match", False):
                    result["sequence_similarity_eval"]["is_perfect_match"] = False

            result["token_level_eval"]["precision"] /= numero_pagine
            result["token_level_eval"]["recall"] /= numero_pagine
            result["token_level_eval"]["f1"] /= numero_pagine
            result["sequence_similarity_eval"]["sequence_similarity_ratio"] /= numero_pagine
            result["sequence_similarity_eval"]["longest_contiguous_match_chars"] /= numero_pagine

            return result
            
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Problema apertura {domain}.json")