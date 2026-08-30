"""
Posta atualizações automaticamente num canal do Telegram: um resumo das
principais notícias do dia, ou um aviso quando a retrospectiva semanal é
publicada.

Como funciona:
- Modo "news": busca a manchete mais recente de cada clube (Google News RSS,
  igual ao update_news.py) e monta uma mensagem com as 4 manchetes + link
  do site.
- Modo "retro": manda uma mensagem simples avisando que a retrospectiva da
  semana foi publicada, com o link.

IMPORTANTE:
- Precisa de um bot do Telegram (gratuito). Fale com @BotFather no
  Telegram, use /newbot, e guarde o token gerado.
- Precisa de um canal público no Telegram, com o bot adicionado como
  administrador.
- Configure as variáveis de ambiente TELEGRAM_BOT_TOKEN e
  TELEGRAM_CHAT_ID (ou "Secrets" no GitHub Actions).

Uso local (para testar na sua máquina):
    pip install feedparser requests
    export TELEGRAM_BOT_TOKEN="seu-token-aqui"
    export TELEGRAM_CHAT_ID="@seucanal"
    python post_telegram.py --mode news
    python post_telegram.py --mode retro
"""

import os
import sys
import argparse
import feedparser
import requests

SITE_URL = "https://bigfournoticias-d91s.vercel.app"

CLUBS = {
    "flamengo": {"label": "Flamengo", "query": "Flamengo"},
    "vasco": {"label": "Vasco da Gama", "query": "Vasco da Gama futebol"},
    "botafogo": {"label": "Botafogo", "query": "Botafogo futebol"},
    "fluminense": {"label": "Fluminense", "query": "Fluminense futebol"},
}


def fetch_top_headline(query: str):
    url = f"https://news.google.com/rss/search?q={query.replace(' ', '+')}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    feed = feedparser.parse(url)
    if not feed.entries:
        return None
    return feed.entries[0].title


def send_message(text: str):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError(
            "Faltam as variáveis TELEGRAM_BOT_TOKEN e/ou TELEGRAM_CHAT_ID. "
            "Configure-as como variáveis de ambiente (ou Secrets do GitHub Actions)."
        )

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    response = requests.post(
        url,
        json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        },
        timeout=30,
    )
    if response.status_code != 200:
        raise RuntimeError(
            f"Telegram recusou o envio (status {response.status_code}): {response.text}"
        )
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram recusou o envio: {data}")
    print("Mensagem enviada com sucesso ao Telegram.")


def build_news_message() -> str:
    lines = ["📰 <b>Big Four — atualizado agora</b>", ""]
    for key, info in CLUBS.items():
        headline = fetch_top_headline(info["query"])
        if headline:
            lines.append(f"• <b>{info['label']}:</b> {headline}")
    lines.append("")
    lines.append(f"Leia mais em {SITE_URL}")
    return "\n".join(lines)


def build_retro_message() -> str:
    return (
        "🗞️ <b>Retrospectiva da Semana no ar!</b>\n\n"
        "Análise da semana de Flamengo, Vasco, Botafogo e Fluminense.\n\n"
        f"Confira: {SITE_URL}/retrospectiva.html"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["news", "retro"], required=True)
    args = parser.parse_args()

    if args.mode == "news":
        message = build_news_message()
    else:
        message = build_retro_message()

    send_message(message)


if __name__ == "__main__":
    main()
