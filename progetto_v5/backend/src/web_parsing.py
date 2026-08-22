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

# PARSER OLYMPICS

def clean_olympics_markdown(markdown_grezzo: str) -> tuple:
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
        'social network',  'sweden anthem', 'replays',         
        'olympic results',  'italy anthem', 'france anthem',
        'germany anthem', 'usa anthem', 'anthem', 'highlights', 'athlete olympic',
        }
    
    for linea in linee:
        linea = linea.strip()
        if not linea:
            continue
            
        linea_lower = linea.lower()
        
        if linea.startswith('# ') and titolo == "Titolo non trovato":
            titolo = linea[2:].strip()
            continue  
        
        if linea_lower in seen:
            continue
        seen.add(linea_lower)
        
        if any(p in linea_lower for p in parole_spazzatura):
            continue
        
        if linea.startswith('[') and '](http' in linea and len(linea) < 80:
            continue
        
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
        'explore', 'topics', 'podcast', 'corporate', 'original series', 
        'live events', 'tv channel', 'replays & highlights', 'results & medals',
        'you may like', 'featured', 'quick update: we have updated', 'find it here',
        'replay e highlights', 'canali tv', 'eventi in diretta',
        'dati societari', 'notizie', 'argomenti', 'esplora',
        'museo', 'negozio', 'su di noi', 'contatti', 'mappa del sito', 'lavoro',
        'politica sulla privacy', 'termini del servizio', 'risultati e medaglie',
        'anthem', 'replays', 'olympic results', 'athlete olympic results content',
        'athlete olympic', 'highlights', 'social network',
        'anno di nascita', 'year of birth', 'scopri i giochi', 'il look', 'la torcia'
    }
    menu_esatti = {'athletes', 'sports', 'more', 'news', 'le medaglie', 'i giochi'}

    seen = set()
    for tag_name, testo in blocchi:
        testo_lower = testo.lower()

        if testo_lower in seen:
            continue
        seen.add(testo_lower)

        if testo_lower == titolo.lower():
            continue

        if len(testo) < 80 and any(p in testo_lower for p in parole_spazzatura):
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

    return [titolo, "\n\n".join(righe_pulite)]


# Parser GOVERNO
def clean_governo_text(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    titolo_tag = soup.find('h1')
    titolo = titolo_tag.get_text(strip=True) if titolo_tag else "Titolo non trovato"

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

    for tag in content.find_all(['script', 'style', 'nav', 'iframe', 'noscript', 'svg']):
        tag.decompose()
        
    noise_keywords = ['social', 'share', 'tags', 'links', 'menu', 'sidebar', 'breadcrumb', 'pagination']
    for tag in content.find_all(class_=lambda classes: classes and any(
        keyword in cls.lower() for cls in classes for keyword in noise_keywords
    )):
        tag.decompose()

    testo_grezzo = content.get_text(separator='\n', strip=True)
    
    linee_valide = []
    for linea in testo_grezzo.split('\n'):
        linea_pulita = linea.strip()
        
        if len(linea_pulita) > 3: 
            linee_valide.append(linea_pulita)

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
