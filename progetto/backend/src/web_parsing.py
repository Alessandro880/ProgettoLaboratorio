from bs4 import BeautifulSoup
import re

def clean_web_content(html_content):
    if not html_content:
        return {"title": "", "content": ""}

    soup = BeautifulSoup(html_content, 'lxml')

    # 1. Estrai il titolo
    title = soup.title.string if soup.title else "Senza Titolo"

    # 2. Rimuovi fisicamente i componenti di disturbo (Layout e Script)
    # Questi tag e classi coprono il 99% di menu, sidebar e footer
    for element in soup.select('script, style, nav, footer, header, aside, .sidebar, #sidebar, .menu, #menu, .nav, #nav, .ads, .footer'):
        element.decompose()

    # 3. Estrai il testo solo dai tag che contengono vero contenuto informativo
    # Evitiamo div generici che spesso contengono solo boilerplate
    content_tags = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li'])
    
    text_blocks = []
    for tag in content_tags:
        # Pulizia rapida del testo nel tag
        text = tag.get_text(" ", strip=True)
        
        # Filtro qualità: evita stringhe troppo corte (es. "Login", "Home", "Vai")
        # e pulisce i riferimenti stile Wikipedia [1], [2], [edit]
        if len(text) > 20:
            clean_text = re.sub(r'\[\d+\]|\[edit\]', '', text)
            text_blocks.append(clean_text)

    # Uniamo i blocchi con doppia riga per leggibilità
    final_content = "\n\n".join(text_blocks)

    return {
        "title": title.strip(),
        "content": final_content
    }

