# import requests 
# from pathlib import Path
# from fastapi import FastAPI, Request, Form, HTTPException
# from pydantic import BaseModel
# from fastapi.templating import Jinja2Templates
# import json
# import re
# import os



# """
#     Frontend Web Application (FastAPI) - Porta 8004

#     Interfaccia utente (UI) del progetto.
#     Gestiste le varie richieste sia tramite http://127.0.0.1:8004/docs per comunicare
#     con il backend, sia tramite template HTML con jinja2
# """

# app = FastAPI()

# """
#     DatiInput viene usata nel @app.post("/evaluate")
#     prendere in ingresso le due stringhe da confrontare, dove gold_text è la stringa corretta
#     serve per passarlo come parametri al backend
# """
# class DatiInput(BaseModel):
#     parsed_text: str
#     gold_text: str


# cartella_script = Path(__file__).parent.resolve()
# cartella_radice = cartella_script.parent.parent


# cartella_templates = cartella_script / "templates"
# templates = Jinja2Templates(directory=str(cartella_templates))


# # @app.get("/") permette di connettersi all'interfaccia grafica generata tramite jinja2
# @app.get("/")
# def home(request: Request):
#     return templates.TemplateResponse(request=request, name="home.html")

# # effettua la richiesta al backend per il parser tramite url in ingresso
# @app.get("/parse")
# def esegui_parser(request: Request, url: str):

#     backend_url = os.getenv("BACKEND_URL", "http://backend:8003")
#     url_backend = f"{backend_url}/parse"
#     parametri={
#         "url":url
#     }
    
#     try:
#         risposta_backend = requests.get(url_backend, params=parametri)
#         risposta_backend.raise_for_status() 
#         dizionario_risultato = risposta_backend.json()
#         return dizionario_risultato
        
#     except requests.exceptions.RequestException as e:
#         raise HTTPException(status_code=500, detail="Backend non raggiungibile")


# #esegue il parser inviando al backend un url e il testo html
# @app.post("/parse")
# async def parser_post(request: Request, url: str = Form(..., examples=[""]), html_text: str = Form(..., examples=[""])):
#     backend_url = os.getenv("BACKEND_URL", "http://backend:8003")
#     url_backend = f"{backend_url}/parse"
    
#     payload_dati = {
#         "url": url,
#         "html_text": html_text
#     }
    
#     try:
#         risposta_backend = requests.post(url_backend, json=payload_dati)
#         if not risposta_backend.ok:
#             raise HTTPException(status_code=risposta_backend.status_code, detail=risposta_backend.json())
               
#         risultato = risposta_backend.json()
#         return risultato
        
#     except requests.exceptions.RequestException as e:
#         raise HTTPException(status_code=500, detail="Backend non raggiungibile")


# # richiede tutti i domini presenti al backend
# @app.get("/domains")
# def mostra_domini(request: Request):
#     backend_url = os.getenv("BACKEND_URL", "http://backend:8003")
#     url_backend = f"{backend_url}/domains"

#     try:
#         risposta_backend = requests.get(url_backend)
        
#         if not risposta_backend.ok:
#             raise HTTPException(status_code=risposta_backend.status_code, detail=risposta_backend.json())
            
#         return risposta_backend.json()
#     except requests.exceptions.ConnectionError:
#         raise HTTPException(status_code=500, detail="Backend non raggiungibile")
        
#     except requests.exceptions.RequestException as e:
#         return {"error": f"Errore di connessione al backend: {str(e)}"}
    

#     # return templates.TemplateResponse(
#     #     request=request, 
#     #     name="domini.html", 
#     #     context={"elenco_domini": domini}
#     # )


# # tramite url in ingresso, restituisce il gs di una determinata pagina
# @app.get("/gold_standard")
# def mostra_gold_standard(url:str, request:Request):
#     backend_url = os.getenv("BACKEND_URL", "http://backend:8003")
#     url_backend = f"{backend_url}/gold_standard"
#     parametri = {
#         "url": url
#     }
#     try:
#         risposta_backend = requests.get(url_backend, params=parametri)
#         if not risposta_backend.ok:
#             raise HTTPException(status_code=risposta_backend.status_code, detail=risposta_backend.json())
            
#         return risposta_backend.json()
#     except requests.exceptions.RequestException as e:
#         raise HTTPException(status_code=500, detail="Backend non raggiungibile")


# #dato un determinato dominio, resatituisce l'intero gs di quel dominio
# @app.get("/full_gold_standard")
# def mostra_full_gold_standard(domain:str, request:Request):
#     backend_url = os.getenv("BACKEND_URL", "http://backend:8003")
#     url_backend = f"{backend_url}/full_gold_standard"
#     parametri = {
#         "domain": domain
#     }
#     try:
#         risposta_backend = requests.get(url_backend, params=parametri)
#         if not risposta_backend.ok:
#             raise HTTPException(status_code=risposta_backend.status_code, detail=risposta_backend.json())
            
#         return risposta_backend.json()
#     except requests.exceptions.RequestException as e:
#         raise HTTPException(status_code=500, detail="Backend non raggiungibile")


# # dato in ingresso DatiInput ( due stringhe ) applica i due algoritmi di valutazione
# @app.post("/evaluate")
# def evaluate(request:Request, dati:DatiInput):
#     backend_url = os.getenv("BACKEND_URL", "http://backend:8003")
#     url_backend = f"{backend_url}/evaluate"
#     payload_dati = {
#     "parsed_text": dati.parsed_text,
#     "gold_text": dati.gold_text
# }
#     try:
#         risposta_backend = requests.post(url_backend, json=payload_dati)
#         if not risposta_backend.ok:
#             raise HTTPException(status_code=risposta_backend.status_code, detail=risposta_backend.json())
            
#         return risposta_backend.json()
#     except requests.exceptions.RequestException as e:
#         raise HTTPException(status_code=500, detail="Backend non raggiungibile")


# # applica ad un interio gs di un dominio le valutazioni, ritornando la media
# @app.get("/full_gs_eval")
# def full_gs_eval(domain:str):
#     backend_url = os.getenv("BACKEND_URL", "http://backend:8003")
#     url_backend = f"{backend_url}/full_gs_eval"
#     payload_dati={
#         "domain":domain
#     }
#     try:
#         risposta_backend = requests.get(url_backend, params=payload_dati)
#         if not risposta_backend.ok:
#             raise HTTPException(status_code=risposta_backend.status_code, detail=risposta_backend.json())
            
#         return risposta_backend.json()
#     except requests.exceptions.RequestException as e:
#         raise HTTPException(status_code=500, detail="Backend non raggiungibile")

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI()

# Colleghiamo la cartella templates
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    # Nelle versioni recenti di FastAPI, i parametri vanno specificati esplicitamente
    return templates.TemplateResponse(
        request=request, 
        name="home.html", 
        context={"request": request}
    )