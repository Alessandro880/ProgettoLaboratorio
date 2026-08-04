from bs4 import BeautifulSoup
import re
import markdown
from readability import Document

# ==========================================
# FUNZIONI DI UTILITÀ E EVALUATION
# ==========================================

def rimuovi_markdown(testo_md: str) -> str:
    """Converte Markdown in HTML e pulisce per l'Evaluate."""
    if not testo_md:
        return ""
    # Evita che i titoli con # diventino attaccati al testo successivo
    testo_md = re.sub(r'(#+ .*?)\n', r'\1\n\n', testo_md)
    html = markdown.markdown(testo_md)
    soup = BeautifulSoup(html, "html.parser")
    # Il separatore spazio risolve i 17 errori su 1728
    testo_pulito = soup.get_text(separator=' ', strip=True) 
    testo_pulito = re.sub(r'\[\d+\]', '', testo_pulito) # Pialla note [1], [2]
    testo_pulito = re.sub(r'\s+', ' ', testo_pulito)
    return testo_pulito.strip()

def formatta_in_markdown(titolo, testo_convertito):
    """Assembla titolo e testo estratto."""
    titolo_pulito = titolo.strip() if titolo else "Titolo non trovato"
    markdown_finale = ""
    
    if titolo_pulito and titolo_pulito != "Titolo non trovato":
        markdown_finale += f"# {titolo_pulito}\n\n"
        
    if testo_convertito:
        # Pulisce spazi orizzontali in eccesso mantenendo gli a capo
        testo_pulito = re.sub(r'[ \t]+', ' ', testo_convertito)
        markdown_finale += testo_pulito.strip()
        
    return [titolo_pulito, markdown_finale.strip()]

# ==========================================
# PARSER 1: WIKIPEDIA
# ==========================================

def clean_wikipedia_text(html_content):
    doc = Document(html_content)
    titolo = doc.title()
    html_principale = doc.summary()

    soup = BeautifulSoup(html_principale, 'html.parser')
    
    for img in soup.find_all(['img', 'figure']):
        img.decompose()
        
    for sup in soup.find_all('sup'):
        sup.decompose()
        
    for span in soup.find_all('span', class_='mw-editsection'):
        span.decompose()
        
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

    tag_inline = ['a', 'span', 'strong', 'em', 'b', 'i', 'u', 'sub', 'code']
    for tag in soup.find_all(tag_inline):
        tag.unwrap()

    soup = BeautifulSoup(str(soup), 'html.parser')

    testo_convertito = soup.get_text(separator='\n\n', strip=True)
    
    testo_convertito = re.sub(r' +', ' ', testo_convertito)
    
    pattern_residui = r'\[\d+\]|\[[a-zA-Z]\]|\[edit\]|\[modifica\]|\[\s*\*?citation needed\*\?\s*\]'
    testo_convertito = re.sub(pattern_residui, '', testo_convertito, flags=re.IGNORECASE)
    
    testo_convertito = re.sub(r'\n{3,}', '\n\n', testo_convertito.strip())

    return formatta_in_markdown(titolo, testo_convertito)

# ==========================================
# PARSER 2: OLYMPICS (Il tuo originale)
# ==========================================

def clean_olympics_text(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    titolo_tag = soup.find('h1')
    titolo = titolo_tag.get_text(separator=' ', strip=True) if titolo_tag else "Titolo non trovato"

    for tag in soup.find_all(['nav', 'header', 'footer', 'aside', 'script', 'style', 'svg', 'button', 'form', 'iframe', 'picture', 'video']):
        tag.decompose()

    for a in soup.find_all('a'):
        if a.attrs is None: continue
        if len(a.get_text(strip=True)) > 50: 
            a.decompose()

    main_area = soup.find('main') or soup.find('article') or soup.find('body') or soup
    testo_grezzo = main_area.get_text(separator='\n', strip=True)
    
    linee = testo_grezzo.split('\n')
    testo_valido = []

    parole_spazzatura = [
        'condividi', 'share', 'leggi di più', 'read more', 'newsletter', 
        'copyright', 'all rights reserved', 'advertisement', 'pubblicità',
        'cookie', 'accetta', 'rifiuta', 'guarda anche', 
        'scopri e rivivi', 'olympic channel', 'film e serie', 'best of', 
        'originali', 'in associazione con'
    ]

    for linea in linee:
        linea = linea.strip()
        if not linea or linea.lower() == titolo.lower() or linea in testo_valido:
            continue
        if '|' in linea and len(linea) < 100:
            continue
        if any(p in linea.lower() for p in parole_spazzatura):
            continue

        lunghezza = len(linea)
        numero_parole = len(linea.split())

        if lunghezza > 60 and numero_parole > 6:
            testo_valido.append(linea)
        elif 15 <= lunghezza <= 60 and numero_parole >= 3:
            testo_valido.append(linea)

    return formatta_in_markdown(titolo, "\n\n".join(testo_valido))

# ==========================================
# PARSER 3: GOVERNO.IT
# ==========================================

def clean_governo_text(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    titolo_tag = soup.find('h1')
    titolo = titolo_tag.get_text(strip=True) if titolo_tag else "Titolo non trovato"

    # Il contenitore corretto per gli articoli del governo
    content = soup.find('div', class_='field-name-body') or soup.find('div', class_='node-content') or soup.find('article')
    if not content: return formatta_in_markdown(titolo, "")

    # Rimozione spazzatura specifica del sito
    for tag in content.find_all(['script', 'style', 'nav']):
        tag.decompose()
        
    for tag in content.find_all(class_=lambda x: x and any(c in x for c in ['social-share', 'tags', 'links', 'menu', 'sidebar'])):
        tag.decompose()

    # Estrazione in blocco per non perdere pezzi
    testo_grezzo = content.get_text(separator='\n\n', strip=True)
    linee_valide = [linea for linea in testo_grezzo.split('\n\n') if len(linea.split()) > 3]
    return formatta_in_markdown(titolo, "\n\n".join(linee_valide))

# ==========================================
# PARSER 4: LO SPIEGONE
# ==========================================

def clean_lospiegone_text(html_content):
    doc = Document(html_content)
    titolo = doc.title()
    html_principale = doc.summary()

    soup = BeautifulSoup(html_principale, 'html.parser')
    
    for img in soup.find_all(['img', 'figure']):
        img.decompose()
        
    for sup in soup.find_all('sup'):
        sup.decompose()
        
    for span in soup.find_all('span', class_='mw-editsection'):
        span.decompose()
        
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

    tag_inline = ['a', 'span', 'strong', 'em', 'b', 'i', 'u', 'sub', 'code']
    for tag in soup.find_all(tag_inline):
        tag.unwrap()

    soup = BeautifulSoup(str(soup), 'html.parser')

    testo_convertito = soup.get_text(separator='\n\n', strip=True)
    
    testo_convertito = re.sub(r' +', ' ', testo_convertito)
    
    pattern_residui = r'\[\d+\]|\[[a-zA-Z]\]|\[edit\]|\[modifica\]|\[\s*\*?citation needed\*\?\s*\]'
    testo_convertito = re.sub(pattern_residui, '', testo_convertito, flags=re.IGNORECASE)
    
    testo_convertito = re.sub(r'\n{3,}', '\n\n', testo_convertito.strip())

    return formatta_in_markdown(titolo, testo_convertito)

# ==========================================
# PARSER 5: FALLBACK
# ==========================================

def clean_text(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    titolo_tag = soup.find('h1') or soup.find('title')
    titolo = titolo_tag.get_text(strip=True) if titolo_tag else "Titolo non trovato"

    for tag in soup.find_all(['nav', 'header', 'footer', 'aside', 'script', 'style']):
        tag.decompose()

    content = soup.find('main') or soup.find('article') or soup.find('body') or soup
    
    testo_grezzo = content.get_text(separator='\n\n', strip=True)
    linee_valide = [linea for linea in testo_grezzo.split('\n\n') if len(linea.split()) > 4]

    return formatta_in_markdown(titolo, "\n\n".join(linee_valide))
