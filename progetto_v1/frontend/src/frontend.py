import requests # IMPORTANTE: Aggiungi questa libreria
from pathlib import Path
from fastapi import FastAPI, Request, Form, HTTPException
from pydantic import BaseModel
from fastapi.templating import Jinja2Templates
import json
import re
import os

app = FastAPI()

class DatiInput(BaseModel):
    parsed_text: str
    gold_text: str

# (La classe Pagina la puoi tenere per il futuro, ma per ora non è strettamente necessaria)

cartella_script = Path(__file__).parent.resolve()
cartella_radice = cartella_script.parent.parent
#percorso_domains = cartella_radice / "domains.json"
#percorso_gs = cartella_radice / "gs_data"

cartella_templates = cartella_script / "templates"
templates = Jinja2Templates(directory=str(cartella_templates))



@app.get("/")
def home(request: Request):
    # Passa i parametri usando esplicitamente i loro nomi (request=..., name=...)
    return templates.TemplateResponse(request=request, name="home.html")

@app.get("/parse")
def esegui_parser(request: Request, url: str):

    backend_url = os.getenv("BACKEND_URL", "http://backend:8003")
    url_backend = f"{backend_url}/parse"
    parametri={
        "url":url
    }
    
    try:
        # Usiamo requests.get per interrogare il nostro backend
        risposta_backend = requests.get(url_backend, params=parametri)
        
        # Genera un errore se il backend restituisce 404 o 500
        risposta_backend.raise_for_status() 
        
        dizionario_risultato = risposta_backend.json()
        return dizionario_risultato
        
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail="Backend non raggiungibile")

@app.post("/parse")
async def parser_post(
    request: Request, 
    # Dicendo Form(...), FastAPI sa che i dati arrivano dal corpo della richiesta HTML
    url: str = Form(..., examples=[""]), 
    html_text: str = Form(..., examples=[""])
):
    backend_url = os.getenv("BACKEND_URL", "http://backend:8003")
    url_backend = f"{backend_url}/parse"
    
    # 1. Prepariamo il pacchetto da spedire al backend
    payload_dati = {
        "url": url,
        "html_text": html_text
    }
    
    try:
        # 2. Spediamo i dati come JSON (QUESTO È PERFETTO!)
        risposta_backend = requests.post(url_backend, json=payload_dati)
        if not risposta_backend.ok:
            raise HTTPException(status_code=risposta_backend.status_code, detail=risposta_backend.json())
               
        risultato = risposta_backend.json()
        
        # Per ora stampiamo il JSON a schermo
        return risultato
        
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail="Backend non raggiungibile")


@app.get("/domains")
def mostra_domini(request: Request):
    backend_url = os.getenv("BACKEND_URL", "http://backend:8003")
    url_backend = f"{backend_url}/domains"

    try:
        # Usiamo requests.get per interrogare il nostro backend
        risposta_backend = requests.get(url_backend)
        
        if not risposta_backend.ok:
            raise HTTPException(status_code=risposta_backend.status_code, detail=risposta_backend.json())
            
        return risposta_backend.json()
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=500, detail="Backend non raggiungibile")
        
    except requests.exceptions.RequestException as e:
        return {"error": f"Errore di connessione al backend: {str(e)}"}
    

    # return templates.TemplateResponse(
    #     request=request, 
    #     name="domini.html", 
    #     context={"elenco_domini": domini}
    # )

@app.get("/gold_standard")
def mostra_gold_standard(url:str, request:Request):
    backend_url = os.getenv("BACKEND_URL", "http://backend:8003")
    url_backend = f"{backend_url}/gold_standard"
    parametri = {
        "url": url
    }
    try:
        # Usiamo requests.get per interrogare il nostro backend
        risposta_backend = requests.get(url_backend, params=parametri)
        if not risposta_backend.ok:
            raise HTTPException(status_code=risposta_backend.status_code, detail=risposta_backend.json())
            
        return risposta_backend.json()
      
        
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail="Backend non raggiungibile")

@app.get("/full_gold_standard")
def mostra_full_gold_standard(domain:str, request:Request):
    backend_url = os.getenv("BACKEND_URL", "http://backend:8003")
    url_backend = f"{backend_url}/full_gold_standard"
    parametri = {
        "domain": domain
    }
    try:
        # Usiamo requests.get per interrogare il nostro backend
        risposta_backend = requests.get(url_backend, params=parametri)
        if not risposta_backend.ok:
            raise HTTPException(status_code=risposta_backend.status_code, detail=risposta_backend.json())
            
        return risposta_backend.json()
        return dizionario_risultato
        
        
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail="Backend non raggiungibile")


@app.post("/evaluate")
def evaluate(request:Request, dati:DatiInput):
    #url_backend = f"http://127.0.0.1:8003/evaluate/"
    backend_url = os.getenv("BACKEND_URL", "http://backend:8003")
    url_backend = f"{backend_url}/evaluate"
    payload_dati = {
    "parsed_text": dati.parsed_text,
    "gold_text": dati.gold_text
}
    try:
        # Usiamo requests.get per interrogare il nostro backend
        risposta_backend = requests.post(url_backend, json=payload_dati)
        if not risposta_backend.ok:
            raise HTTPException(status_code=risposta_backend.status_code, detail=risposta_backend.json())
            
        return risposta_backend.json()
        
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail="Backend non raggiungibile")


@app.get("/full_gs_eval")
def full_gs_eval(domain:str):
    backend_url = os.getenv("BACKEND_URL", "http://backend:8003")
    url_backend = f"{backend_url}/full_gs_eval"
    payload_dati={
        "domain":domain
    }
    try:
        # Usiamo requests.get per interrogare il nostro backend
        risposta_backend = requests.post(url_backend, params=payload_dati)
        if not risposta_backend.ok:
            raise HTTPException(status_code=risposta_backend.status_code, detail=risposta_backend.json())
            
        return risposta_backend.json()
        
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail="Backend non raggiungibile")