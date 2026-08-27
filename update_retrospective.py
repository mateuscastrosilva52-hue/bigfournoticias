"""
Gera a "Retrospectiva da Semana" do site Big Four usando a API da Anthropic
(Claude) para escrever um texto de análise original, e atualiza a página
retrospectiva.html.

Como funciona:
1. Busca as notícias mais recentes de cada clube (mesmo feed usado pelo
   update_news.py).
2. Monta um resumo dessas manchetes e manda pra API da Anthropic, pedindo
   pra escrever uma retrospectiva em tom de coluna de opinião, uma seção
   por clube.
3. Substitui o bloco "RETRO-START ... RETRO-END" e a data dentro de
   retrospectiva.html.

IMPORTANTE:
- Precisa de uma chave de API da Anthropic. Crie uma em
  https://console.anthropic.com, e configure como variável de ambiente
  ANTHROPIC_API_KEY (ou como "Secret" no GitHub Actions).
- Cada execução consome uma pequena quantidade de créditos da API
  (geralmente poucos centavos, já que roda só 1x por semana).

Uso local (para testar na sua máquina):
    pip install feedparser requests
    export ANTHROPIC_API_KEY="sua-chave-aqui"
    python update_retrospective.py
"""

import os
import re
import html
import datetime
import feedparser
import requests

CLUBS = {
    "flamengo": {"label": "Flamengo", "query": "Flamengo"},
    "vasco": {"label": "Vasco da Gama", "query": "Vasco da Gama futebol"},
    "botafogo": {"label": "Botafogo", "query": "Botafogo futebol"},
    "fluminense": {"label": "Fluminense", "query": "Fluminense futebol"},
}

HEADLINES_PER_CLUB = 8
HTML_FILE = "retrospectiva.html"
ANTHROPIC_MODEL = "claude-sonnet-5"


def fetch_headlines(query: str, limit: int = HEADLINES_PER_CLUB):
    url = f"https://news.google.com/rss/search?q={query.replace(' ', '+')}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    feed = feedparser.parse(url)
    return [entry.title for entry in feed.entries[:limit]]


def build_prompt(all_headlines):
    sections = []
    for key, info in CLUBS.items():
        headlines = "\n".join(f"- {h}" for h in all_headlines[key])
        sections.append(f"### {info['label']}\n{headlines}")
    manchetes = "\n\n".join(sections)

    return f"""Você escreve a coluna semanal de um jornal esportivo carioca chamado
"Big Four", que cobre Flamengo, Vasco da Gama, Botafogo e Fluminense.

Com base nas manchetes recentes abaixo (colhidas de fontes esportivas),
escreva uma "Retrospectiva da Semana": um texto de análise original, em
português do Brasil, comentando o momento de cada um dos quatro clubes.

Manchetes recentes por clube:

{manchetes}

Regras:
- Escreva UMA seção por clube, nesta ordem: Flamengo, Vasco da Gama, Botafogo, Fluminense.
- Cada seção deve ter um título curto (uma frase de efeito sobre o momento do clube)
  seguido de 2 a 3 parágrafos de análise (não apenas resumo das manchetes — dê uma
  leitura própria, contextualize, comente tendências).
- Tom: jornalístico, seguro, mas com voz própria — como uma coluna de opinião, não
  um press release.
- NÃO invente resultados, números ou fatos que não estejam implícitos nas manchetes.
  Se as manchetes forem vagas, comente de forma mais genérica em vez de inventar.
- Formate a resposta em HTML simples, usando apenas as tags <h3> para os títulos de
  seção e <p> para os parágrafos. Não use markdown, não use ```html, não escreva
  nada fora desse HTML (sem saudação, sem introdução, sem comentário final).
"""


def call_anthropic(prompt: str) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Variável de ambiente ANTHROPIC_API_KEY não encontrada. "
            "Crie uma chave em https://console.anthropic.com e configure-a "
            "como variável de ambiente (ou Secret do GitHub Actions)."
        )

    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": ANTHROPIC_MODEL,
            "max_tokens": 2000,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()

    text_parts = [block["text"] for block in data.get("content", []) if block.get("type") == "text"]
    text = "".join(text_parts).strip()

    # Segurança: remove blocos de código markdown, caso o modelo os inclua por engano.
    text = re.sub(r"^```html\s*", "", text)
    text = re.sub(r"```\s*$", "", text)
    return text.strip()


def update_html(retro_html: str):
    with open(HTML_FILE, encoding="utf-8") as f:
        content = f.read()

    retro_pattern = re.compile(r"<!-- RETRO-START -->.*?<!-- RETRO-END -->", re.DOTALL)
    date_pattern = re.compile(r"<!-- RETRO-DATE-START -->.*?<!-- RETRO-DATE-END -->", re.DOTALL)
    adslot_pattern = re.compile(r"<!-- ADSLOT-START -->.*?<!-- ADSLOT-END -->", re.DOTALL)

    if not retro_pattern.search(content) or not date_pattern.search(content) or not adslot_pattern.search(content):
        raise RuntimeError(
            "Não encontrei os marcadores RETRO-START/RETRO-END, "
            "RETRO-DATE-START/RETRO-DATE-END ou ADSLOT-START/ADSLOT-END "
            "no retrospectiva.html. Use a versão do arquivo que já inclui "
            "esses blocos."
        )

    hoje = datetime.date.today().strftime("%d/%m/%Y")
    new_retro_block = f'<!-- RETRO-START -->\n  <div class="retro" id="retro">\n{retro_html}\n  </div>\n  <!-- RETRO-END -->'
    new_date_block = f'<!-- RETRO-DATE-START -->\n    <div class="date">Publicada em {hoje}</div>\n    <!-- RETRO-DATE-END -->'

    # O anúncio só é inserido aqui, quando já existe conteúdo de verdade —
    # antes disso a página fica sem anúncio para não violar a política do
    # AdSense de "telas sem conteúdo do editor".
    new_adslot_block = (
        '<!-- ADSLOT-START -->\n'
        '  <div class="adslot">\n'
        '    <ins class="adsbygoogle"\n'
        '         style="display:block"\n'
        '         data-ad-client="ca-pub-4541574318300832"\n'
        '         data-ad-slot="4348930777"\n'
        '         data-ad-format="auto"\n'
        '         data-full-width-responsive="true"></ins>\n'
        '    <script>\n'
        '         (adsbygoogle = window.adsbygoogle || []).push({});\n'
        '    </script>\n'
        '  </div>\n'
        '  <!-- ADSLOT-END -->'
    )

    content = retro_pattern.sub(new_retro_block, content)
    content = date_pattern.sub(new_date_block, content)
    content = adslot_pattern.sub(new_adslot_block, content)

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print("retrospectiva.html atualizada com sucesso.")


def main():
    all_headlines = {key: fetch_headlines(info["query"]) for key, info in CLUBS.items()}
    prompt = build_prompt(all_headlines)
    retro_html = call_anthropic(prompt)
    update_html(retro_html)


if __name__ == "__main__":
    main()
