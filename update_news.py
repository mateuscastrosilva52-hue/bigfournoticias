"""
Script que busca as últimas notícias de Flamengo, Vasco, Botafogo e Fluminense
no Google News (RSS) e usa a API gratuita do Google Gemini para escrever UM
resumo diário original por clube — um parágrafo sintetizando as principais
notícias do dia, em vez de uma lista de links individuais.

Isso resolve o problema de "conteúdo de baixo valor" apontado pelo AdSense:
antes a home era basicamente uma lista de links; agora cada time tem um
texto de verdade, escrito com apoio de IA a partir das manchetes do dia.

O script atualiza o index.html em DOIS lugares:
1. O bloco "DATA-START ... DATA-END" (usado pelo JavaScript ao filtrar por time).
2. O bloco "STORIES-START ... STORIES-END" (HTML puro, visível sem JS).

IMPORTANTE:
- Precisa da mesma chave GEMINI_API_KEY já usada pela retrospectiva semanal
  (não precisa criar uma nova — é a mesma configurada como Secret no GitHub).

Uso local (para testar na sua máquina):
    pip install feedparser requests
    export GEMINI_API_KEY="sua-chave-aqui"
    python update_news.py
"""

import os
import re
import json
import html
import datetime
import feedparser
import requests

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

HEADLINES_PER_CLUB = 8
HTML_FILE = "index.html"
GEMINI_MODEL = "gemini-3.5-flash"


def fetch_headlines(query: str, limit: int = HEADLINES_PER_CLUB):
    """Busca manchetes recentes no Google News RSS para uma consulta."""
    url = f"https://news.google.com/rss/search?q={query.replace(' ', '+')}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    feed = feedparser.parse(url)
    return [entry.title for entry in feed.entries[:limit]]


def generate_club_digest(club_label: str, headlines: list) -> dict:
    """
    Manda as manchetes do dia de um clube para o Gemini e pede um resumo
    diário original: um título curto e um parágrafo de 3-5 frases. Se a
    chamada falhar, devolve um digest vazio (o site mostra um aviso simples).
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or not headlines:
        return {"title": "", "summary": ""}

    headlines_list = "\n".join(f"- {h}" for h in headlines)
    prompt = f"""Você escreve para um jornal esportivo carioca chamado "Big Four",
que cobre o {club_label}.

Com base nas manchetes recentes abaixo, escreva um resumo diário ORIGINAL
sobre o momento do {club_label} — um parágrafo de 3 a 5 frases, em português
do Brasil, sintetizando e contextualizando as notícias (não apenas listando
os títulos com outras palavras). Se as manchetes forem vagas ou repetitivas,
comente de forma mais genérica em vez de inventar fatos que não estão nelas.

Manchetes de hoje:
{headlines_list}

Responda APENAS com um JSON no formato abaixo, sem markdown, sem \\`\\`\\`json:
{{"title": "Uma frase curta e direta sobre o momento do time", "summary": "O parágrafo de 3 a 5 frases"}}
"""

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
        response = requests.post(
            url,
            headers={"content-type": "application/json", "x-goog-api-key": api_key},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"^```\s*", "", text)
        text = re.sub(r"```\s*$", "", text)
        result = json.loads(text)
        return {"title": result.get("title", ""), "summary": result.get("summary", "")}
    except Exception as e:
        print(f"Aviso: não consegui gerar o resumo de {club_label} ({e}).")
        return {"title": "", "summary": ""}


def build_data_block(all_digests):
    lines = ["// DATA-START", "const DATA = {"]
    club_keys = list(CLUBS.keys())
    for i, (key, info) in enumerate(CLUBS.items()):
        digest = all_digests[key]
        title = html.escape(digest["title"]).replace("'", "\\'").replace('"', '\\"')
        summary = html.escape(digest["summary"]).replace("'", "\\'").replace('"', '\\"').replace("\n", " ")
        comma = "," if i < len(club_keys) - 1 else ""
        lines.append(f'  {key}: {{')
        lines.append(f'    label: "{info["label"]}", short: "{info["short"]}",')
        lines.append(f'    theme: {info["theme"]},')
        lines.append(f'    dot: "{info["dot"]}",')
        lines.append(f'    title: "{title}",')
        lines.append(f'    summary: "{summary}"')
        lines.append(f'  }}{comma}')
    lines.append("};")
    lines.append("")
    lines.append(
        'const DEFAULT_THEME = { bg:"#F3EFE3", text:"#1A1A1A", sub:"#4B4B44", '
        'accent:"#C89B3C", line:"rgba(26,26,26,0.15)" };'
    )
    lines.append("// DATA-END")
    return "\n".join(lines)


def build_stories_html(all_digests):
    """
    Gera o HTML puro (visível sem JavaScript) com os 4 resumos diários,
    um por clube.
    """
    cards = []
    for key, info in CLUBS.items():
        digest = all_digests[key]
        title = html.escape(digest["title"]) or f"Momento do {info['label']}"
        summary = html.escape(digest["summary"]) or "Resumo do dia ainda não disponível."
        cards.append(
            '    <div class="story">\n'
            f'      <span class="tag">{html.escape(info["label"])}</span>\n'
            f'      <h3>{title}</h3>\n'
            f'      <p>{summary}</p>\n'
            '    </div>'
        )

    block = "\n".join([
        "<!-- STORIES-START -->",
        "  <!--",
        "    Este bloco é escrito diretamente pelo update_news.py a cada execução.",
        "    Ele fica visível no HTML puro, sem precisar de JavaScript, o que",
        '    resolve a violação do AdSense de "tela sem conteúdo do editor".',
        "    Cada time tem um resumo diário original gerado por IA (Gemini),",
        '    em vez de uma lista de links (evita "conteúdo de baixo valor").',
        "  -->",
        '  <div class="stories" id="stories">',
        "\n".join(cards),
        "  </div>",
        "<!-- STORIES-END -->",
    ])
    return block


def update_html():
    with open(HTML_FILE, encoding="utf-8") as f:
        content = f.read()

    all_digests = {}
    for key, info in CLUBS.items():
        headlines = fetch_headlines(info["query"])
        all_digests[key] = generate_club_digest(info["label"], headlines)

    data_pattern = re.compile(r"// DATA-START.*?// DATA-END", re.DOTALL)
    stories_pattern = re.compile(r"<!-- STORIES-START -->.*?<!-- STORIES-END -->", re.DOTALL)
    date_pattern = re.compile(r"<!-- HOME-DATE-START -->.*?<!-- HOME-DATE-END -->", re.DOTALL)

    if not data_pattern.search(content) or not stories_pattern.search(content):
        raise RuntimeError(
            "Não encontrei os marcadores DATA-START/END ou STORIES-START/END no "
            "index.html. Use a versão do arquivo que já inclui esses blocos."
        )

    content = data_pattern.sub(build_data_block(all_digests), content)
    content = stories_pattern.sub(build_stories_html(all_digests), content)

    if date_pattern.search(content):
        hoje = datetime.date.today().strftime("%d/%m/%Y")
        content = date_pattern.sub(f"<!-- HOME-DATE-START -->Edição de {hoje}<!-- HOME-DATE-END -->", content)

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print("index.html atualizado com sucesso (resumos diários por IA, um por clube).")


if __name__ == "__main__":
    update_html()
