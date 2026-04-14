import json
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from fastapi.templating import Jinja2Templates

app = FastAPI()

class Pagina(BaseModel):
    url:str
    title:str
    domain:str
    html_txt:str
    parsed_txt:str


cartella_script = Path(__file__).parent.resolve()
cartella_templates = cartella_script / "templates"
templates = Jinja2Templates(directory=str(cartella_templates))

@app.get("/")
def home(request: Request):
    # Mostra l'index.html all'utente
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/parse")
def esegui_parser(request: Request, url:str):
    url_backend = "http://backend:8000/api/parse"
    try:
        # Il frontend passa l'url al backend (come abbiamo visto prima)
        payload = {"url_da_cercare": url}
        risposta_backend = request.post(url_backend, json=payload)
        risposta_backend.raise_for_status()
        
        dizionario_risultato = risposta_backend.json()
        
        # Ora puoi mostrare i risultati. 
        # (Potresti restituire un altro template HTML passando i risultati, 
        # oppure semplicemente stampare il JSON sullo schermo)
        print(dizionario_risultato)
        return dizionario_risultato
        
    except request.exceptions.RequestException as e:
        return {"error": f"Errore: {str(e)}"}