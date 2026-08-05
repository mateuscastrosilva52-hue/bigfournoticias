"""
Script que busca as últimas notícias de Flamengo, Vasco, Botafogo e Fluminense
no Google News (RSS, sem necessidade de chave de API) e atualiza o bloco de
dados dentro do index.html do site Big Four.

Como funciona:
1. Para cada clube, busca o feed RSS de notícias do Google News em português.
2. Pega as 3 manchetes mais recentes de cada um.
3. Substitui o bloco "DATA-START ... DATA-END" dentro do index.html
   pelas notícias novas, mantendo as cores e o layout do site intactos.

Uso local (para testar na sua máquina):
    pip install feedparser
    python update_news.py
"""

import re
import html
import feedparser

# Um item de busca por clube (usado para montar a URL do Google News)
CLUBS = {
    "flamengo": {
        "label": "Flamengo",
        "short": "Rubro-Negro",
        "query": "Flamengo",
        "theme": '{ bg:"#8C1116", text:"#F3EFE3", sub:"#E7E0CC", accent:"#C89B3C", line:"rgba(243,239,227,0.2)" }',
        "dot": "#1A1A1A",
    },
    "vasco": {
        "label": "Vasco da Gama",
        "short": "Cruzmaltino",
        "query": "Vasco da Gama futebol",
        "theme": '{ bg:"#141414", text:"#F3EFE3", sub:"#E7E0CC", accent:"#C89B3C", line:"rgba(243,239,227,0.18)" }',
        "dot": "#ffffff",
    },
    "botafogo": {
        "label": "Botafogo",
        "short": "Alvinegro",
        "query": "Botafogo futebol",
        "theme": '{ bg:"#ffffff", text:"#1A1A1A", sub:"#4B4B44", accent:"#B5121B", line:"rgba(181,18,27,0.25)" }',
        "dot": "#B5121B",
    },
    "fluminense": {
        "label": "Fluminense",
        "short": "Tricolor",
        "query": "Fluminense futebol",
        "theme": '{ bg:"#1F4D36", text:"#F3EFE3", sub:"#E7E0CC", accent:"#F2A6A0", line:"rgba(243,239,227,0.2)" }',
        "dot": "#7A1E3C",
    },
}

MAX_STORIES_PER_CLUB = 5
HTML_FILE = "index.html"


def fetch_news(query: str, limit: int = MAX_STORIES_PER_CLUB):
    """Busca notícias recentes no Google News RSS para uma consulta."""
    url = f"https://news.google.com/rss/search?q={query.replace(' ', '+')}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    feed = feedparser.parse(url)
    items = []
    for entry in feed.entries[:limit]:
        title = html.escape(entry.title).replace("'", "\\'")
        link = entry.link
        # O Google News coloca o nome da fonte depois de " - " no final do título
        source = "Google Notícias"
        if hasattr(entry, "source") and entry.source and entry.source.get("title"):
            source = html.escape(entry.source["title"])
        items.append({"title": title, "link": link, "source": source})
    return items


def build_data_block():
    lines = ["// DATA-START", "const DATA = {"]
    club_keys = list(CLUBS.keys())
    for i, (key, info) in enumerate(CLUBS.items()):
        stories = fetch_news(info["query"])
        stories_js = ",\n      ".join(
            f'{{ title:"{s["title"]}", link:"{s["link"]}", source:"{s["source"]}" }}'
            for s in stories
        )
        comma = "," if i < len(club_keys) - 1 else ""
        lines.append(f'  {key}: {{')
        lines.append(f'    label: "{info["label"]}", short: "{info["short"]}",')
        lines.append(f'    theme: {info["theme"]},')
        lines.append(f'    dot: "{info["dot"]}",')
        lines.append(f'    stories: [\n      {stories_js}\n    ]')
        lines.append(f'  }}{comma}')
    lines.append("};")
    lines.append("")
    lines.append(
        'const DEFAULT_THEME = { bg:"#F3EFE3", text:"#1A1A1A", sub:"#4B4B44", '
        'accent:"#C89B3C", line:"rgba(26,26,26,0.15)" };'
    )
    lines.append("// DATA-END")
    return "\n".join(lines)


def update_html():
    with open(HTML_FILE, encoding="utf-8") as f:
        content = f.read()

    new_block = build_data_block()
    pattern = re.compile(r"// DATA-START.*?// DATA-END", re.DOTALL)

    if not pattern.search(content):
        raise RuntimeError(
            "Não encontrei os marcadores // DATA-START e // DATA-END no index.html. "
            "Confirme se o arquivo é a versão certa do site."
        )

    updated = pattern.sub(new_block, content)

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(updated)

    print("index.html atualizado com sucesso.")


if __name__ == "__main__":
    update_html()
