from readability import Document
from bs4 import BeautifulSoup
import re

def clean_text(html_content):
    """
    Riceve in input l'HTML grezzo, ne estrae il titolo e il testo principale
    ripulito da menu, pubblicità, foto, bibliografia, contatti, link, formattazioni e note.
    """
    
    # 1. Readability: isola il corpo dell'articolo
    doc = Document(html_content)
    titolo = doc.title()
    html_principale = doc.summary()

    # 2. Pulizia profonda con BeautifulSoup
    soup = BeautifulSoup(html_principale, 'html.parser')
    
    # Rimuovi immagini e figure
    for img in soup.find_all(['img', 'figure']):
        img.decompose()
        
    # --- RIMOZIONE NOTE E BOTTONI (Wikipedia e simili) ---
    # Rimuove tutti i numeri in apice come [1], [a], [citation needed]
    for sup in soup.find_all('sup'):
        sup.decompose()
        
    # Rimuove i pulsanti [edit] o [modifica]
    for span in soup.find_all('span', class_='mw-editsection'):
        span.decompose()
        
    # --- LA GHIGLIOTTINA DEFINITIVA ---
    parole_da_scartare = [
        'bibliografia', 'contatti', 'chi siamo', 'fonti', 'voci correlate', 
        'collegamenti esterni', 'references', 'see also', 'external links', 
        'further reading', 'notes'
    ]
    
    for nodo in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div']):
        da_tagliare = False
        
        if nodo.name == 'div':
            classi_id = str(nodo.get('class', [])) + " " + str(nodo.get('id', ''))
            if 'reflist' in classi_id.lower() or 'references' in classi_id.lower():
                da_tagliare = True
                
        elif nodo.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            testo_nodo = nodo.get_text(separator=' ', strip=True).lower()
            if any(parola in testo_nodo for parola in parole_da_scartare):
                da_tagliare = True
                
        if da_tagliare:
            for elemento in nodo.find_all_next():
                try:
                    elemento.decompose()
                except:
                    pass
            nodo.decompose() 
            break 

    # --- SCIOGLIMENTO TAG INLINE ---
    # Rimuove la struttura dei link e grassetti mantenendo il testo.
    # NOTA: non mettiamo più 'sup' qui dentro, l'abbiamo già distrutto sopra!
    tag_inline = ['a', 'span', 'strong', 'em', 'b', 'i', 'u', 'sub', 'code']
    for tag in soup.find_all(tag_inline):
        tag.unwrap()

    # --- IL TRUCCO MAGICO PER COMPATTARE IL TESTO ---
    # Salviamo in stringa e ricarichiamo l'albero HTML. 
    # Questo fonde le singole parole "slegate" dai link in paragrafi continui.
    soup = BeautifulSoup(str(soup), 'html.parser')

    # Ora estraiamo il testo: i paragrafi interi rimarranno uniti, separati solo da \n\n
    testo_convertito = soup.get_text(separator='\n\n', strip=True)
    
    # --- PULIZIA FINALE ---
    # Rimuove eventuali doppi spazi creati dalla rimozione dei tag
    testo_convertito = re.sub(r' +', ' ', testo_convertito)
    
    # Rete di sicurezza: rimuove eventuali rimasugli di note sfuggite all'HTML
    pattern_residui = r'\[\d+\]|\[[a-zA-Z]\]|\[edit\]|\[modifica\]|\[\s*\*?citation needed\*\?\s*\]'
    testo_convertito = re.sub(pattern_residui, '', testo_convertito, flags=re.IGNORECASE)
    
    # Sistema gli a capo per avere un testo bello e compatto
    testo_convertito = re.sub(r'\n{3,}', '\n\n', testo_convertito.strip())

    return titolo, testo_convertito








