
import os
import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

BLOG_URL = "https://www.hauntedchocolatier.net/"
FEED_URL = BLOG_URL + "feed/"
STATE_FILE = Path("last_post.json")


def fetch(url):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "HauntedChocolatierUpdateBot/1.0"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def send_telegram(message):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": message,
        "disable_web_page_preview": "false",
    }).encode()

    request = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.loads(response.read())

    if not result.get("ok"):
        raise RuntimeError("Telegram kunne ikke sende beskeden")


def main():
    root = ET.fromstring(fetch(FEED_URL))
    items = root.findall("./channel/item")

    if not items:
        raise RuntimeError(
            "RSS-feedet indeholder ingen indlæg. "
            "Kontrollér feedets format."
        )

    posts = []
    for item in items:
        title = item.findtext("title", default="Nyt blogindlæg")
        link = item.findtext("link", default="")
        if link:
            posts.append({"title": title, "link": link})

    if not posts:
        raise RuntimeError("Kunne ikke finde blogindlæg i feedet")

    latest_link = posts[0]["link"]

    if not STATE_FILE.exists():
        STATE_FILE.write_text(
            json.dumps({"latest": latest_link}),
            encoding="utf-8"
        )
        print("Første kørsel: gemmer seneste indlæg uden notifikation.")
        return

    state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    previous_link = state.get("latest")

    if latest_link == previous_link:
        print("Ingen nye blogindlæg.")
        return

    new_posts = []
    for post in posts:
        if post["link"] == previous_link:
            break
        new_posts.append(post)

    if not new_posts:
        raise RuntimeError(
            "Sidste kendte indlæg findes ikke i feedet. "
            "Stopper for at undgå falske notifikationer."
        )

    for post in reversed(new_posts):
        send_telegram(
            "🍫 Nyt Haunted Chocolatier-blogindlæg!\n\n"
            f"{post['title']}\n{post['link']}"
        )

    STATE_FILE.write_text(
        json.dumps({"latest": latest_link}),
        encoding="utf-8"
    )
    print(f"Sendte {len(new_posts)} notifikation(er).")


if __name__ == "__main__":
    main()
