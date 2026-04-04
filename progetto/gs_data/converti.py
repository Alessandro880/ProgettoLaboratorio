import json
html_grezzo:str

with open("file.html", "r", encoding="utf-8") as f:
    html_grezzo = f.read()

gold_txt:str

with open("file.txt", "r", encoding="utf-8") as f:
    gold_txt = f.read()


gold_standard = [{
    "url": "https://en.wikipedia.org/wiki/Minerv",
    "title" : "Minerva - Wikipedia",
    "domain" : "wikipedia.org",
    "html_txt": html_grezzo,
    "gold_text" : gold_txt
}]

with open("domain_wikipedia_gs.json", "w", encoding="utf-8") as f:
    json.dump(gold_standard, f, ensure_ascii=False, indent=4)