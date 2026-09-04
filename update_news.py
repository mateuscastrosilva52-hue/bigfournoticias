"""
Script que busca as últimas notícias de Flamengo, Vasco, Botafogo e Fluminense
no Google News (RSS, sem necessidade de chave de API para a busca) e usa a
API gratuita do Google Gemini para escrever um resuminho ORIGINAL de 1-2
frases para cada manchete — em vez de só linkar para a matéria externa.

Isso resolve o problema de "conteúdo de baixo valor" apontado pelo AdSense:
antes, a home era basicamente uma lista de links; agora cada notícia tem um
comentário próprio, escrito com apoio de IA a partir da manchete.

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

MAX_STORIES_PER_CLUB = 5
STORIES_IN_HOMEPAGE_PER_CLUB = 2  # quantas notícias de cada time aparecem na home ("Todos")
HTML_FILE = "index.html"
GEMINI_MODEL = "gemini-3.5-flash"


def fetch_news(query: str, limit: int = MAX_STORIES_PER_CLUB):
    """Busca notícias recentes no Google News RSS para uma consulta."""
    url = f"https://news.google.com/rss/search?q={query.replace(' ', '+')}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    feed = feedparser.parse(url)
    items = []
    for entry in feed.entries[:limit]:
        raw_title = entry.title
        source = "Google Notícias"
        if hasattr(entry, "source") and entry.source and entry.source.get("title"):
            source = entry.source["title"]
        if raw_title.endswith(f" - {source}"):
            raw_title = raw_title[: -(len(source) + 3)]
        items.append({
            "title": raw_title.strip(),
            "link": entry.link,
            "source": source,
        })
    return items


def add_summaries_with_gemini(club_label: str, stories: list) -> list:
    """
    Manda as manchetes de um clube para o Gemini e pede um resumo original
    de 1-2 frases para cada uma. Se a chamada falhar por qualquer motivo,
    devolve as notícias sem resumo (o site continua funcionando normalmente).
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or not stories:
        for s in stories:
            s["summary"] = ""
        return stories

    titles_list = "\n".join(f"{i+1}. {s['title']}" for i, s in enumerate(stories))
    prompt = f"""Você escreve para um jornal esportivo carioca chamado "Big Four",
que cobre o {club_label}.

Para cada manchete abaixo, escreva um resumo ORIGINAL de 1 a 2 frases, em
português do Brasil, explicando o contexto ou a relevância da notícia —
não apenas repetindo o título com outras palavras. Se a manchete for vaga,
comente de forma mais genérica em vez de inventar detalhes que não estão nela.

Manchetes:
{titles_list}

Responda APENAS com um JSON array de strings, na mesma ordem das manchetes,
um resumo por item. Não escreva nada fora do JSON, sem markdown, sem ```json.
Exemplo de formato: ["Resumo da primeira notícia.", "Resumo da segunda notícia."]
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
        summaries = json.loads(text)

        for i, s in enumerate(stories):
            s["summary"] = summaries[i] if i < len(summaries) else ""
    except Exception as e:
        print(f"Aviso: não consegui gerar resumos para {club_label} ({e}). Seguindo sem resumo.")
        for s in stories:
            s["summary"] = ""

    return stories


def build_data_block(all_stories):
    lines = ["// DATA-START", "const DATA = {"]
    club_keys = list(CLUBS.keys())
    for i, (key, info) in enumerate(CLUBS.items()):
        stories = all_stories[key]
        stories_js = ",\n      ".join(
            '{{ title:"{title}", link:"{link}", source:"{source}", summary:"{summary}" }}'.format(
                title=html.escape(s["title"]).replace("'", "\\'").replace('"', '\\"'),
                link=s["link"],
                source=html.escape(s["source"]).replace('"', '\\"'),
                summary=html.escape(s.get("summary", "")).replace("'", "\\'").replace('"', '\\"').replace("\n", " "),
            )
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


def build_stories_html(all_stories):
    """
    Gera o HTML puro (visível sem JavaScript) com uma mistura de notícias
    dos quatro times, cada uma com o resumo original escrito pela IA.
    """
    mixed = []
    for key in CLUBS:
        mixed.extend(all_stories[key][:STORIES_IN_HOMEPAGE_PER_CLUB])

    cards = []
    for s in mixed:
        title = html.escape(s["title"])
        source = html.escape(s["source"])
        link = html.escape(s["link"], quote=True)
        summary = html.escape(s.get("summary", ""))
        summary_html = f'\n      <p>{summary}</p>' if summary else ""
        cards.append(
            '    <div class="story">\n'
            f'      <span class="tag">{source}</span>\n'
            f'      <h3>{title}</h3>{summary_html}\n'
            f'      <a class="source" href="{link}" target="_blank" rel="noopener">Leia a matéria completa →</a>\n'
            '    </div>'
        )

    block = "\n".join([
        "<!-- STORIES-START -->",
        "  <!--",
        "    Este bloco é escrito diretamente pelo update_news.py a cada execução.",
        "    Ele fica visível no HTML puro, sem precisar de JavaScript, o que",
        '    resolve a violação do AdSense de "tela sem conteúdo do editor".',
        "    Cada notícia inclui um resumo original gerado por IA (Gemini),",
        '    para evitar o problema de "conteúdo de baixo valor" (só links).',
        "    O JavaScript apenas SUBSTITUI este conteúdo quando o usuário",
        "    clica em um time específico — a carga inicial já vem pronta.",
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

    all_stories = {}
    for key, info in CLUBS.items():
        stories = fetch_news(info["query"])
        stories = add_summaries_with_gemini(info["label"], stories)
        all_stories[key] = stories

    data_pattern = re.compile(r"// DATA-START.*?// DATA-END", re.DOTALL)
    stories_pattern = re.compile(r"<!-- STORIES-START -->.*?<!-- STORIES-END -->", re.DOTALL)

    if not data_pattern.search(content):
        raise RuntimeError(
            "Não encontrei os marcadores // DATA-START e // DATA-END no index.html. "
            "Confirme se o arquivo é a versão certa do site."
        )
    if not stories_pattern.search(content):
        raise RuntimeError(
            "Não encontrei os marcadores <!-- STORIES-START --> e <!-- STORIES-END --> "
            "no index.html. Use a versão atualizada do index.html que inclui esse bloco."
        )

    content = data_pattern.sub(build_data_block(all_stories), content)
    content = stories_pattern.sub(build_stories_html(all_stories), content)

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print("index.html atualizado com sucesso (DATA + conteúdo visível sem JS + resumos por IA).")


if __name__ == "__main__":
    update_html()
