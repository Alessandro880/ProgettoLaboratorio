
import sys
import re
import json
from fastapi import FastAPI, Request, HTTPException, Form, Query
from pathlib import Path
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import os
import requests
from ollama import Client
import mariadb
from contextlib import asynccontextmanager
from typing import Optional
import socket
import time
from fastapi import BackgroundTasks
import threading

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
ollama_url = os.getenv("OLLAMA_HOST", "http://ollama:11434")
ollama_client = Client(host=ollama_url)

db_host = os.getenv("DB_HOST", "mariadb")
db_port = int(os.getenv("DB_PORT", 3306))
db_user = os.getenv("DB_USER", "user")
db_password = os.getenv("DB_PASSWORD", "sonoio")
db_name = os.getenv("DB_NAME", "project_db")

def execute_query(conn: mariadb.Connection, query: str, data: tuple = None):
    """Esegue una query e restituisce i risultati se è una SELECT"""
    with conn.cursor() as cursor:
        if data:
            cursor.execute(query, data)
        else:
            cursor.execute(query)

        if cursor.description is not None:
            result = cursor.fetchall()
        else:
            result = []

    conn.commit()
    return result


def calcola_e_salva_valutazione_in_background(url: str, gold_text: str):
    conn = None
    try:
        conn = mariadb.connect(host=db_host, port=db_port, user=db_user, password=db_password, database=db_name)
        cur = conn.cursor()
        
        cur.execute("SELECT domain, html_text FROM web_resources WHERE url=?", (url,))
        row = cur.fetchone()
        if not row: return
            
        domain, html_text = row[0], row[1]
        
        if "wikipedia.org" in domain: testo = clean_wikipedia_text(html_text)
        elif "olympics.com" in domain: testo = clean_olympics_text(html_text)
        elif "governo.it" in domain: testo = clean_governo_text(html_text)
        elif "lospiegone.com" in domain: testo = clean_lospiegone_text(html_text)
        else: testo = clean_text(html_text)

        testo_parsato = str(testo[1]) if isinstance(testo, (list, tuple)) and len(testo) > 1 else str(testo.get("text", "")) if isinstance(testo, dict) else str(testo)
        
        parsed_pulito = rimuovi_markdown(testo_parsato)
        gold_pulito = rimuovi_markdown(gold_text)
        
        w_token = token_level_eval(parsed_pulito, gold_pulito)
        p = w_token.get("precision", 0.0)
        r = w_token.get("recall", 0.0)
        f1 = w_token.get("f1", 0.0)

        w_seq = sequence_similarity_eval(parsed_pulito, gold_pulito)
        seq_ratio = w_seq.get("sequence_similarity_ratio", 0.0)
        seq_match = w_seq.get("longest_contiguous_match_chars", 0.0)
        seq_perf = bool(w_seq.get("is_perfect_match", False))

        try:
            limite_1 = min(400, len(parsed_pulito)//4)
            limite_2 = min(400, len(gold_pulito)//4)
            prompt = f"""Confronta i testi. Rispondi SOLO in JSON con "model_name": "{MODEL}", "judge_score" (intero da 0 a 5).
            T1: {parsed_pulito[:limite_1]}
            T2: {gold_pulito[:limite_2]}"""
            
            response = ollama_client.generate(model=MODEL, prompt=prompt, format="json", options={"temperature": 0.0})
            res_json = json.loads(response['response'])
            judge = float(res_json.get("judge_score", 0.0))
        except Exception:
            judge = 0.0

        cur.execute("""
            INSERT INTO evaluations (url, precision_val, recall_val, f1_val, seq_ratio, seq_match, seq_perfect, judge_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON DUPLICATE KEY UPDATE 
            precision_val=VALUES(precision_val), recall_val=VALUES(recall_val), f1_val=VALUES(f1_val), 
            seq_ratio=VALUES(seq_ratio), seq_match=VALUES(seq_match), seq_perfect=VALUES(seq_perfect), judge_score=VALUES(judge_score)
        """, (url, p, r, f1, seq_ratio, seq_match, seq_perf, judge))
        
        conn.commit()
    except Exception as e:
        print(f"Errore calcolo per {url}: {e}")
    finally:
        if conn: conn.close()



def calcola_valutazioni_mancanti():
    """Cerca nel database i documenti che non hanno ancora una valutazione e la calcola"""
    time.sleep(5)  
    conn = None
    try:
        conn = mariadb.connect(host=db_host, port=db_port, user=db_user, password=db_password, database=db_name)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT g.url, g.gold_text 
            FROM gold_standard g 
            LEFT JOIN evaluations e ON g.url = e.url 
            WHERE e.url IS NULL
        """)
        mancanti = cur.fetchall()
        
        if mancanti:
            print(f"Trovate {len(mancanti)} risorse senza valutazione. Inizio il calcolo in background...")
            for row in mancanti:
                calcola_e_salva_valutazione_in_background(row[0], row[1])
            print("Calcolo background completato!")
            
    except Exception as e:
        print(f"Errore nel thread di background: {e}")
    finally:
        if conn: conn.close()


# --- FUNZIONE DI INIZIALIZZAZIONE ---
def inizializza_e_popola_db():
    percorso_gs = "/app/gs_data"
    percorso_domains = "/app/domains.json"

    db_host = os.getenv("DB_HOST", "mariadb")
    db_port = int(os.getenv("DB_PORT", 3306))
    db_user = os.getenv("DB_USER", "user") 
    db_password = os.getenv("DB_PASSWORD", "sonoio") 
    db_name = os.getenv("DB_NAME", "project_db")
    
    print("Tentativo di connessione a MariaDB...")
    
    connection = None
    for i in range(10):
        try:
            connection = mariadb.connect(host=db_host, port=db_port, user=db_user, password=db_password, database=db_name)
            print("Connessione a MariaDB riuscita!")
            break
        except mariadb.Error as e:
            print(f"Database non ancora pronto ({e}) - Tentativo {i+1}/10... Attendo 3 secondi.")
            time.sleep(3)
            
    if not connection:
        print("Impossibile connettersi al database.")
        return

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS web_resources (
                    url VARCHAR(2048) CHARACTER SET ascii PRIMARY KEY,
                    domain VARCHAR(255) NOT NULL,
                    title VARCHAR(2048) NOT NULL,
                    html_text LONGTEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS gold_standard (
                    url VARCHAR(2048) CHARACTER SET ascii PRIMARY KEY,
                    gold_text LONGTEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_gold_web FOREIGN KEY (url) REFERENCES web_resources(url) ON DELETE CASCADE
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS evaluations (
                    url VARCHAR(2048) CHARACTER SET ascii PRIMARY KEY,
                    precision_val FLOAT,
                    recall_val FLOAT,
                    f1_val FLOAT,
                    seq_ratio FLOAT,
                    seq_match FLOAT,
                    seq_perfect BOOLEAN,
                    judge_score INT,
                    CONSTRAINT fk_eval_gold FOREIGN KEY (url) REFERENCES gold_standard(url) ON DELETE CASCADE
                )
            """)
            connection.commit()

        with open(percorso_domains, "r", encoding="utf-8") as f:
            dati_domains = json.load(f)
            domini = dati_domains.get("domains", []) if isinstance(dati_domains, dict) else dati_domains

        with connection.cursor() as cursor:
            for domain in domini:
                file_json = f"{percorso_gs}/{domain}.json"
                if not os.path.exists(file_json): continue
                
                with open(file_json, "r", encoding="utf-8") as f:
                    dati_gs = json.load(f)
                    pagine = dati_gs.get("gold_standard", [])
                    
                    for pagina in pagine:
                        url = pagina.get("url")
                        title = pagina.get("title", "Titolo mancante")
                        html_text = pagina.get("html_text", "")
                        gold_text = pagina.get("gold_text", "")
                        if not url: continue
                        
                        cursor.execute("INSERT IGNORE INTO web_resources (url, domain, title, html_text) VALUES (?, ?, ?, ?)", (url, domain, title, html_text))
                        cursor.execute("INSERT IGNORE INTO gold_standard (url, gold_text) VALUES (?, ?)", (url, gold_text))
            
            connection.commit()
            print("Popolamento DB completato!")
            
    except Exception as e:
        print(f"Errore durante il popolamento: {e}")
    finally:
        connection.close()

    threading.Thread(target=calcola_valutazioni_mancanti).start()


@asynccontextmanager
async def lifespan(app: FastAPI):
    inizializza_e_popola_db()
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



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
        browser_cfg = BrowserConfig(headless=True)
        crawler_cfg = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, delay_before_return_html=2.0, magic=True)
        try:
            async with AsyncWebCrawler(config=browser_cfg) as crawler:
                result = await crawler.arun(url=url_search, config=crawler_cfg)
                if not result.html:
                    raise HTTPException(status_code=400, detail="URL irraggiungibile o pagina vuota")
                html_text = result.html
                markdown_di_backup = getattr(result, 'markdown', "") 
        except HTTPException:
            raise 
        except Exception as e:
            raise HTTPException(status_code=400, detail="URL irraggiungibile")

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
    evaluate prende in ingreso un DatiInput, formato da due stringhe e ne esegue la valutazione
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
        if not url or url == "None":
            raise HTTPException(status_code=400, detail="URL vuoto o mancante")

        conn = mariadb.connect(
            host=db_host, port=db_port, user=db_user,
            password=db_password, database=db_name
        )

        query = """
            SELECT w.domain, w.title, w.html_text, j.gold_text 
            FROM web_resources as w 
            JOIN gold_standard as j on w.url=j.url 
            WHERE w.url = ?
        """
        risultato = execute_query(conn, query, (url,))
        
        if risultato:
            return {
                "url": url,
                "domain": str(risultato[0][0] or ""),
                "title": str(risultato[0][1] or ""),
                "html_text": str(risultato[0][2] or ""),
                "gold_text": str(risultato[0][3] or "")
            }

        url_search = url if url.startswith("http") else "https://" + url
        pattern = r"https?://((?:www\.)?[^/]+)"
        match = re.search(pattern, url_search)
        
        if not match:
            raise HTTPException(status_code=400, detail="URL non valido")
            
        domain = match.group(1).lower()

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
    la valutazione tramite token_level_eval, sequence_similarity_eval e LLM-as-judge, calcolandone la media
"""
@app.get("/full_gs_eval")
def full_gs_eval(domain: str):
    percorso_gs = "/app/gs_data"
    percorso_domains = "/app/domains.json"

    try:
        with open(percorso_domains, "r", encoding="utf-8") as f:
            dati_json = json.load(f)
            domini = dati_json.get("domains", dati_json) if isinstance(dati_json, dict) else dati_json
    except FileNotFoundError:
        domini = []
        
    if domain not in domini: 
        raise HTTPException(status_code=404, detail="Dominio non supportato!")

    file = f"{percorso_gs}/{domain}.json"
    
    try:
        with open(file, "r", encoding="utf-8") as f:
            dati_json = json.load(f)
            pagine = dati_json.get("gold_standard", [])
            
            if not pagine:
                raise HTTPException(status_code=404, detail="Il file GS è vuoto")

        conn = None
        try:
            conn = mariadb.connect(host=db_host, port=db_port, user=db_user, password=db_password, database=db_name)
            cur = conn.cursor()

            cur.execute("""
                SELECT e.url 
                FROM evaluations e 
                JOIN web_resources w ON e.url = w.url 
                WHERE w.domain = ?
            """, (domain,))
            
            url_valutati = set(row[0] for row in cur.fetchall())

            for page in pagine:
                url = page.get("url", "")
                
                if url not in url_valutati:
                    html = page.get("html_text", "")
                    gold = page.get("gold_text", "")
                    
                    if "wikipedia.org" in domain: testo = clean_wikipedia_text(html)
                    elif "olympics.com" in domain: testo = clean_olympics_text(html)
                    elif "governo.it" in domain: testo = clean_governo_text(html)
                    elif "lospiegone.com" in domain: testo = clean_lospiegone_text(html)
                    else: testo = clean_text(html)
                    
                    testo_parsato = str(testo[1]) if isinstance(testo, (list, tuple)) and len(testo) > 1 else str(testo.get("text", "")) if isinstance(testo, dict) else str(testo)

                    w_token_eval = token_level_eval(testo_parsato, gold)
                    p = w_token_eval.get("precision", 0.0)
                    r = w_token_eval.get("recall", 0.0)
                    f1 = w_token_eval.get("f1", 0.0)

                    w_sequence_sim = sequence_similarity_eval(testo_parsato, gold)
                    seq_ratio = w_sequence_sim.get("sequence_similarity_ratio", 0.0)
                    seq_match = w_sequence_sim.get("longest_contiguous_match_chars", 0.0)
                    seq_perf = bool(w_sequence_sim.get("is_perfect_match", False))

                    try:
                        testo_1 = testo_parsato[:400]
                        testo_2 = gold[:400]
                        prompt = f"""Confronta i testi. Rispondi SOLO in JSON con "model_name": "{MODEL}", "judge_score" (intero da 1 a 5).
                        T1: {testo_1}
                        T2: {testo_2}"""
                        
                        response = ollama_client.generate(model=MODEL, prompt=prompt, format="json", options={"temperature": 0.0})
                        res_json = json.loads(response['response'])
                        
                        score = int(res_json.get("judge_score", 1))
                        if score < 1: score = 1
                        if score > 5: score = 5
                    except Exception:
                        score = 1
                        
                    cur.execute("""
                        INSERT INTO evaluations (url, precision_val, recall_val, f1_val, seq_ratio, seq_match, seq_perfect, judge_score)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ON DUPLICATE KEY UPDATE 
                        precision_val=VALUES(precision_val), recall_val=VALUES(recall_val), f1_val=VALUES(f1_val), 
                        seq_ratio=VALUES(seq_ratio), seq_match=VALUES(seq_match), seq_perfect=VALUES(seq_perfect), judge_score=VALUES(judge_score)
                    """, (url, p, r, f1, seq_ratio, seq_match, seq_perf, score))
                    
                    conn.commit()
                    url_valutati.add(url) 

            cur.execute("""
                SELECT 
                    AVG(e.precision_val), 
                    AVG(e.recall_val), 
                    AVG(e.f1_val), 
                    AVG(e.seq_ratio), 
                    AVG(e.seq_match), 
                    MIN(e.seq_perfect), 
                    AVG(e.judge_score)
                FROM web_resources w
                JOIN evaluations e ON w.url = e.url
                WHERE w.domain = ?
            """, (domain,))
            
            row = cur.fetchone()
            
            return {
                "token_level_eval": {
                    "precision": round(row[0] or 0.0, 4),
                    "recall": round(row[1] or 0.0, 4),
                    "f1": round(row[2] or 0.0, 4)
                },
                "sequence_similarity_eval": {
                    "sequence_similarity_ratio": round(row[3] or 0.0, 4),
                    "longest_contiguous_match_chars": round(row[4] or 0.0, 4),
                    "is_perfect_match": bool(row[5]) if row[5] is not None else False
                },
                "judge_score": round(row[6] or 0.0, 4)
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Errore DB interno: {e}")
        finally:
            if conn: conn.close()
            
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Problema apertura {domain}.json")


@app.post("/evaluate_judge")
def evaluate_judge(dati: DatiInput): 
    try:
        prompt = f"""Confronta i testi. Rispondi SOLO ed ESCLUSIVAMENTE in JSON valido con 3 chiavi:
        "model_name": "{MODEL}",
        "judge_score": (intero tra 1 e 5),
        "judge_feedback": (stringa con una breve spiegazione del voto).
        
        T1: {dati.parsed_text[:400]}
        T2: {dati.gold_text[:400]}"""
        
        response = ollama_client.generate(
            model=MODEL, 
            prompt=prompt, 
            format="json",
            options={"temperature": 0.0}
        )
        
        res_json = json.loads(response['response'])
        
        feedback = str(res_json.get("judge_feedback", "Nessun feedback fornito."))
        
        try:
            score = int(res_json.get("judge_score", 1))
        except (ValueError, TypeError):
            score = 1
            
        if score < 1:
            score = 1
        elif score > 5:
            score = 5
        
        return {
            "model_name": MODEL,
            "judge_score": score,  
            "judge_feedback": feedback
        }

    except Exception as e:
        return {
            "model_name": MODEL,
            "judge_score": 1,  
            "judge_feedback": "Errore durante la valutazione"
        }


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
        
        lista_urls = [riga[0] for riga in risultati_grezzi]
        
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
    conn = None
    try:
            pattern_dominio = r"^(?:https?://)?(?:www\.)?([^/]+)"
            match = re.search(pattern_dominio, risorsa.url)
            domain = match.group(1) if match else "sconosciuto"

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
        if conn is not None:
            conn.close()


@app.delete("/web_resource")
async def delete_web_resource(request: Request):

    try:
        url = None
        try:
            corpo_json = await request.json()
            url = corpo_json.get("url")
        except:
            pass
            
        if not url:
            try:
                corpo_form = await request.form()
                url = corpo_form.get("url")
            except:
                pass
                
        if not url:
            url = request.query_params.get("url")

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
def add_gold_standard(dati : GoldInput, background_tasks: BackgroundTasks):

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
        background_tasks.add_task(calcola_e_salva_valutazione_in_background, dati.url, dati.gold_text)
        return {"status":"ok"}
    except Exception as e:
        return {"status" : "error"}
    finally:
            conn.close()
    

@app.delete("/gold_standard")
async def delete_gold_standard(request:Request):

    try:
        url = None
        
        try:
            corpo_json = await request.json()
            url = corpo_json.get("url")
        except:
            pass
            
        if not url:
            try:
                corpo_form = await request.form()
                url = corpo_form.get("url")
            except:
                pass
                
        if not url:
            url = request.query_params.get("url")

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
        "evaluations":{
            "url" : "varchar(255), PK",
            "precision_val" : "FLOAT",
            "recall_val" :  "FLOAT",
            "f1_val" : "FLOAT",
            "seq_ratio":  "FLOAT",
            "seq_match" : "FLOAT",
            "seq_perfect"  : "BOOLEAN",
            "judge_score" : "INT",
            "judge_score" :  "FLOAT"
        }
    }


@app.get("/status")
async def status():
    return {
        "backend": "ok",
        "database": is_online("mariadb", 3306),
        "ollama": is_online("ollama_service", 11434)
    }


@app.get("/db_stats")
def db_stats():
    conn = None
    try:
        conn = mariadb.connect(host=db_host, port=db_port, user=db_user, password=db_password, database=db_name)
        cur = conn.cursor()

        web_res_counts, gs_counts, avg_eval, avg_eval_judge = {}, {}, {}, {}
        tutti_domini = set()

        cur.execute("SELECT domain, COUNT(*) FROM web_resources GROUP BY domain")
        for row in cur.fetchall():
            tutti_domini.add(row[0])
            web_res_counts[row[0]] = row[1]

        cur.execute("SELECT w.domain, COUNT(*) FROM gold_standard g JOIN web_resources w ON g.url = w.url GROUP BY w.domain")
        for row in cur.fetchall():
            tutti_domini.add(row[0])
            gs_counts[row[0]] = row[1]

        for dom in tutti_domini:
            if dom not in web_res_counts: web_res_counts[dom] = 0
            if dom not in gs_counts: gs_counts[dom] = 0
            avg_eval[dom] = {"token_level_eval": {"precision": 0.0, "recall": 0.0, "f1": 0.0}}
            avg_eval_judge[dom] = {"judge_score": 0.0}

        cur.execute("""
            SELECT w.domain, 
                   AVG(e.precision_val), 
                   AVG(e.recall_val), 
                   AVG(e.f1_val), 
                   AVG(e.judge_score)
            FROM web_resources w
            JOIN evaluations e ON w.url = e.url
            GROUP BY w.domain
        """)
        
        for row in cur.fetchall():
            dom = row[0]
            if dom in avg_eval:
                avg_eval[dom]["token_level_eval"] = {
                    "precision": round(row[1] or 0.0, 4),
                    "recall": round(row[2] or 0.0, 4),
                    "f1": round(row[3] or 0.0, 4)
                }
                avg_eval_judge[dom]["judge_score"] = round(row[4] or 0.0, 4)

        return {
            "web_resources": web_res_counts,
            "gold_standard": gs_counts,
            "avg_eval": avg_eval,
            "avg_eval_judge": avg_eval_judge
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore interno: {e}")
    finally:
        if conn: conn.close()