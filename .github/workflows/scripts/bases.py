"""Bases et compos méta partagées automatiquement sur Discord (HDV 16 à 19).

Source : les articles de Blueprint CoC (flux Atom de leur blog, un par HDV).
- Liens « copier la base » (action OpenLayout)  -> salon des bases  (secret DISCORD_BASES_WEBHOOK)
- Liens « copier l'armée » (action CopyArmy)    -> salon des compos (secret DISCORD_COMPOS_WEBHOOK)

Une fois par jour au plus. Chaque lien n'est partagé qu'une seule fois.
Au tout premier passage, seuls les liens de l'article le plus récent de chaque HDV sont envoyés
(3 au maximum par HDV), pour ne pas inonder le salon avec l'historique.
Sans webhook, le script affiche dans le journal ce qu'il aurait envoyé (essai à blanc).

Mémoire d'un passage à l'autre : data/bases.json (publié avec le site, relu au passage suivant).
"""
import datetime
import html
import json
import os
import re
import sys
import urllib.request

THS = (19, 18, 17, 16)
FEED = "https://blueprintcoc.com/blogs/town-hall-{}.atom"
PAGES = os.environ.get("PAGES_URL", "https://gravaen.pages.dev/")
HOOK_BASES = os.environ.get("DISCORD_BASES_WEBHOOK", "").strip()
HOOK_COMPOS = os.environ.get("DISCORD_COMPOS_WEBHOOK", "").strip()
FORCE = os.environ.get("BASES_FORCE") == "true"
NOW = datetime.datetime.now(datetime.timezone.utc)
UA = "Mozilla/5.0 (compatible; GravaenBot/1.0; +https://gravaen.pages.dev)"
FIRST_MAX, RUN_MAX = 3, 6
LINK = re.compile(r'href="(https://link\.clashofclans\.com/[^"]*?action=(OpenLayout|CopyArmy)[^"]*)"', re.I)
HEAD = re.compile(r"<h[1-4][^>]*>(.*?)</h[1-4]>", re.I | re.S)


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def text(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"^[#\d.)\-–:\s]+", "", s)
    return s[:90]


def entries(th):
    """Articles du flux Atom, du plus récent au plus ancien : titre, adresse, date, liens avec leur intitulé."""
    xml = get(FEED.format(th))
    out = []
    for e in re.findall(r"<entry>(.*?)</entry>", xml, re.S):
        title = text(re.search(r"<title[^>]*>(.*?)</title>", e, re.S).group(1)) if "<title" in e else "Article"
        m = re.search(r'<link[^>]*rel="alternate"[^>]*href="([^"]+)"', e) or re.search(r'<link[^>]*href="([^"]+)"', e)
        url = html.unescape(m.group(1)) if m else "https://blueprintcoc.com"
        pub = (re.search(r"<published>(.*?)</published>", e) or re.search(r"<updated>(.*?)</updated>", e)).group(1)
        c = re.search(r"<content[^>]*>(.*?)</content>", e, re.S)
        body = html.unescape(c.group(1)) if c else ""
        links, seen, head = [], set(), ""
        pos = 0
        for m2 in re.finditer(HEAD.pattern + "|" + LINK.pattern, body, re.I | re.S):
            if m2.group(1) is not None:          # un titre : il sert d'intitulé aux liens qui suivent
                head = text(m2.group(1))
                continue
            href, kind = html.unescape(m2.group(2)), m2.group(3)
            key = re.sub(r"[?&](?:utm_[^&]*)", "", href)
            if key in seen or "army-link-here" in href:
                continue
            seen.add(key)
            links.append({"url": href, "kind": "base" if kind.lower() == "openlayout" else "army", "label": head or title})
            pos += 1
        out.append({"title": title, "url": url, "pub": pub, "links": links})
    out.sort(key=lambda x: x["pub"], reverse=True)
    return out


def load():
    try:
        return json.loads(get(PAGES + "data/bases.json?ts=" + str(int(NOW.timestamp()))))
    except Exception as e:
        print(f"  bases.json précédent introuvable : {e}", file=sys.stderr)
        return {}


def post(hook, msg):
    req = urllib.request.Request(hook, data=json.dumps(msg).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "User-Agent": "DiscordBot (gravaen, 1)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        r.read()


def message(th, kind, items):
    """Un message par HDV : chaque lien avec son intitulé, et l'article d'origine cité."""
    is_base = kind == "base"
    lines, n = [], 0
    for it in items:
        line = f"**{it['label']}**\n[{'📋 Copier la base' if is_base else '⚔️ Copier l’armée'}]({it['url']})"
        if n + len(line) > 3800:
            break
        lines.append(line)
        n += len(line) + 2
    srcs = []
    for it in items:
        s = f"[{it['src']}]({it['srcurl']})"
        if s not in srcs:
            srcs.append(s)
    return {
        "username": "Gravaen · bases" if is_base else "Gravaen · compos",
        "embeds": [{
            "author": {"name": ("Nouvelles bases" if is_base else "Compos méta") + f" · HDV {th}"},
            "description": "\n\n".join(lines) + "\n\n-# Source : " + " · ".join(srcs[:3]) + " (Blueprint CoC)",
            "color": 0xF8C801 if is_base else 0x2F8F55,
            "footer": {"text": "Touchez un lien depuis votre téléphone pour l’ouvrir dans Clash of Clans"},
        }],
    }


def main():
    state = load()
    sent = set(state.get("sent") or [])
    first = not sent
    last = state.get("last")
    if last and not FORCE and NOW - datetime.datetime.fromisoformat(last) < datetime.timedelta(hours=20):
        print("bases : déjà passé il y a moins de 20 h")
        save(state)
        return
    hooks = {"base": HOOK_BASES, "army": HOOK_COMPOS}
    for th in THS:
        try:
            arts = entries(th)
        except Exception as e:
            print(f"  HDV {th} : flux illisible ({e})", file=sys.stderr)
            continue
        if first:
            arts = arts[:1]
        for kind in ("base", "army"):
            new = []
            for a in arts:
                for l in a["links"]:
                    if l["kind"] == kind and l["url"] not in sent and l["url"] not in {x["url"] for x in new}:
                        new.append({**l, "src": a["title"], "srcurl": a["url"]})
            new = new[:FIRST_MAX if first else RUN_MAX]
            if not new:
                continue
            msg = message(th, kind, new)
            if hooks[kind]:
                try:
                    post(hooks[kind], msg)
                    print(f"HDV {th} · {kind} : {len(new)} lien(s) postés")
                except Exception as e:
                    print(f"  HDV {th} · {kind} non posté : {e}", file=sys.stderr)
                    continue
            else:
                print(f"[essai à blanc, pas de webhook] HDV {th} · {kind} : {len(new)} lien(s)")
                for x in new:
                    print("   ", x["label"], "→", x["url"][:90])
            sent.update(x["url"] for x in new)
        if first:   # au premier passage, tout l'historique visible est noté comme « déjà vu »
            try:
                for a in entries(th):
                    sent.update(l["url"] for l in a["links"])
            except Exception:
                pass
    if HOOK_BASES or HOOK_COMPOS:
        state["sent"] = sorted(sent)[-3000:]
        state["last"] = NOW.isoformat(timespec="seconds")
    save(state)


def save(state):
    os.makedirs("data", exist_ok=True)
    with open("data/bases.json", "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)


if __name__ == "__main__":
    main()
