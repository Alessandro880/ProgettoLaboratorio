import requests # IMPORTANTE: Aggiungi questa libreria
from pathlib import Path
from fastapi import FastAPI, Request
from pydantic import BaseModel
from fastapi.templating import Jinja2Templates

app = FastAPI()

# (La classe Pagina la puoi tenere per il futuro, ma per ora non è strettamente necessaria)

cartella_script = Path(__file__).parent.resolve()
cartella_templates = cartella_script / "templates"
templates = Jinja2Templates(directory=str(cartella_templates))

@app.get("/")
def home(request: Request):
    # Passa i parametri usando esplicitamente i loro nomi (request=..., name=...)
    return templates.TemplateResponse(request=request, name="home.html")

@app.get("/parse")
def esegui_parser(request: Request, url: str):
    # NOTA BENE: Se non stai usando Docker, l'indirizzo è 127.0.0.1, non "backend"
    # Abbiamo attaccato "url" alla fine della stringa, come si aspetta il backend!
    url_backend = f"http://127.0.0.1:8003/api/parse/{url}"
    
    try:
        # Usiamo requests.get per interrogare il nostro backend
        risposta_backend = requests.get(url_backend)
        
        # Genera un errore se il backend restituisce 404 o 500
        risposta_backend.raise_for_status() 
        
        dizionario_risultato = risposta_backend.json()
        
        # Per ora stampiamo il JSON a schermo, 
        # il prossimo passo sarà passarlo a un altro template HTML!
        return dizionario_risultato["parsed_txt"]
        
    except requests.exceptions.RequestException as e:
        return {"error": f"Errore di connessione al backend: {str(e)}"}