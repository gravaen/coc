"""Nouveautés officielles de Clash of Clans partagées sur Discord (salon #actus).

Source : le blog officiel de Supercell (https://supercell.com/en/games/clashofclans/blog/).
Chaque nouvel article (mise à jour, équilibrage, événement, actualité) part une seule fois, avec son image.
Au tout premier passage, seul l'article le plus récent est envoyé ; les plus anciens sont notés comme déjà vus.
Sans webhook (secret DISCORD_ACTUS_WEBHOOK), le script affiche ce qu'il aurait envoyé (essai à blanc).
Mémoire d'un passage à l'autre : data/news.json (publié avec le site, relu au passage suivant).
"""
import datetime
import html
import json
import os
import re
import sys
import urllib.request

BLOG = "https://supercell.com/en/games/clashofclans/blog/"
SITE = "https://supercell.com"
PAGES = os.environ.get("PAGES_URL", "https://gravaen.pages.dev/")
HOOK = os.environ.get("DISCORD_ACTUS_WEBHOOK", "").strip()
NOW = datetime.datetime.now(datetime.timezone.utc)
UA = "Mozilla/5.0 (compatible; GravaenBot/1.0; +https://gravaen.pages.dev)"
LINK = re.compile(r"/en/games/clashofclans/blog/([a-z0-9-]+)/([a-z0-9-]+)/?")
CAT = {"release-notes": "Mise à jour"}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def meta(page, prop):
    m = (re.search(r'<meta[^>]+(?:property|name)="' + re.escape(prop) + r'"[^>]+content="([^"]*)"', page)
         or re.search(r'<meta[^>]+content="([^"]*)"[^>]+(?:property|name)="' + re.escape(prop) + r'"', page))
    return html.unescape(m.group(1)).strip() if m else ""


def articles():
    """Adresses des articles du blog, du plus récent au plus ancien (ordre de la page)."""
    page = get(BLOG)
    out, seen = [], set()
    for m in LINK.finditer(page):
        kind, slug = m.group(1), m.group(2)
        if kind in ("page",) or slug.isdigit():
            continue
        url = f"{SITE}/en/games/clashofclans/blog/{kind}/{slug}/"
        if url not in seen:
            seen.add(url)
            out.append((kind, url))
    if not out:
        raise ValueError(f"aucun article trouvé ({len(page)} caractères)")
    return out


def category(kind, title):
    if kind in CAT:
        return CAT[kind]
    t = title.lower()
    if "balance" in t:
        return "Équilibrage"
    if any(w in t for w in ("update", "patch", "maintenance")):
        return "Mise à jour"
    if any(w in t for w in ("event", "season", "clan games", "challenge", "league")):
        return "Événement"
    return "Actualité"


def message(kind, url):
    page = get(url)
    title = meta(page, "og:title") or meta(page, "twitter:title") or url.rstrip("/").rsplit("/", 1)[-1].replace("-", " ")
    title = re.sub(r"(\s*[|–×-]\s*(Supercell|Clash of Clans)\s*)+$", "", title)
    img = meta(page, "og:image") or meta(page, "twitter:image")
    emb = {
        "author": {"name": "Nouveauté Clash of Clans · " + category(kind, title)},
        "title": title[:250],
        "url": url,
        "description": f"📖 **[Lire l'annonce officielle]({url})**",
        "color": 0xF8C801,
        "footer": {"text": "Source : blog officiel de Supercell"},
    }
    if img:
        emb["image"] = {"url": img}
    return {"username": "Gravaen · actus", "embeds": [emb]}, title


def load():
    try:
        return json.loads(get(PAGES + "data/news.json?ts=" + str(int(NOW.timestamp()))))
    except Exception as e:
        print(f"  news.json précédent introuvable : {e}", file=sys.stderr)
        return {}


def post(msg):
    req = urllib.request.Request(HOOK, data=json.dumps(msg).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "User-Agent": "DiscordBot (gravaen, 1)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        r.read()


def save(state):
    os.makedirs("data", exist_ok=True)
    with open("data/news.json", "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)


def main():
    state = load()
    sent = set(state.get("sent") or [])
    first = not sent
    try:
        arts = articles()
    except Exception as e:
        print(f"  blog illisible : {e}", file=sys.stderr)
        save(state)
        return
    print(f"  actus : {len(arts)} article(s) sur la page, dernier : {arts[0][1]}")
    new = [a for a in arts if a[1] not in sent]
    if first:
        new = new[:1]
    for kind, url in reversed(new[:4]):   # du plus ancien au plus récent, 4 au maximum par passage
        try:
            msg, title = message(kind, url)
        except Exception as e:
            print(f"  article illisible {url} : {e}", file=sys.stderr)
            continue
        if HOOK:
            try:
                post(msg)
                print("actu postée :", title)
            except Exception as e:
                print(f"  actu non postée {url} : {e}", file=sys.stderr)
                continue
        else:
            print(f"[essai à blanc, pas de webhook] {msg['embeds'][0]['author']['name']} · {title} → {url}")
        sent.add(url)
    if first:
        sent.update(u for _, u in arts)
    if HOOK:
        state["sent"] = sorted(sent)[-500:]
    state["last"] = NOW.isoformat(timespec="seconds")
    save(state)


if __name__ == "__main__":
    main()
