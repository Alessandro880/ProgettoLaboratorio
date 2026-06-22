import json
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from ollama import Client
import uvicorn


app = FastAPI()

MODEL = "llama3.2:3b"

class Compare(BaseModel):
    text:str
    gold:str

class Response(BaseModel):
    model: str
    score: int
    feedback: str

ollama_client = Client(host='http://ollama:11434')


@app.post("/evaluate_judge", response_model=Response)
async def evaluate_judge(request: Compare):
    prompt = f"""
    Sei un assistente esperto nell'analisi di testi. Il tuo unico compito è confrontare le due stringhe fornite e valutare quanto sono simili per il contenuto.
    
    REGOLE OBBLIGATORIE:
    - Rispondi ESCLUSIVAMENTE in formato JSON valido.
    - Non aggiungere testo prima o dopo il JSON.
    - Il JSON deve avere esattamente queste tre chiavi:
      1. "modello_usato": scrivi "{MODEL}"
      2. "score": un numero intero da 0 a 5 (0 = completamente diverse, 5 = identiche)
      3. "feedback": un riassunto delle differenze ESTREMAMENTE conciso (massimo 10-15 parole) in italiano.

    --- INIZIO STRINGA 1 ---
    {request.text}
    --- FINE STRINGA 1 ---

    --- INIZIO STRINGA 2 ---
    {request.gold}
    --- FINE STRINGA 2 ---
    """
    try:
        # Usiamo format='json' per forzare Ollama a generare solo JSON valido
        response = ollama_client.generate(model=MODEL, prompt=prompt, format="json")
        
        # La risposta di Ollama è una stringa in formato JSON. La parsiamo in un dizionario.
        result_dict = json.loads(response['response'])
        
        return result_dict
    
    except json.JSONDecodeError:
         # Se Ollama fa confusione e non restituisce un JSON valido, intercettiamo l'errore
         raise HTTPException(status_code=500, detail="Errore: Ollama non ha restituito un formato JSON valido.")
    except Exception as e:
         raise HTTPException(status_code=500, detail=f"Errore di comunicazione con Ollama: {str(e)}")
