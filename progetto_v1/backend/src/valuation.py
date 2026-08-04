import difflib

def token_level_eval(testo_estratto: str, testo_gs: str) -> dict:
    """
    Calcola Precision, Recall e F1-score a livello di token.
    
    :param testo_estratto: Il testo prodotto dal parser (già pulito).
    :param testo_gs: Il testo del Gold Standard di riferimento.
    :return: Dizionario contenente le metriche calcolate.
    """
    # 1. Tokenizzazione: lowercase, separazione per spazio e conversione in "insiemi" (set)
    # L'uso di set() rimuove i duplicati e permette di usare l'operatore di intersezione
    tokens_estratti = set(testo_estratto.lower().split())
    tokens_gs = set(testo_gs.lower().split())

    # 2. Intersezione (tokens_estratti ∩ tokens_gs)
    intersezione = tokens_estratti.intersection(tokens_gs)
    len_intersezione = len(intersezione)

    # 3. Calcolo Metriche (con controlli per evitare ZeroDivisionError)
    
    # Precision: |tokens_estratti ∩ tokens_gs| / |tokens_estratti|
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

    # 4. Ritorna il dizionario
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1
    }

# --- Esempio di utilizzo ---
# test_parser = "Il modello ha estratto queste parole"
# test_gold = "Il modello ha estratto alcune di queste parole"
# metriche = token_level_eval(test_parser, test_gold)
# print(metriche)



def sequence_similarity_eval(testo_estratto: str, testo_gs: str) -> dict:
    """
    Calcola la similarità esatta delle stringhe utilizzando SequenceMatcher.
    Ottimo per rilevare frammentazione del testo, inserimenti, cancellazioni o errori di battitura.
    """
    testo_estratto_clean = testo_estratto.lower().strip()
    testo_gs_clean = testo_gs.lower().strip()

    # SequenceMatcher trova i blocchi contigui di testo corrispondenti
    matcher = difflib.SequenceMatcher(None, testo_estratto_clean, testo_gs_clean)
    
    # Restituisce un valore da 0 a 1 (1.0 = match perfetto)
    similarity_ratio = matcher.ratio()
    
    # Restituisce la lunghezza della frase contigua più lunga trovata in entrambi
    match = matcher.find_longest_match(0, len(testo_estratto_clean), 0, len(testo_gs_clean))
    longest_match_len = match.size

    return {
        "sequence_similarity_ratio": round(similarity_ratio, 4),
        "longest_contiguous_match_chars": longest_match_len,
        "is_perfect_match": similarity_ratio == 1.0
    }
