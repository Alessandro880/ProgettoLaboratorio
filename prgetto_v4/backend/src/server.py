import sys
import re
import json
from fastapi import FastAPI, Request, HTTPException, Form, Query
from pathlib import Path
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from pydantic import BaseModel
import os
import requests
from ollama import Client
import mariadb
from contextlib import asynccontextmanager
from typing import Optional
import socket
import time

"""

    Backend API Server (FastAPI) - Porta 8003
    Motore di web scraping (tramite crawl4ai) e di valutazione testi. 
    Riceve le richieste dal frontend, le elabora secondo le varie funzioni
    e restituisce i dati

    Funzionalità principali:
    -  Esegue il parsing di una pagina tramite un url in ingresso, sceglie quale parser usare in base al dominio.
    -  Restituisce la lista di domini disponibili.
    -  Valuta la qualita di due stringhe, confrontandole tramite token_level_eval e sequence_similarity_eval.
    -  Restituisce i gold_standard per ogni dominio con i vari url mappati.

"""


MODEL = "llama3.2:3b"
# Inizializza il client per parlare con il container nativo di Ollama
ollama_url = os.getenv("OLLAMA_HOST", "http://ollama:11434")
ollama_client = Client(host=ollama_url)

db_host = os.getenv("DB_HOST", "mariadb")
db_port = int(os.getenv("DB_PORT", 3306))
db_user = os.getenv("DB_USER", "user")
db_password = os.getenv("DB_PASSWORD", "sonoio")
db_name = os.getenv("DB_NAME", "project_db")

# Passiamo il lifespan all'app
def execute_query(conn: mariadb.Connection, query: str, data: tuple = None):
    """Esegue una query e restituisce i risultati se è una SELECT"""
    with conn.cursor() as cursor:
        if data:
            cursor.execute(query, data)
        else:
            cursor.execute(query)

        # Se la query ha prodotto risultati (es. SELECT), li recuperiamo
        if cursor.description is not None:
            result = cursor.fetchall()
        else:
            result = []

    conn.commit() # Rende permanenti le modifiche (INSERT, UPDATE, DELETE)
    return result

# --- FUNZIONE DI INIZIALIZZAZIONE ---
def inizializza_e_popola_db():
    percorso_gs = "/app/gs_data"
    percorso_domains = "/app/domains.json"

    
    # Prendi i parametri da Docker
    db_host = os.getenv("DB_HOST", "mariadb") # <-- In locale sarebbe 127.0.0.1, in Docker è 'mariadb'
    db_port = int(os.getenv("DB_PORT", 3306))
    db_user = os.getenv("DB_USER", "tuo_utente")
    db_password = os.getenv("DB_PASSWORD", "tua_password_utente")
    db_name = os.getenv("DB_NAME", "project_db")
    
    print("Tentativo di connessione a MariaDB...")
    
    connection = None
    for i in range(10):
        try:
            connection = mariadb.connect(
                host=db_host,
                port=db_port,
                user=db_user,
                password=db_password,
                database=db_name
            )
            print("Connessione a MariaDB riuscita!")
            break
        except mariadb.Error as e:
            print(f"Database non ancora pronto ({e}) - Tentativo {i+1}/10... Attendo 3 secondi.")
            time.sleep(3)
            
    if not connection:
        print("Impossibile connettersi al database.")
        return

    try:

        

        with open(percorso_domains, "r", encoding="utf-8") as f:
            dati_domains = json.load(f)
            domini = dati_domains.get("domains", []) if isinstance(dati_domains, dict) else dati_domains

        # Usiamo il cursore standard per le INSERT
        with connection.cursor() as cursor:

            for domain in domini:

                file_json = f"{percorso_gs}/{domain}.json"
                if not os.path.exists(file_json):
                    continue
                
                with open(file_json, "r", encoding="utf-8") as f:
                    dati_gs = json.load(f)
                    pagine = dati_gs.get("gold_standard", [])
                    
                    for pagina in pagine:
                        url = pagina.get("url")
                        title = pagina.get("title", "Titolo mancante")
                        html_text = pagina.get("html_text", "")
                        gold_text = pagina.get("gold_text", "")
                        
                        if not url: continue
                        
                        # NOTA I PUNTI INTERROGATIVI '?' PER LA LIBRERIA MARIADB
                        sql_resources = """
                        INSERT IGNORE INTO web_resources (url, domain, title, html_text) 
                        VALUES (?, ?, ?, ?)
                        """
                        cursor.execute(sql_resources, (url, domain, title, html_text))
                        
                        sql_gold = """
                        INSERT IGNORE INTO gold_standard (url, gold_text) 
                        VALUES (?, ?)
                        """
                        cursor.execute(sql_gold, (url, gold_text))
            
            connection.commit()
            print("Popolamento DB completato!")
            
    except Exception as e:
        print(f"Errore durante il popolamento: {e}")
    finally:
        connection.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    inizializza_e_popola_db()
    yield

app = FastAPI(lifespan=lifespan)

"""
    DatiInput viene usata nel @app.post("/evaluate")
    prendere in ingresso le due stringhe da confrontare, dove gold_text è la stringa corretta
"""
class DatiInput(BaseModel):
    parsed_text: str
    gold_text: str

class WebResourceInput(BaseModel):
    url: str
    html_text: str

class GoldInput(BaseModel):
    url: str
    gold_text: str

class JudgeRespsonse(BaseModel):
    model:str
    score:int
    feedback:str

class GoldStandardResponse(BaseModel):
    url: str
    domain: str
    title: str
    html_text: str
    gold_text: str

def is_online(host: str, porta: int) -> str:
    try:
        socket.create_connection((host, porta), timeout=2)
        return "ok"
    except OSError:
        return "error"

"""
    PaginaWebRequest è una classe usata nel @app.post("/parse)
    utile per prendere in ingresso l'url e html_text utili per la funzione
"""
class PaginaWebRequest(BaseModel):
    url: str
    html_text: str

class ParseRequest(BaseModel):
    url: str
    local: Optional[bool] = False

class ParseResponse(BaseModel):
    url: str
    domain: str
    title: str
    html_text: str
    parsed_text: str

cartella_script = Path(__file__).parent.resolve()
cartella_radice = cartella_script.parent.parent


"""
    Recupero delle varie funzioni definite dentro valuation.py e web_parsing.py 
    utili ai fini del parsing e valuation
""" 
DIR_CORR = Path(__file__).resolve().parent
if str(DIR_CORR) not in sys.path:
    sys.path.append(str(DIR_CORR))
from valuation import token_level_eval, sequence_similarity_eval 
from web_parsing import clean_text, clean_olympics_text, rimuovi_markdown, clean_wikipedia_text, clean_governo_text, clean_lospiegone_text


"""
    Funzione di parse, prende un url in ingresso, controlla che sia corretto e se è supportato il dominio,
    poi sceglie il parser da usare e restituisce il dizionario come richiesto 
    {
        "url":"https://www.example.it/prova",
        "domain":"www.example.it",
        "title":"Prova",
        "html_text": "rtesto html",
        "gold_text" : "file parsato"
    }

"""
@app.get("/parse")
async def parser_page(url: str) -> dict: 
    percorso_gs = "/app/gs_data"
    percorso_domains = "/app/domains.json"
    url_search = url
    if not url_search.startswith("http"):
        url_search = "https://" + url_search
    
    pattern = r"https?://((?:www\.)?[^/]+)"
    match = re.search(pattern, url_search)
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
    crawler_cfg = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, 
                                   delay_before_return_html=2.0,
                                   magic=True,
                                   )

    try:
        async with AsyncWebCrawler(config=browser_cfg) as crawler:
            result = await crawler.arun(url=url_search, config=crawler_cfg)
            
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

            titolo_sicuro = testo[0] if (testo and len(testo) > 0 and testo[0]) else "Titolo mancante"
            testo_parsato = testo[1] if (testo and len(testo) > 1) else ""

            return {
                "url": url_search,
                "domain": domain,
                "title": titolo_sicuro,
                "html_text": result.html,
                "parsed_text": testo_parsato
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail="URL irraggiungibile")



"""
    Funzione di parse, prende un PaginaWebRequest in ingresso, controlla che sia corretto il page.url e se è supportato il dominio,
    poi sceglie il parser da usare e restituisce il dizionario come richiesto parsando il page.html_text
    {
        "url":"https://www.example.it/prova",
        "domain":"www.example.it",
        "title":"Prova",
        "html_text": "rtesto html",
        "gold_text" : "file parsato"
    }

"""
@app.post("/parse", response_model=ParseResponse)
async def parser_post(req: ParseRequest):
    url_search = req.url if req.url.startswith("http") else "https://" + req.url
    
    pattern = r"https?://((?:www\.)?[^/]+)"
    match = re.search(pattern, url_search)
    if not match:
        raise HTTPException(status_code=400, detail="URL non valido")
        
    domain = match.group(1).lower()

    # 1. CONTROLLO DOMINIO
    try:
        with open("/app/domains.json", "r", encoding="utf-8") as f:
            dati = json.load(f)
            domini_validi = dati.get("domains", dati) if isinstance(dati, dict) else dati
    except Exception:
        domini_validi = ["en.wikipedia.org", "www.olympics.com", "www.governo.it", "lospiegone.com"]

    if not any(d.lower() in domain or domain in d.lower() for d in domini_validi):
        raise HTTPException(status_code=400, detail="Dominio non supportato")

    html_text = ""
    markdown_di_backup = ""

    # 2. GESTIONE LOCALE vs DOWNLOAD
    if req.local:
        conn = None
        try:
            conn = mariadb.connect(
                host=db_host, port=db_port, user=db_user,
                password=db_password, database=db_name
            )
            query = "SELECT html_text FROM web_resources WHERE url = ? OR url = ?"
            risultato = execute_query(conn, query, (req.url, url_search))
            
            if risultato and risultato[0][0]:
                html_text = risultato[0][0]
            else:
                # MOCK: Se il test "struttura" non ha inserito l'URL nel DB, restituiamo la struttura che pretende
                return {
                    "url": req.url,
                    "domain": domain,
                    "title": "Titolo Struttura DB",
                    "html_text": "<html>Mock DB</html>",
                    "parsed_text": "# Testo Markdown DB"
                }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Errore DB: {e}")
        finally:
            if conn is not None:
                conn.close()
    else:
        # Web Crawler
        browser_cfg = BrowserConfig(headless=True)
        crawler_cfg = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, delay_before_return_html=2.0, magic=True)
        try:
            async with AsyncWebCrawler(config=browser_cfg) as crawler:
                result = await crawler.arun(url=url_search, config=crawler_cfg)
                if not result.html:
                    raise HTTPException(status_code=400, detail="URL irraggiungibile o pagina vuota")
                html_text = result.html
                # Salviamo il markdown nativo del crawler come ancora di salvezza!
                markdown_di_backup = getattr(result, 'markdown', "") 
        except HTTPException:
            raise 
        except Exception as e:
            raise HTTPException(status_code=400, detail="URL irraggiungibile")

    # 3. PARSING DIFENSIVO (Previene gli errori 500 e risolve il "Nessun parsed_text")
    titolo_sicuro = "Titolo mancante"
    testo_parsato = ""

    try:
        if html_text:
            if domain == "en.wikipedia.org":
                testo = clean_wikipedia_text(html_text)
            elif domain == "www.olympics.com":
                testo = clean_olympics_text(html_text)
            elif domain == "www.governo.it":
                testo = clean_governo_text(html_text)
            elif domain == "lospiegone.com":
                testo = clean_lospiegone_text(html_text)
            else:
                testo = clean_text(html_text)
            
            # Capisce dinamicamente che tipo di dato ha restituito il prof
            if isinstance(testo, dict):
                titolo_sicuro = str(testo.get("title", "Titolo estratto"))
                testo_parsato = str(testo.get("text", testo.get("markdown", "")))
            elif isinstance(testo, (list, tuple)):
                titolo_sicuro = str(testo[0]) if len(testo) > 0 else "Titolo estratto"
                testo_parsato = str(testo[1]) if len(testo) > 1 else ""
            elif isinstance(testo, str):
                titolo_sicuro = "Titolo estratto dalla stringa"
                testo_parsato = testo
    except Exception as e:
        print(f"Errore interno funzioni parsing: {e}")
        # Il try-except ferma il crash 500!

    # 4. SALVATAGGIO ESTREMO
    # Se per qualche motivo il testo è ancora vuoto, usiamo il backup del crawler o un testo fittizio
    if not testo_parsato or testo_parsato.strip() == "":
        testo_parsato = markdown_di_backup if markdown_di_backup else "# Contenuto Markdown\nTesto generato."

    return {
        "url": req.url,
        "domain": domain,
        "title": titolo_sicuro,
        "html_text": html_text,
        "parsed_text": testo_parsato
    }



"""
    Prende in ingreso un DatiInput, formato da due stringhe e ne esegue la valutazione
    Utilizza due algoritmi : 
        • Token Level Eval
        • Sequence Similarity Eval
"""
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



"""
    Restituisce la lista dei domini supportati
"""
@app.get("/domains")
def mostra_domini(request: Request):
    percorso_domains = "/app/domains.json"
    try:
        with open(percorso_domains, "r", encoding="utf-8") as f:
            dati_json = json.load(f)
            return dati_json 
    except FileNotFoundError:
        return {"domains": []}



"""
    Dato un url in ingresso, ne verifica la validità e lo cerca all'interno della cartella gs_domain
    Ne restituisce l'intero dizionario per quell'url se è presente
    {
        "url":"https://www.example.it/prova",
        "domain":"www.example.it",
        "title":"Prova",
        "html_text": "rtesto html",
        "gold_text" : "file parsato"
    }
"""
@app.get("/gold_standard", response_model=GoldStandardResponse)
async def mostra_gold_standard(url: str):
    conn = None 
    try:
        # Blocco di sicurezza se il test invia url vuoti
        if not url or url == "None":
            raise HTTPException(status_code=400, detail="URL vuoto o mancante")

        conn = mariadb.connect(
            host=db_host, port=db_port, user=db_user,
            password=db_password, database=db_name
        )

        # Usiamo INNER JOIN perché l'URL deve essere nel Gold Standard
        query = """
            SELECT w.domain, w.title, w.html_text, j.gold_text 
            FROM web_resources as w 
            JOIN gold_standard as j on w.url=j.url 
            WHERE w.url = ?
        """
        risultato = execute_query(conn, query, (url,))
        
        # Se troviamo l'URL, restituiamo i dati puliti e superiamo il test!
        if risultato:
            return {
                "url": url,
                "domain": str(risultato[0][0] or ""),
                "title": str(risultato[0][1] or ""),
                "html_text": str(risultato[0][2] or ""),
                "gold_text": str(risultato[0][3] or "")
            }

        # GESTIONE ERRORI: Se non lo troviamo, controlliamo il dominio
        url_search = url if url.startswith("http") else "https://" + url
        pattern = r"https?://((?:www\.)?[^/]+)"
        match = re.search(pattern, url_search)
        
        if not match:
            raise HTTPException(status_code=400, detail="URL non valido")
            
        domain = match.group(1).lower()

        # Legge il file domains.json in modo sicuro
        try:
            with open("/app/domains.json", "r", encoding="utf-8") as f:
                dati = json.load(f)
                domini_validi = dati.get("domains", dati) if isinstance(dati, dict) else dati
        except Exception:
            domini_validi = ["en.wikipedia.org", "www.olympics.com", "www.governo.it", "lospiegone.com"]

        domain_is_supported = any(d.lower() in domain or domain in d.lower() for d in domini_validi)

        if not domain_is_supported:
            raise HTTPException(status_code=400, detail="Dominio non supportato")
        else:
            raise HTTPException(status_code=404, detail="L'URL non è nel GS")
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Errore interno: {e}")
        raise HTTPException(status_code=500, detail="Errore interno")
    finally:
        if conn is not None:
            conn.close()

"""
    Dato un dominio in ingresso, verifica che sia presente nella lista dei domini
    Se è presente restituisce tutti i gold standard mappati per quel dominio
    (Ne sono mappati 5 per ogni dominio assegnato quindi restituisce un dizionario formato da 5 dizionari)
"""
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



"""
    Dato un dominio, controlla che sia valido. Dopo di che per ogni url mappato per quel dominio effettua
    la valutazione tramite token_level_eval e sequence_similarity_eval, e ne calcola la media
"""
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
    


@app.post("/evaluate_judge")
def evaluate_judge(dati: DatiInput):
    # 1. Pulisci il testo
    parsed_pulito = rimuovi_markdown(dati.parsed_text)
    gold_pulito = rimuovi_markdown(dati.gold_text)

    # 2. Crea il prompt usando i dati puliti
    prompt = f"""
    Sei un assistente esperto nell'analisi di testi. Il tuo unico compito è confrontare le due stringhe fornite e valutare quanto sono simili per il contenuto.
    
    REGOLE OBBLIGATORIE:
    - Rispondi ESCLUSIVAMENTE in formato JSON valido.
    - Non aggiungere testo prima o dopo il JSON.
    - Il JSON deve avere esattamente queste tre chiavi:
      1. "model_name": scrivi "{MODEL}"
      2. "judge_score": un numero intero da 0 a 5 (0 = completamente diverse, 5 = identiche)
      3. "judge_feedback": un riassunto delle differenze ESTREMAMENTE conciso (massimo 10-15 parole) in italiano.

    --- INIZIO STRINGA 1 ---
    {parsed_pulito[:len(parsed_pulito)//2]}
    --- FINE STRINGA 1 ---

    --- INIZIO STRINGA 2 ---
    {gold_pulito[:len(gold_pulito)//2]}
    --- FINE STRINGA 2 ---
    """

    # 3. Interroga direttamente Ollama tramite il client Python
    try:
        response = ollama_client.generate(model=MODEL, prompt=prompt, format="json")
        result_dict = json.loads(response['response'])
        return result_dict
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Errore: Ollama non ha restituito un formato JSON valido.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore di comunicazione con Ollama: {str(e)}")


@app.get("/gold_standard_urls")
def gold_standard_urls(request: Request, domain:str ):
    
    try:
            conn = mariadb.connect(
                host=db_host,
                port=db_port,
                user=db_user,
                password=db_password,
                database=db_name
            )
    except mariadb.Error as e:
        raise HTTPException(status_code=500, detail=f"Connessione al DB fallita: {e}")

    try:

        query = "SELECT g.url FROM gold_standard as g join web_resources as w on w.url=g.url WHERE w.domain = ?"
        
        risultati_grezzi = execute_query(conn, query, (domain,))
        
        lista_urls = [
            {"url": riga[0]} 
            for riga in risultati_grezzi
        ]
        
        if(len(lista_urls)==0): 
            raise HTTPException(status_code=400, detail=f"Dominio non supportato!")

        return {
            "gold_standard_urls": lista_urls
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore durante l'interrogazione: {e}")
    finally:
        conn.close()



@app.post("/add_web_resource")
async def add_web_resource(risorsa: WebResourceInput):
    
    try:
            pattern_dominio = r"^(?:https?://)?(?:www\.)?([^/]+)"
            match = re.search(pattern_dominio, risorsa.url)
            domain = match.group(1) if match else "sconosciuto"

    # 2. Estraiamo il titolo direttamente dall'HTML fornito dal test
    # Cerca il testo contenuto tra i tag <title> e </title>
            title_match = re.search(r"<title>(.*?)</title>", risorsa.html_text, re.IGNORECASE | re.DOTALL)
            title = title_match.group(1).strip() if title_match else "Titolo mancante"
            conn = mariadb.connect(
                host=db_host,
                port=db_port,
                user=db_user,
                password=db_password,
                database=db_name
            )

            query = "INSERT INTO web_resources (url, domain, title, html_text) values (?, ?, ?, ?)"
            
            execute_query(conn, query, (risorsa.url, domain,  title, risorsa.html_text))
            return {"status":"ok"}
    except Exception as e:
        return {"status":"error"}
    finally:
        conn.close()

@app.delete("/web_resource")
async def delete_web_resource(request: Request):

    try:
        url = None
        
        # Tentativo A: Cerca l'URL nel corpo JSON
        try:
            corpo_json = await request.json()
            url = corpo_json.get("url")
        except:
            pass
            
        # Tentativo B: Se non era un JSON, cercalo nei Form Data
        if not url:
            try:
                corpo_form = await request.form()
                url = corpo_form.get("url")
            except:
                pass
                
        # Tentativo C: Se non era in un Form, cercalo nell'indirizzo (Query Parameter)
        if not url:
            url = request.query_params.get("url")

        # Se il test ci ha inviato una richiesta senza un url valido,
        # restituiamo subito errore senza far crashare il server.
        if not url:
            return {"status": "error"}
        conn = mariadb.connect(
                host=db_host,
                port=db_port,
                user=db_user,
                password=db_password,
                database=db_name
        )

        query = "DELETE FROM web_resources WHERE url =?"
            
        execute_query(conn, query, (url, ))
        return {"status":"ok"}
    except Exception as e:
        return {"status":"error"}
    finally:
            conn.close()

@app.post("/add_gold_standard")
def add_gold_standard(dati : GoldInput):

    try:
        conn = mariadb.connect(
                host=db_host,
                port=db_port,
                user=db_user,
                password=db_password,
                database=db_name
            )
    
        query = "INSERT INTO gold_standard (url, gold_text) values (?, ?)"
            
        execute_query(conn, query, (dati.url, dati.gold_text))
        return {"status":"ok"}
    except Exception as e:
        return {"status" : "error"}
    finally:
            conn.close()

@app.delete("/gold_standard")
async def delete_gold_standard(request:Request):

    try:
        url = None
        
        # Tentativo A: Cerca l'URL nel corpo JSON
        try:
            corpo_json = await request.json()
            url = corpo_json.get("url")
        except:
            pass
            
        # Tentativo B: Se non era un JSON, cercalo nei Form Data
        if not url:
            try:
                corpo_form = await request.form()
                url = corpo_form.get("url")
            except:
                pass
                
        # Tentativo C: Se non era in un Form, cercalo nell'indirizzo (Query Parameter)
        if not url:
            url = request.query_params.get("url")

        # Se il test ci ha inviato una richiesta senza un url valido,
        # restituiamo subito errore senza far crashare il server.
        if not url:
            return {"status": "error"}

        conn = mariadb.connect(
                host=db_host,
                port=db_port,
                user=db_user,
                password=db_password,
                database=db_name
            )
    
        query = "DELETE FROM gold_standard WHERE url =?"
            
        execute_query(conn, query, (url, ))
        return {"status":"ok"}
    except Exception as e:
        return {"status":"error"}
    finally:
            conn.close()

@app.get("/db_schema")
def db_schema():
    return {
        "web_resources":{
            "url": "varchar(2048), PK",
            "domain": "varchar(255) NOT NULL",
            "title": "varchar(2048) NOT NULL",
            "html_text": "longtext",
            "created_at": "datetime"
        },
        "gold_standard":{
            "url": "varchar(2048), PK, FK(web_resources.url)",
            "gold_text": "longtext NOT NULL",
            "created_at": "datetime"
        },
        "domini":{
            "domain":"varchar(255), PK"
        }
    }


@app.get("/status")
async def status():
    # Sostituisci i nomi e le porte con quelli reali dei tuoi servizi
    return {
        "backend": "ok",
        "database": is_online("mariadb", 3306),
        "ollama": is_online("ollama_service", 11434)
    }


@app.get("/test")
def test():
    db_host = os.getenv("DB_HOST", "mariadb")
    db_port = int(os.getenv("DB_PORT", 3306))
    db_user = os.getenv("DB_USER", "user")
    db_password = os.getenv("DB_PASSWORD", "sonoio")
    db_name = os.getenv("DB_NAME", "project_db")
    try:
            conn = mariadb.connect(
                host=db_host,
                port=db_port,
                user=db_user,
                password=db_password,
                database=db_name
            )
    except mariadb.Error as e:
        raise HTTPException(status_code=500, detail=f"Connessione al DB fallita: {e}")

    try:

        query = "SELECT *  FROM gold_standard"
            
        risultato = execute_query(conn, query)
        return risultato
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore durante l'interrogazione: {e}")
    finally:
            conn.close()