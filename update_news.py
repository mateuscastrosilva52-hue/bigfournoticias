"""
Script que busca as últimas notícias de Flamengo, Vasco, Botafogo e Fluminense
no Google News (RSS, sem necessidade de chave de API) e atualiza o index.html
do site Big Four em DOIS lugares:

1. O bloco "DATA-START ... DATA-END" (usado pelo JavaScript quando o
   usuário clica para filtrar por time).
2. O bloco "STORIES-START ... STORIES-END" (HTML puro, já visível na
   página sem precisar rodar JavaScript). É esse segundo bloco que
   resolve a violação do Google AdSense de "tela sem conteúdo do
   editor" — crawlers que não executam JS agora veem notícias reais
   direto no HTML.

Uso local (para testar na sua máquina):
    pip install feedparser
    python update_news.py
"""

import re
import html
import feedparser

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
        # O Google News às vezes deixa o nome da fonte no final do título
        # separado por " - "; remove se bater com a fonte já identificada.
        if raw_title.endswith(f" - {source}"):
            raw_title = raw_title[: -(len(source) + 3)]
        items.append({
            "title": raw_title.strip(),
            "link": entry.link,
            "source": source,
        })
    return items


def build_data_block(all_stories):
    lines = ["// DATA-START", "const DATA = {"]
    club_keys = list(CLUBS.keys())
    for i, (key, info) in enumerate(CLUBS.items()):
        stories = all_stories[key]
        stories_js = ",\n      ".join(
            '{{ title:"{title}", link:"{link}", source:"{source}" }}'.format(
                title=html.escape(s["title"]).replace("'", "\\'").replace('"', '\\"'),
                link=s["link"],
                source=html.escape(s["source"]).replace('"', '\\"'),
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
    dos quatro times, igual ao que a view "Todos" mostra no JS.
    """
    mixed = []
    for key in CLUBS:
        mixed.extend(all_stories[key][:STORIES_IN_HOMEPAGE_PER_CLUB])

    cards = []
    for s in mixed:
        title = html.escape(s["title"])
        source = html.escape(s["source"])
        link = html.escape(s["link"], quote=True)
        cards.append(
            '    <div class="story">\n'
            f'      <span class="tag">{source}</span>\n'
            f'      <h3>{title}</h3>\n'
            f'      <a class="source" href="{link}" target="_blank" rel="noopener">Leia a matéria completa →</a>\n'
            '    </div>'
        )

    block = "\n".join([
        "<!-- STORIES-START -->",
        "  <!--",
        "    Este bloco é escrito diretamente pelo update_news.py a cada execução.",
        "    Ele fica visível no HTML puro, sem precisar de JavaScript, o que",
        '    resolve a violação do AdSense de "tela sem conteúdo do editor".',
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

    all_stories = {key: fetch_news(info["query"]) for key, info in CLUBS.items()}

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

    print("index.html atualizado com sucesso (DATA + conteúdo visível sem JS).")


if __name__ == "__main__":
    update_html()
