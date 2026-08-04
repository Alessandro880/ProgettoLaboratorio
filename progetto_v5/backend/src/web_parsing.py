from bs4 import BeautifulSoup
import re
import markdown
from readability import Document

"""
    Funzioni utili per togliere il markdown e formattare in markdown
    I diversi parser, uno per ogni dominio assegnato
"""

def rimuovi_markdown(testo_md: str) -> str:
    if not testo_md:
        return ""
    testo_md = re.sub(r'(#+ .*?)\n', r'\1\n\n', testo_md)
    html = markdown.markdown(testo_md)
    soup = BeautifulSoup(html, "html.parser")
    testo_pulito = soup.get_text(separator=' ', strip=True) 
    testo_pulito = re.sub(r'\[\d+\]', '', testo_pulito) 
    testo_pulito = re.sub(r'\s+', ' ', testo_pulito)
    return testo_pulito.strip()

def formatta_in_markdown(titolo, testo_convertito):
    titolo_pulito = titolo.strip() if titolo else "Titolo non trovato"
    markdown_finale = ""
    
    if titolo_pulito and titolo_pulito != "Titolo non trovato":
        markdown_finale += f"# {titolo_pulito}\n\n"
        
    if testo_convertito:
        # Pulisce spazi orizzontali in eccesso mantenendo gli a capo
        testo_pulito = re.sub(r'[ \t]+', ' ', testo_convertito)
        markdown_finale += testo_pulito.strip()
        
    return [titolo_pulito, markdown_finale.strip()]


# Parser WIKIPEDIA
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


# Parser OLYMPICS

# def clean_olympics_text(html_content):
#     soup = BeautifulSoup(html_content, 'html.parser')
#     titolo_tag = soup.find('h1')
#     titolo = titolo_tag.get_text(separator=' ', strip=True) if titolo_tag else "Titolo non trovato"

#     # 1. Rimuoviamo tag inutili alla lettura
#     for tag in soup.find_all(['nav', 'header', 'footer', 'aside', 'script', 'style', 'svg', 'button', 'form', 'iframe', 'picture', 'video']):
#         tag.decompose()

#     # 2. Gestione link lunghi (Rilassata)
#     for a in soup.find_all('a'):
#         if a.attrs is None: continue
#         if len(a.get_text(strip=True)) > 80: 
#             a.decompose()

#     # 3. Individuazione dell'area principale
#     main_area = soup.find('main') or soup.find(id='__next') or soup.find(id='root') or soup.find('article') or soup.find('body') or soup
    
#     # NOVITÀ: Evitiamo che testi in span o sup (es. 73rd) vengano spezzati dal newline
#     for inline in main_area.find_all(['span', 'sup', 'sub', 'b', 'i', 'strong', 'em']):
#         inline.unwrap()

#     testo_grezzo = main_area.get_text(separator='\n', strip=True)
#     linee = testo_grezzo.split('\n')
#     testo_valido = []

#     # 4. Filtri testo ampliati
#     parole_spazzatura = {
#         'condividi', 'share', 'leggi di più', 'read more', 'newsletter', 
#         'copyright', 'all rights reserved', 'advertisement', 'pubblicità',
#         'cookie', 'accetta', 'rifiuta', 'guarda anche', 
#         'scopri e rivivi', 'olympic channel', 'film e serie', 'best of', 
#         'originali', 'in associazione con', 'privacy policy', 'terms of service',
#         'sitemap', 'contact centre', 'about us', 'shop', 'museum', 
#         'international olympic committee', 'explore', 'topics', 'podcast',
#         'corporate', 'original series', 'live events', 'tv channel',
#         'all olympic games', 'replays & highlights', 'results & medals',
#         'you may like', 'featured', 'quick update: we have updated', 'find it here',
#         'olympic games milano cortina 2026'
#     }
    
#     # NOVITÀ: Voci di menu singole da eliminare solo in caso di match esatto
#     menu_esatti = {'athletes', 'sports', 'more', 'news'}

#     for linea in linee:
#         linea = linea.strip()
#         linea_lower = linea.lower()
        
#         if not linea or linea_lower == titolo.lower() or linea in testo_valido:
#             continue
#         if '|' in linea and len(linea) < 50:
#             continue
            
#         # Filtro parziale
#         if any(p in linea_lower for p in parole_spazzatura):
#             continue
            
#         # Filtro esatto
#         if linea_lower in menu_esatti:
#             continue

#         lunghezza = len(linea)
#         numero_parole = len(linea.split())

#         # Le stringhe con i ":" le teniamo se hanno un minimo di senso
#         if ":" in linea and lunghezza > 3:
#             testo_valido.append(linea)
#             continue

#         # Salvataggio dati brevi e statistici
#         if lunghezza > 20 and numero_parole >= 2:
#             testo_valido.append(linea)
#         elif 4 <= lunghezza <= 60:
#             testo_valido.append(linea)
#         elif 0 < lunghezza < 4 and linea.isalnum(): 
#             testo_valido.append(linea)

#     return formatta_in_markdown(titolo, "\n\n".join(testo_valido))

def clean_olympics_markdown(markdown_grezzo: str) -> tuple:
    """Pulisce il markdown già generato da Crawl4AI per olympics.com"""
    linee = markdown_grezzo.split('\n')
    
    titolo = "Titolo non trovato"
    righe_finali = []
    seen = set()
    
    parole_spazzatura = {
        'giochi olimpici', 'milano cortina 2026', 'replay e highlights',
        'tutti i giochi olimpici', 'canali tv', 'eventi in diretta',
        'dati societari', 'notizie', 'argomenti', 'esplora',
        'comitato olimpico internazionale', 'museo', 'negozio',
        'su di noi', 'contatti', 'mappa del sito', 'lavoro',
        'politica sulla privacy', 'termini del servizio',
        'risultati e medaglie', 'olympic channel', 'cookie',
        'privacy policy', 'terms of service', 'sitemap',
        'contact centre', 'about us', 'shop', 'museum',
        'international olympic committee', 'corporate',
        'original series', 'live events', 'tv channel',
        'all olympic games', 'replays & highlights',
        'results & medals', 'newsletter', 'advertisement',
        'social network',  # campo metadato della pagina atleta
            'sweden anthem',
        'replays',          # cattura "Armand DUPLANTIS Replays"
        'olympic results',  # cattura "Olympic Results"  
        'athlete olympic results content',
        'italy anthem',
        'france anthem',
        'germany anthem',
        'usa anthem',       # aggiungi altri paesi se servono
        'anthem',           # più generico, cattura tutti gli inni
        'highlights',
        'athlete olympic',
        }
    
    for linea in linee:
        linea = linea.strip()
        if not linea:
            continue
            
        linea_lower = linea.lower()
        
        # Estrai titolo dall'H1 markdown
        if linea.startswith('# ') and titolo == "Titolo non trovato":
            titolo = linea[2:].strip()
            continue  # il titolo lo gestisce formatta_in_markdown
        
        # Deduplicazione
        if linea_lower in seen:
            continue
        seen.add(linea_lower)
        
        # Filtro spazzatura
        if any(p in linea_lower for p in parole_spazzatura):
            continue
        
        # Salta righe che sono solo un link markdown [testo](url)
        if linea.startswith('[') and '](http' in linea and len(linea) < 80:
            continue
        
        # Salta separatori markdown
        if linea.startswith('---') or linea.startswith('==='):
            continue
            
        righe_finali.append(linea)
    
    return formatta_in_markdown(titolo, "\n\n".join(righe_finali))

def clean_olympics_text(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')

    for tag in soup.find_all(['nav', 'header', 'footer', 'aside', 'script',
                               'style', 'svg', 'button', 'form', 'iframe',
                               'picture', 'video']):
        tag.decompose()

    titolo_tag = soup.find('h1')
    titolo = titolo_tag.get_text(separator=' ', strip=True) if titolo_tag else "Titolo non trovato"

    righe_finali = []

    # --- METADATI (paese, disciplina, medaglie, ecc.) ---
    nocs = soup.find(attrs={"data-cy": "nocs"})
    if nocs:
        for span in nocs.find_all('span'):
            t = span.get_text(strip=True)
            if t and len(t) > 1:
                righe_finali.append(t)

    disciplines = soup.find(attrs={"data-cy": "disciplines"})
    if disciplines:
        for span in disciplines.find_all('span'):
            t = span.get_text(strip=True)
            if t and len(t) > 1:
                righe_finali.append(t)

    profile = soup.find(attrs={"data-cy": "athlete-profile"})
    if profile:
        for row in profile.find_all(class_=lambda c: c and 'fOoPCV' in c):
            t = row.get_text(separator='\n', strip=True)
            if t:
                righe_finali.append(t)

    # --- BIOGRAFIA ---
    main_area = (soup.find('main') or soup.find(id='__next') or
                 soup.find(id='root') or soup.find('article') or
                 soup.find('body') or soup)

    blocchi = []
    for tag in main_area.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'li']):
        testo = tag.get_text(separator=' ', strip=True)
        testo = ' '.join(testo.split())
        if testo:
            blocchi.append((tag.name, testo))

    parole_spazzatura = {
        'condividi', 'share', 'leggi di più', 'read more', 'newsletter',
        'copyright', 'all rights reserved', 'advertisement', 'pubblicità',
        'cookie', 'accetta', 'rifiuta', 'guarda anche',
        'scopri e rivivi', 'olympic channel', 'film e serie', 'best of',
        'originali', 'in associazione con', 'privacy policy', 'terms of service',
        'sitemap', 'contact centre', 'about us', 'shop', 'museum',
        'international olympic committee', 'explore', 'topics', 'podcast',
        'corporate', 'original series', 'live events', 'tv channel',
        'all olympic games', 'replays & highlights', 'results & medals',
        'you may like', 'featured', 'quick update: we have updated', 'find it here',
        'olympic games milano cortina 2026',
        'giochi olimpici', 'milano cortina 2026', 'replay e highlights',
        'tutti i giochi olimpici', 'canali tv', 'eventi in diretta',
        'dati societari', 'notizie', 'argomenti', 'esplora', 'atleti',
        'sport', 'altro', 'comitato olimpico internazionale', 'museo',
        'negozio', 'su di noi', 'contatti', 'mappa del sito', 'lavoro',
        'politica sulla privacy', 'termini del servizio', 'risultati e medaglie',
        'anthem', 'replays', 'olympic results', 'athlete olympic results content',
        'athlete olympic', 'highlights', 'social network',
        'anno di nascita', 'year of birth',
    }
    menu_esatti = {'athletes', 'sports', 'more', 'news'}

    seen = set()
    for tag_name, testo in blocchi:
        testo_lower = testo.lower()

        if testo_lower in seen:
            continue
        seen.add(testo_lower)

        if testo_lower == titolo.lower():
            continue

        if any(p in testo_lower for p in parole_spazzatura):
            continue

        if testo_lower in menu_esatti:
            continue

        if '|' in testo and len(testo) < 50:
            continue

        if tag_name == 'h1':
            pass
        elif tag_name in ('h2', 'h3', 'h4'):
            righe_finali.append(testo)
        elif len(testo.split()) >= 2:
            righe_finali.append(testo)

    righe_pulite = []
    precedente = None
    for linea in righe_finali:
        if linea != precedente:
            righe_pulite.append(linea)
        precedente = linea

    return [titolo,"\n\n".join(righe_pulite)]


# Parser GOVERNO
def clean_governo_text(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 1. Estrazione del Titolo
    titolo_tag = soup.find('h1')
    titolo = titolo_tag.get_text(strip=True) if titolo_tag else "Titolo non trovato"

    # 2. Ricerca del contenitore principale (Ordine universale per siti Drupal/PA)
    content = (
        soup.find('div', class_='region-content') or
        soup.find('div', class_='view-content') or
        soup.find('div', class_='field-name-body') or 
        soup.find('div', class_='node-content') or 
        soup.find('article') or
        soup.find('main')
    )
    
    if not content: 
        return formatta_in_markdown(titolo, "Nessun contenuto principale rilevato sulla pagina.")

    # 3. Pulizia profonda dei tag inutili (inclusi iframe e noscript)
    for tag in content.find_all(['script', 'style', 'nav', 'iframe', 'noscript', 'svg']):
        tag.decompose()
        
    # 4. Pulizia flessibile del "rumore" (Menu, social, sidebar)
    # L'uso di una lambda sui loop della classe gestisce i tag con classi multiple
    noise_keywords = ['social', 'share', 'tags', 'links', 'menu', 'sidebar', 'breadcrumb', 'pagination']
    for tag in content.find_all(class_=lambda classes: classes and any(
        keyword in cls.lower() for cls in classes for keyword in noise_keywords
    )):
        tag.decompose()

    # 5. Estrazione sicura del testo
    # Passiamo '\n' come separatore per evitare che gli elementi di una lista <li> si attacchino tra loro
    testo_grezzo = content.get_text(separator='\n', strip=True)
    
    # 6. Filtraggio intelligente delle linee
    linee_valide = []
    for linea in testo_grezzo.split('\n'):
        linea_pulita = linea.strip()
        
        # Filtriamo le stringhe vuote o artefatti minuscoli (< 3 caratteri), 
        # ma conserviamo righe composte anche da una o due sole parole.
        if len(linea_pulita) > 3: 
            linee_valide.append(linea_pulita)

    # Ricompatta il testo in paragrafi Markdown
    return formatta_in_markdown(titolo, "\n\n".join(linee_valide))


# Parser LOSPIEGONE
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


# Parser basico, di backup, mai utilizzato
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
