"""Récupère les chiffres du clan Gravaen et prépare les icônes du haut de page.

Lancé par .github/workflows/site.yml. La clé de l'API Clash of Clans est lue dans
la variable d'environnement COC_TOKEN (secret GitHub), jamais écrite ici.

Écrit :
  data/clan.json          les chiffres affichés en haut de page
  data/icons/*.webp       le blason du clan et les icônes de ligue en cours,
                          passés en noir et blanc avec les parties dorées gardées en or
Icônes de ligue : ClashKing (https://github.com/ClashKingInc/ClashKingAssets).
"""
import datetime
import io
import json
import os
import re
import sys
import urllib.parse
import urllib.request

TAG = "#2C0CVRCPV"  # clan principal
TAG2 = "#2J0UPJVQJ"  # clan secondaire
API = os.environ.get("COC_API_BASE", "https://cocproxy.royaleapi.dev/v1")
CK = "https://raw.githubusercontent.com/ClashKingInc/ClashKingAssets/main/assets/leagues/"
ROMAN = {"I": "1", "II": "2", "III": "3"}


def get_json(url):
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + os.environ["COC_TOKEN"], "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def get_bytes(url):
    req = urllib.request.Request(url, headers={"User-Agent": "gravaen-site"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def slug(name):
    """'Master League III' -> 'master_league_3' ; 'Legend League' -> 'legend_league'"""
    if not name:
        return None
    m = re.match(r"^(\w+) League(?: (I{1,3}))?$", name)
    if m:
        return m.group(1).lower() + "_league" + ("_" + ROMAN[m.group(2)] if m.group(2) else "")
    return "unranked" if name.lower() == "unranked" else None


def style(png_bytes):
    """Noir et blanc + parties dorées gardées en or (même effet que les autres icônes du site)."""
    import numpy as np
    from PIL import Image
    from scipy import ndimage as nd

    img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    up = 2 if img.width < 200 else 1
    if up > 1:
        img = img.resize((img.width * up, img.height * up), Image.LANCZOS)
    a = np.array(img).astype(float) / 255.0
    rgb, al = a[..., :3], a[..., 3]
    mx, mn = rgb.max(-1), rgb.min(-1)
    v = mx
    s = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    d = np.maximum(mx - mn, 1e-6)
    h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    L = 0.2126 * r + 0.7152 * g + 0.0722 * b
    gold = (((h >= 30) & (h <= 68) & (s > 0.42) & (v > 0.42)) | ((h >= 27) & (h < 30) & (s > 0.70) & (v > 0.80))) & (al > 0.4)
    gold = nd.binary_opening(gold, iterations=1)
    lab, n = nd.label(gold)
    if n:
        sz = nd.sum(gold, lab, range(1, n + 1))
        gold = np.isin(lab, [i + 1 for i, x in enumerate(sz) if x >= max(8, gold.size * 0.0015)])
    gold = nd.binary_closing(gold, iterations=1)
    gm = nd.gaussian_filter(gold.astype(float), 0.8 * up).clip(0, 1)
    inb = (al > 0.5) & ~gold
    lo, hi = np.percentile(L[inb], [2, 99]) if inb.sum() > 50 else (0.0, 1.0)
    G = ((L - lo) / max(hi - lo, 1e-3)).clip(0, 1) ** 0.75 * 0.94 + 0.05
    glo, ghi = np.percentile(L[gold], [3, 99.5]) if gold.sum() > 20 else (0.3, 1.0)
    Lg = ((L - glo) / max(ghi - glo, 1e-3)).clip(0, 1)
    H, S, V = 0.115 + 0.02 * Lg, (0.98 - 0.50 * Lg ** 2.2).clip(0, 1), (0.42 + 0.62 * Lg).clip(0, 1)
    i = np.floor(H * 6) % 6
    f = H * 6 - np.floor(H * 6)
    p, q, t = V * (1 - S), V * (1 - f * S), V * (1 - (1 - f) * S)
    goldc = np.zeros(H.shape + (3,))
    for k, (R, Gc, B) in enumerate([(V, t, p), (q, V, p), (p, V, t), (p, q, V), (t, p, V), (V, p, q)]):
        m = i == k
        goldc[m] = np.dstack([R, Gc, B])[m]
    out = np.dstack([G, G, G]) * (1 - gm[..., None]) + goldc * gm[..., None]
    res = Image.fromarray((np.dstack([out, al]) * 255).clip(0, 255).astype("uint8"), "RGBA")
    if up > 1:
        res = res.resize((res.width // up, res.height // up), Image.LANCZOS)
    res = res.crop(res.getbbox())
    if res.width > 220:
        res = res.resize((220, round(res.height * 220 / res.width)), Image.LANCZOS)
    buf = io.BytesIO()
    res.save(buf, "WEBP", quality=88, method=6)
    return buf.getvalue()


def icon(name, url):
    """Télécharge, applique l'effet et enregistre data/icons/<name>.webp ; renvoie le chemin ou None."""
    try:
        data = style(get_bytes(url))
    except Exception as e:  # une icône qui manque ne doit jamais bloquer le reste
        print(f"  icône {name} non préparée : {e}", file=sys.stderr)
        return None
    os.makedirs("data/icons", exist_ok=True)
    path = f"data/icons/{name}.webp"
    with open(path, "wb") as f:
        f.write(data)
    return path


clan = get_json(API + "/clans/" + urllib.parse.quote(TAG))
war_league = (clan.get("warLeague") or {}).get("name")
capital_league = (clan.get("capitalLeague") or {}).get("name")

data = {
    "updated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    "clanLevel": clan.get("clanLevel"),
        "clanPoints": clan.get("clanPoints"),
    "warLeague": war_league,
    "capitalLeague": capital_league,
    "warWinStreak": clan.get("warWinStreak"),
    "warWins": clan.get("warWins"),
    # présent seulement si le journal de guerre du clan est public
    "warLosses": clan.get("warLosses"),
    "icons": {},
}

# le nom de fichier change avec la ligue, pour que les navigateurs ne gardent pas l'ancienne image en cache
if slug(war_league):
    p = icon("ligue-clans-" + slug(war_league), CK + "cwl/" + slug(war_league) + ".png")
    if p:
        data["icons"]["war"] = p
if slug(capital_league):
    p = icon("ligue-capitale-" + slug(capital_league), CK + "capital-leagues/" + slug(capital_league) + ".png")
    if p:
        data["icons"]["capital"] = p
badge = (clan.get("badgeUrls") or {}).get("large")
if badge:
    p = icon("blason-" + badge.rstrip("/").split("/")[-1].split(".")[0][:12], badge)
    if p:
        data["icons"]["badge"] = p

def conditions(c):
    """Infos pratiques des cartes : HDV requis, ligue classée requise, membres."""
    out = {"th": c.get("requiredTownhallLevel"), "members": c.get("members")}
    if "requiredLeagueTier" in c:  # absent sur les anciennes réponses : la page garde alors son texte
        out["league"] = (c.get("requiredLeagueTier") or {}).get("name") or "Unranked"
    return out


data["clans"] = {"main": conditions(clan)}
try:
    data["clans"]["second"] = conditions(get_json(API + "/clans/" + urllib.parse.quote(TAG2)))
except Exception as e:
    print(f"  clan secondaire non récupéré : {e}", file=sys.stderr)

os.makedirs("data", exist_ok=True)
with open("data/clan.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=1)
print(json.dumps(data, ensure_ascii=False))
