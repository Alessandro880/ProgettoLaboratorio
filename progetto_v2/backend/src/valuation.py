import difflib

"""
    Funzioni utili per la valutazione del Parer:

    Implementate due funzioni :

    • token level eval :  
        divide il testo in token ovvero ogni parola e confrontando i due insiemi trovati dai due testi calcola :
            - precision : confronta il numero di token trovati
            - recall    : quanti token effettivi sono stati trovati
            - F1        : media bilanciata tra precision  e recall

    • sequence similarity eval :
        questa metrica valuta la struttura e l'ordine esatto del testo, calcola :
            - similarity ratio         : indica quanto i due testi si somigliano comlessivamente, penalizza
                                         refusi, spazi in più e parole messe in ordine sbagliato
            - longest contiguos match  : il numero di caratteri più lunga che risulta identica al testo esatto
            - perfect match            : valore booleano per dire se il testoè completamente identico
"""

def token_level_eval(testo_estratto: str, testo_gs: str) -> dict:
    """
    Calcola Precision, Recall e F1-score a livello di token.
    
    Parametri :
    testo_estratto: Il testo prodotto dal parser (già pulito).
    testo_gs: Il testo del Gold Standard di riferimento.
    
    Return:
    Dizionario contenente le metriche calcolate:
        • precision
        • recall
        • f1
    """
    
    tokens_estratti = set(testo_estratto.lower().split())
    tokens_gs = set(testo_gs.lower().split())

    intersezione = tokens_estratti.intersection(tokens_gs)
    len_intersezione = len(intersezione)

    # Calcolo Metriche (con controlli per evitare ZeroDivisionError)
    
    if len(tokens_estratti) > 0:
        precision = len_intersezione / len(tokens_estratti)
    else:
        precision = 0.0

    # Recall: |tokens_estratti ∩ tokens_gs| / |tokens_gs|
    if len(tokens_gs) > 0:
        recall = len_intersezione / len(tokens_gs)
    else:
        recall = 0.0

    # F1: 2 * precision * recall / (precision + recall)
    if (precision + recall) > 0:
        f1 = 2 * precision * recall / (precision + recall)
    else:
        f1 = 0.0

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1
    }


def sequence_similarity_eval(testo_estratto: str, testo_gs: str) -> dict:
    testo_estratto_clean = testo_estratto.lower().strip()
    testo_gs_clean = testo_gs.lower().strip()

    # SequenceMatcher trova i blocchi contigui di testo corrispondenti
    matcher = difflib.SequenceMatcher(None, testo_estratto_clean, testo_gs_clean)
    
    similarity_ratio = matcher.ratio()
    
    # Restituisce la lunghezza della frase contigua più lunga trovata in entrambi
    match = matcher.find_longest_match(0, len(testo_estratto_clean), 0, len(testo_gs_clean))
    longest_match_len = match.size

    return {
        "sequence_similarity_ratio": round(similarity_ratio, 4),
        "longest_contiguous_match_chars": longest_match_len,
        "is_perfect_match": similarity_ratio == 1.0
    }
