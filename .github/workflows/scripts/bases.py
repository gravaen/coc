"""Bases et compos méta partagées automatiquement sur Discord (HDV 16 à 19).

Source : les articles de Blueprint CoC (flux Atom de leur blog, un par HDV).
- Liens « copier la base » (action OpenLayout)  -> salon des bases  (secret DISCORD_BASES_WEBHOOK)
- Liens « copier l'armée » (action CopyArmy)    -> salon des compos (secret DISCORD_COMPOS_WEBHOOK)
- La vidéo YouTube de l'article, s'il y en a une, accompagne le message : vignette en grand et lien « Regarder la vidéo ».

Vérifié toutes les heures : chaque nouvelle base ou compo part dès qu'elle est publiée. Chaque lien n'est partagé qu'une seule fois.
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
import time
import unicodedata
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
LINK = re.compile(r"(https://link\.clashofclans\.com/[^\s\"'<>]*?action=(OpenLayout|CopyArmy)[^\s\"'<>]*)", re.I)
PROMO = re.compile(r"💎|every month|get new|subscribe|discount|sale|pack", re.I)
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
    # émojis et symboles en début ou en fin d'intitulé (️⃣, ▶️, 🔗, 💎…)
    edge = lambda ch: unicodedata.category(ch)[0] in "SMC" or ch in "\ufe0f\u20e3 #*" or ch.isdigit()
    while s and edge(s[0]):
        s = s[1:]
    while s and (unicodedata.category(s[-1])[0] in "SMC" or s[-1] in "\ufe0f\u20e3 "):
        s = s[:-1]
    return s.strip()[:90]


def entries(th):
    """Articles du flux Atom, du plus récent au plus ancien : titre, adresse, date, liens avec leur intitulé."""
    xml = get(FEED.format(th))
    if "<entry" not in xml:
        raise ValueError(f"réponse inattendue ({len(xml)} caractères) : {xml[:120]!r}")
    out = []
    for e in re.findall(r"<entry>(.*?)</entry>", xml, re.S):
        title = text(re.search(r"<title[^>]*>(.*?)</title>", e, re.S).group(1)) if "<title" in e else "Article"
        m = re.search(r'<link[^>]*rel="alternate"[^>]*href="([^"]+)"', e) or re.search(r'<link[^>]*href="([^"]+)"', e)
        url = html.unescape(m.group(1)) if m else "https://blueprintcoc.com"
        pub = (re.search(r"<published>(.*?)</published>", e) or re.search(r"<updated>(.*?)</updated>", e)).group(1)
        c = re.search(r"<content[^>]*>(.*?)</content>", e, re.S)
        body = html.unescape(html.unescape(c.group(1))) if c else ""   # contenu parfois échappé deux fois
        links, seen = [], set()
        # titres de section (ceux qui contiennent eux-mêmes un lien du jeu ne servent pas d'intitulé)
        heads = [(h.end(), text(h.group(1))) for h in HEAD.finditer(body)
                 if "link.clashofclans.com" not in h.group(1) and len(text(h.group(1))) > 2
                 and not PROMO.search(h.group(1))]
        for m2 in LINK.finditer(body):
            href, kind = html.unescape(m2.group(1)).rstrip(".,);"), m2.group(2)
            key = re.sub(r"[?&](?:utm_[^&]*)", "", href)
            if key in seen or "army-link-here" in href:
                continue
            seen.add(key)
            prev = [t for e, t in heads if e <= m2.start()]
            links.append({"url": href, "kind": "base" if kind.lower() == "openlayout" else "army", "label": prev[-1] if prev else title})
        yt = re.search(r"(?:youtube\.com/(?:embed/|watch\?v=)|youtu\.be/)([A-Za-z0-9_-]{11})", body)
        out.append({"title": title, "url": url, "pub": pub, "links": links,
                    "video": ("https://www.youtube.com/watch?v=" + yt.group(1)) if yt else None})
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
    vids = []
    for it in items:
        if it.get("video") and it["video"] not in vids:
            vids.append(it["video"])
    # vignette de la vidéo (image YouTube) en grand dans le message, et lien « Regarder la vidéo » en tête
    vid_id = re.search(r"v=([A-Za-z0-9_-]{11})", vids[0]).group(1) if vids else None
    head = (f"🎬 **[Regarder la vidéo]({vids[0]})**\n\n" if vids else "")
    return {
        "username": "Gravaen · bases" if is_base else "Gravaen · compos",
        "embeds": [{
            "author": {"name": ("Nouvelles bases" if is_base else "Compos méta") + f" · HDV {th}"},
            **({"image": {"url": f"https://i.ytimg.com/vi/{vid_id}/hqdefault.jpg"}} if vid_id else {}),
            "description": head + "\n\n".join(lines) + "\n\n-# Source : " + " · ".join(srcs[:3]) + " (Blueprint CoC)",
            "color": 0xF8C801 if is_base else 0x2F8F55,
            "footer": {"text": "Touchez un lien depuis votre téléphone pour l’ouvrir dans Clash of Clans"},
        }],
    }


def main():
    state = load()
    sent = set(state.get("sent") or [])
    first = not sent
    last = state.get("last")
    if last and not FORCE and NOW - datetime.datetime.fromisoformat(last) < datetime.timedelta(minutes=55):
        print("bases : déjà vérifié il y a moins d'1 h")
        save(state)
        return
    hooks = {"base": HOOK_BASES, "army": HOOK_COMPOS}
    for th in THS:
        try:
            arts = entries(th)
        except Exception as e:
            print(f"  HDV {th} : flux illisible ({e})", file=sys.stderr)
            continue
        print(f"  HDV {th} : {len(arts)} article(s), dernier « {arts[0]['title'] if arts else '-'} » "
              f"({sum(1 for l in (arts[0]['links'] if arts else []) if l['kind'] == 'base')} base(s), "
              f"{sum(1 for l in (arts[0]['links'] if arts else []) if l['kind'] == 'army')} armée(s))")
        time.sleep(2)
        if first:
            arts = arts[:1]
        for kind in ("base", "army"):
            new = []
            for a in arts:
                for l in a["links"]:
                    if l["kind"] == kind and l["url"] not in sent and l["url"] not in {x["url"] for x in new}:
                        new.append({**l, "src": a["title"], "srcurl": a["url"], "video": a.get("video")})
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
