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


def raw_webp(png_bytes):
    """Image d'origine, en couleurs, simplement réduite (220 px de large au plus)."""
    from PIL import Image
    img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    if img.width > 220:
        img = img.resize((220, round(img.height * 220 / img.width)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "WEBP", quality=88, method=6)
    return buf.getvalue()


def icon(name, url, raw=False):
    """Télécharge l'image (avec l'effet, ou en couleurs d'origine si raw) et l'enregistre dans data/icons/<name>.webp."""
    try:
        data = raw_webp(get_bytes(url)) if raw else style(get_bytes(url))
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
    "warTies": clan.get("warTies"),
    "icons": {},
}

# le nom de fichier change avec la ligue, pour que les navigateurs ne gardent pas l'ancienne image en cache
if slug(war_league):
    p = icon("ligue-clans-o-" + slug(war_league), CK + "cwl/" + slug(war_league) + ".png", raw=True)
    if p:
        data["icons"]["war"] = p
if slug(capital_league):
    p = icon("ligue-capitale-o-" + slug(capital_league), CK + "capital-leagues/" + slug(capital_league) + ".png", raw=True)
    if p:
        data["icons"]["capital"] = p
badge = (clan.get("badgeUrls") or {}).get("large")
data["badgeUrl"] = badge  # blason officiel, affiché tel quel depuis les serveurs de Supercell
if badge:
    p = icon("blason-o-" + badge.rstrip("/").split("/")[-1].split(".")[0][:12], badge, raw=True)
    if p:
        data["icons"]["badge"] = p
        try:   # copie au nom fixe : le site l'affiche dès le chargement, sans attendre les serveurs de Supercell
            import shutil
            shutil.copyfile(p, "data/blason.webp")
        except Exception as e:
            print(f"  blason.webp non copié : {e}", file=sys.stderr)
    # vignette des liens partagés (Discord…) : le blason en grand, centré, sur le fond sombre du site
    try:
        from PIL import Image
        _bg = Image.new("RGB", (1200, 630), (33, 35, 32))
        _b = Image.open(io.BytesIO(get_bytes(badge))).convert("RGBA")
        _h = 470
        _b = _b.resize((round(_b.width * _h / _b.height), _h), Image.LANCZOS)
        _bg.paste(_b, ((1200 - _b.width) // 2, (630 - _h) // 2), _b)
        _bg.save("og-image.jpg", "JPEG", quality=92)
        for _n in (192, 512):
            _ic = Image.new("RGB", (_n, _n), (33, 35, 32))
            _hh = int(_n * 0.72)
            _bb = Image.open(io.BytesIO(get_bytes(badge))).convert("RGBA")
            _bb = _bb.resize((round(_bb.width * _hh / _bb.height), _hh), Image.LANCZOS)
            _ic.paste(_bb, ((_n - _bb.width) // 2, (_n - _hh) // 2), _bb)
            _ic.save(f"icon-{_n}.png", "PNG")
    except Exception as e:
        print(f"  vignette non préparée : {e}", file=sys.stderr)

# tuiles du haut : dons de la saison et HDV moyen des membres du clan principal
_members = clan.get("memberList") or []
if _members:
    data["donations"] = sum(m.get("donations", 0) for m in _members)
    _ths = [m.get("townHallLevel") for m in _members if m.get("townHallLevel")]
    if _ths:
        data["thAvg"] = round(sum(_ths) / len(_ths), 1)

def conditions(c):
    """Infos pratiques des cartes : HDV requis, ligue classée requise, membres."""
    out = {"th": c.get("requiredTownhallLevel"), "members": c.get("members"), "wf": c.get("warFrequency"),
           "cwl": (c.get("warLeague") or {}).get("name"),   # ligue de clans du clan, discrète sur sa carte
           "ww": c.get("warWins"), "wl": c.get("warLosses"), "wt": c.get("warTies")}   # bilan de guerre du clan
    if "requiredLeagueTier" in c:  # absent sur les anciennes réponses : la page garde alors son texte
        out["league"] = (c.get("requiredLeagueTier") or {}).get("name") or "Unranked"
    return out


data["clans"] = {"main": conditions(clan)}
data["clans"]["main"]["badge"] = (clan.get("badgeUrls") or {}).get("large")  # blason officiel, affiché sur la carte du clan
clan2 = None
try:
    clan2 = get_json(API + "/clans/" + urllib.parse.quote(TAG2))
    data["clans"]["second"] = conditions(clan2)
    data["clans"]["second"]["badge"] = (clan2.get("badgeUrls") or {}).get("large")
except Exception as e:
    print(f"  clan secondaire non récupéré : {e}", file=sys.stderr)

def side(x):
    x = x or {}
    return x.get("stars"), round(x.get("destructionPercentage") or 0, 1)


def get_or_none(url):
    try:
        return get_json(url)
    except Exception as e:  # journal privé, pas de guerre, API indisponible…
        print(f"  {url.rsplit('/', 1)[-1]} : {e}", file=sys.stderr)
        return None


def when(t):
    """20261112T180000.000Z -> 2026-11-12T18:00:00Z"""
    try:
        return datetime.datetime.strptime(t[:15], "%Y%m%dT%H%M%S").strftime("%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError):
        return None


def roster(side_, other):
    """Une ligne par base, dans l'ordre de la carte : pseudo, HDV, attaques (cible, étoiles, %) et meilleure attaque subie."""
    def order(s):
        return sorted(s.get("members") or [], key=lambda m: m.get("mapPosition", 99))
    pos = {m.get("tag"): i + 1 for i, m in enumerate(order(other))}
    out = []
    for i, m in enumerate(order(side_)):
        atks = sorted(m.get("attacks") or [], key=lambda a: a.get("order", 0))
        b = m.get("bestOpponentAttack")
        out.append({"p": i + 1, "n": m.get("name"), "th": m.get("townhallLevel"), "a": len(atks),
                    "x": [[pos.get(a.get("defenderTag")), a.get("stars", 0), round(a.get("destructionPercentage") or 0)] for a in atks],
                    "b": [pos.get(b.get("attackerTag")), b.get("stars", 0), round(b.get("destructionPercentage") or 0)] if b else None})
    return out


def details(w, cw, us, them):
    """Détail affiché dans le Hall de guerre : score, attaques, blasons et les deux équipes."""
    w["size"] = cw.get("teamSize") or len(us.get("members") or [])
    w["apm"] = cw.get("attacksPerMember") or 1
    w["usAtk"], w["themAtk"] = us.get("attacks", 0), them.get("attacks", 0)
    w["usBadge"] = (us.get("badgeUrls") or {}).get("small")
    w["badge"] = (them.get("badgeUrls") or {}).get("small")
    w["mine"], w["theirs"] = roster(us, them), roster(them, us)


def cwl_war(tag):
    """Pendant la Ligue de clans, /currentwar ne dit rien : la guerre du jour se trouve dans le groupe de ligue."""
    q = urllib.parse.quote(tag)
    g = get_or_none(API + f"/clans/{q}/currentwar/leaguegroup")
    if not g or g.get("state") not in ("preparation", "inWar", "warEnded"):
        return None, None
    rounds = g.get("rounds") or []
    found = []
    for i in range(len(rounds) - 1, max(-1, len(rounds) - 3), -1):  # les deux dernières manches : préparation et bataille
        for wt in rounds[i].get("warTags") or []:
            if not wt or wt == "#0":
                continue
            cw = get_or_none(API + "/clanwarleagues/wars/" + urllib.parse.quote(wt))
            if not cw:
                continue
            if (cw.get("opponent") or {}).get("tag") == tag:
                cw["clan"], cw["opponent"] = cw.get("opponent"), cw.get("clan")
            if (cw.get("clan") or {}).get("tag") == tag:
                found.append((i, cw))
                break
    for st in ("inWar", "preparation", "warEnded"):
        for i, cw in found:
            if cw.get("state") == st:
                return cw, {"round": i + 1, "rounds": len(rounds)}
    return None, None


def hist_of(tag):
    """Dix dernières guerres du journal (résultat et étoiles) : None si le journal est privé ou le clan inconnu."""
    if not tag:
        return None
    log = get_or_none(API + f"/clans/{urllib.parse.quote(tag)}/warlog?limit=10")
    if log is None:
        return None
    out = []
    for it in log.get("items", []):
        us, them = it.get("clan") or {}, it.get("opponent") or {}
        out.append({"r": it.get("result"), "s": us.get("stars"), "t": them.get("stars")})
    return out


def war_of(tag):
    """Pastille des cartes : la guerre en cours (classique ou Ligue de clans), sinon la dernière guerre terminée."""
    q = urllib.parse.quote(tag)
    cw = get_or_none(API + f"/clans/{q}/currentwar")
    cwl = None
    if not cw or cw.get("state") not in ("preparation", "inWar", "warEnded"):
        c2, cwl = cwl_war(tag)
        if c2:
            cw = c2
    if cw and cw.get("state") in ("preparation", "inWar", "warEnded"):
        us, them = cw.get("clan") or {}, cw.get("opponent") or {}
        w = {"state": cw["state"], "start": when(cw.get("startTime")), "end": when(cw.get("endTime")), "opponent": them.get("name")}
        if cwl:
            w["cwl"] = cwl
        try:
            details(w, cw, us, them)
        except Exception as e:
            print(f"  détail de guerre {tag} : {e}", file=sys.stderr)
    else:
        log = get_or_none(API + f"/clans/{q}/warlog?limit=10") or {}
        for item in log.get("items", []):
            them = item.get("opponent") or {}
            if item.get("result") in ("win", "lose", "tie") and them.get("name"):  # les guerres de Ligue de clans n'ont pas d'adversaire nommé
                us = item.get("clan") or {}
                w = {"state": "last", "result": item["result"], "end": when(item.get("endTime")), "opponent": them.get("name")}
                break
        else:
            return None
    w["hist"] = {"m": hist_of(tag), "t": hist_of(them.get("tag"))}
    w["us"], w["usPct"] = side(us)
    w["them"], w["themPct"] = side(them)
    return w


for key, tag in (("main", TAG), ("second", TAG2)):
    if key in data["clans"]:
        w = war_of(tag)
        if w:
            data["clans"][key]["war"] = w

os.makedirs("data", exist_ok=True)
with open("data/clan.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=1)
print(json.dumps(data, ensure_ascii=False))


# ---------------------------------------------------------------------------
# Simulateur de score « meilleur joueur de la saison » et liste noire
# Écrit data/players.json : pour chaque membre des deux clans, ses chiffres de la saison,
# ses points par catégorie (grille du site) et sa place dans un classement commun aux deux clans.
# Les compteurs « depuis le début de la saison » ont besoin d'un point de départ :
# il est repris du fichier déjà en ligne, et remis à zéro à chaque nouvelle saison.
# ---------------------------------------------------------------------------
PAGES = os.environ.get("PAGES_URL", "https://gravaen.pages.dev/")
GRID = {"cwl": (5, 15), "gdc": (4, 10), "cap": (3, 10), "rk": (2, 10), "don": (1, 10)}  # l'activité ne compte plus : on ne peut pas la mesurer pour tout le monde
# Liste noire : points retirés par faute, avec un plafond par faute (total au plus -100)
BLACK = {"rad": 30, "man": 25, "des": 25, "piq": 10, "tou": 10}
# Recalage sur ClashPerk (référence du clan) quand le simulateur a raté des données : voir saison_corrections.json
CORR_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saison_corrections.json")


def corrections(season):
    try:
        with open(CORR_FILE, encoding="utf-8") as f:
            return {t: v for t, v in (json.load(f).get(season) or {}).items() if t.startswith("#")}
    except Exception as e:
        print(f"  corrections illisibles : {e}", file=sys.stderr)
        return {}


def league_tier(name):
    """Mode classé : Légende I > II > III > Électro 33 > … ; les trophées repartent de zéro chaque semaine dans chaque ligue."""
    n = str(name or "")
    if not n or "Unranked" in n:
        return 0
    m = re.match(r"^Legend League (I{1,3})$", n)
    if m:
        return 37 - len(m.group(1))
    d = re.search(r"(\d+)\s*$", n)
    return int(d.group(1)) if d else 0


def season_start(now):
    """Les saisons de Clash of Clans changent le 1er de chaque mois à 5 h UTC (dates ClashKing)."""
    s = datetime.datetime(now.year, now.month, 1, 5, tzinfo=datetime.timezone.utc)
    if now < s:
        s = datetime.datetime(now.year - (now.month == 1), (now.month - 2) % 12 + 1, 1, 5, tzinfo=datetime.timezone.utc)
    return s.strftime("%Y-%m-%d")


CKAPI = "https://api.clashk.ing"


def ck_warhits(tag, start, clans):
    """Guerres du joueur depuis le début de la saison, d'après ClashKing (qui suit Gravaen en continu).
    Renvoie étoiles et destruction en Ligue de clans, étoiles en guerre classique, attaques ratées et oubliées."""
    url = (f"{CKAPI}/player/{urllib.parse.quote(tag)}/warhits?timestamp_start={int(start.timestamp())}"
           f"&timestamp_end={int(datetime.datetime.now(datetime.timezone.utc).timestamp())}&limit=200")
    req = urllib.request.Request(url, headers={"User-Agent": "gravaen-site (github.com/gravaen/coc)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        items = json.load(r).get("items") or []
    o = {"cs": 0, "cd": 0, "gs": 0, "zero": 0, "one": 0, "missed": 0, "wars": 0,
         "det": {"cwl": [], "war": []}}  # détail des attaques, pour les fiches du staff
    for it in items:
        w, me = it.get("war_data") or {}, it.get("member_data") or {}
        if (w.get("clan") or {}).get("tag") not in clans or w.get("type") == "friendly":
            continue
        atks = it.get("attacks") or []
        th = me.get("townhallLevel") or 0
        stars = sum(a.get("stars", 0) for a in atks)
        o["wars"] += 1
        start_ = w.get("preparationStartTime") or w.get("startTime") or ""
        if w.get("type") == "cwl":
            o["cs"] += stars
            o["cd"] += sum(a.get("destructionPercentage", 0) for a in atks)
            a0 = atks[0] if atks else {}
            o["det"]["cwl"].append([start_, a0.get("stars", 0), a0.get("destructionPercentage", 0),
                                    (a0.get("defender") or {}).get("townhallLevel", 0), len(atks)])
        else:
            o["gs"] += stars
            for a in atks:
                o["det"]["war"].append([start_, a.get("stars", 0), a.get("destructionPercentage", 0),
                                        (a.get("defender") or {}).get("townhallLevel", 0)])
            if w.get("state") == "warEnded":
                o["det"].setdefault("missed", 0)
                o["det"]["missed"] += max(0, (w.get("attacksPerMember") or 2) - len(atks))
        for a in atks:
            if (a.get("defender") or {}).get("townhallLevel", 99) <= th:
                o["zero"] += a.get("stars", 0) == 0
                o["one"] += a.get("stars", 0) == 1
        if w.get("state") == "warEnded":
            per = 1 if w.get("type") == "cwl" else (w.get("attacksPerMember") or 2)
            o["missed"] += max(0, per - len(atks))
    return o


def activity_days():
    """Jours actifs de chaque membre sur la saison, relevés toutes les 15 min par staff.py (façon ClashPerk)."""
    try:
        with urllib.request.urlopen(urllib.request.Request(PAGES + "data/staff.json?ts=" + str(int(datetime.datetime.now().timestamp())), headers={"User-Agent": "Mozilla/5.0 (compatible; GravaenBot/1.0; +https://gravaen.pages.dev)"}), timeout=20) as r:
            st = json.loads(r.read().decode())
    except Exception:
        return {}, None
    return {t: s for t, s in (st.get("seen") or {}).items()}, st.get("tracking")


def previous_players():
    try:
        with urllib.request.urlopen(urllib.request.Request(PAGES + "data/players.json?ts=" + str(int(datetime.datetime.now().timestamp())), headers={"User-Agent": "Mozilla/5.0 (compatible; GravaenBot/1.0; +https://gravaen.pages.dev)"}), timeout=20) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print(f"  players.json précédent introuvable : {e}", file=sys.stderr)
        return {}


def rank_points(values, top, tie=None):
    """values : {tag: valeur}. 1er = top pts, 2e = top-1… ; égalité parfaite = mêmes points, au meilleur rang ; 0 = absent."""
    key = (lambda t: (values[t], tie[t])) if tie else (lambda t: values[t])
    order = sorted([t for t in values if values[t] > 0], key=key, reverse=True)
    pts, prev, prev_rank = {}, None, 0
    for i, t in enumerate(order):
        r = prev_rank if prev is not None and key(t) == prev else i + 1
        prev, prev_rank = key(t), r
        if r <= top:
            pts[t] = (top + 1 - r, r)
    return pts


def bad(m, foe, stars):
    """Attaques ratées (0 ou 1 étoile) sur une cible de niveau d'HDV égal ou inférieur : viser plus haut n'est pas puni."""
    th = m.get("townhallLevel") or 0
    return sum(1 for a in m.get("attacks") or []
               if a.get("stars", 0) == stars and foe.get(a.get("defenderTag"), 0) <= th)


# niveau max des héros par HDV (Roi, Reine, Prince, Gardien, Championne, Duc) : même table que le Worker des candidatures
HERO_CAPS = {7: [10, 0, 0, 0, 0, 0], 8: [20, 10, 0, 0, 0, 0], 9: [30, 30, 10, 0, 0, 0], 10: [40, 40, 20, 0, 0, 0],
             11: [50, 50, 30, 20, 0, 0], 12: [65, 65, 40, 40, 0, 0], 13: [75, 75, 50, 50, 25, 0], 14: [85, 85, 60, 60, 30, 0],
             15: [90, 90, 70, 65, 40, 10], 16: [95, 95, 80, 70, 45, 15], 17: [100, 100, 90, 75, 50, 20], 18: [110, 110, 95, 85, 55, 25]}
HERO_NAMES = ["Barbarian King", "Archer Queen", "Minion Prince", "Grand Warden", "Royal Champion", "Dragon Duke"]


def hero_progress(p):
    """Part des niveaux de héros atteints par rapport au max de son HDV (1 = compte accompli)."""
    caps = HERO_CAPS.get(min(18, max(7, p.get("townHallLevel") or 7)))
    lv = {h["name"]: h.get("level", 0) for h in p.get("heroes") or [] if h.get("village") == "home"}
    tot = sum(caps)
    return round(sum(min(lv.get(n, 0), c) for n, c in zip(HERO_NAMES, caps)) / tot, 3) if tot else 1


PETS = {"L.A.S.S.I", "Electro Owl", "Mighty Yak", "Unicorn", "Frosty", "Diggy", "Poison Lizard", "Phoenix",
        "Spirit Fox", "Angry Jelly", "Sneezy", "Greedy Raven"}
SIEGE = {"Wall Wrecker", "Battle Blimp", "Stone Slammer", "Siege Barracks", "Log Launcher", "Flame Flinger",
         "Battle Drill", "Troop Launcher"}
SUPER = {"Super Barbarian", "Super Archer", "Super Giant", "Sneaky Goblin", "Super Wall Breaker", "Rocket Balloon",
         "Super Wizard", "Super Dragon", "Inferno Dragon", "Super Minion", "Super Valkyrie", "Super Witch", "Ice Hound",
         "Super Bowler", "Super Miner", "Super Hog Rider", "Super Yeti"}


def _ts(x):
    try:
        return int(datetime.datetime.strptime((x or "")[:15], "%Y%m%dT%H%M%S").replace(tzinfo=datetime.timezone.utc).timestamp())
    except ValueError:
        return 0


def ck_hits90(tag, clans):
    """Attaques et défenses des 90 derniers jours (guerre et ligue de clans), pour les moyennes des fiches du staff."""
    now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    url = (f"{CKAPI}/player/{urllib.parse.quote(tag)}/warhits?timestamp_start={now - 90 * 86400}&timestamp_end={now}&limit=500")
    req = urllib.request.Request(url, headers={"User-Agent": "gravaen-site (github.com/gravaen/coc)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        items = json.load(r).get("items") or []
    atk, dfn = [], []
    for it in items:
        w = it.get("war_data") or {}
        if (w.get("clan") or {}).get("tag") not in clans or w.get("type") == "friendly":
            continue
        kind, ts = ("cwl" if w.get("type") == "cwl" else "war"), _ts(w.get("endTime") or w.get("startTime"))
        for a in it.get("attacks") or []:
            atk.append([ts, kind, a.get("stars", 0), a.get("destructionPercentage", 0)])
        for a in it.get("defenses") or []:
            dfn.append([ts, kind, a.get("stars", 0), a.get("destructionPercentage", 0)])
    return {"atk": atk, "def": dfn}


def previous_fiches():
    try:
        with urllib.request.urlopen(urllib.request.Request(PAGES + "data/fiches.json?ts=" + str(int(datetime.datetime.now().timestamp())), headers={"User-Agent": "Mozilla/5.0 (compatible; GravaenBot/1.0; +https://gravaen.pages.dev)"}), timeout=20) as r:
            return json.loads(r.read().decode()).get("players") or {}
    except Exception:
        return {}


def fiche(p, k_, key):
    """Fiche détaillée d'un membre du staff (page joueur.html) : ligue de clans, guerres, armée."""
    home = lambda xs: [x for x in xs or [] if x.get("village") == "home"]
    lvl = lambda x: [x.get("name"), x.get("level", 0), x.get("maxLevel", 0)]
    troops = home(p.get("troops"))
    det = (k_ or {}).get("det") or {}
    cwl = [r[1:] for r in sorted(det.get("cwl") or [], key=lambda r: r[0])][:7]
    war = det.get("war") or []
    lt = p.get("leagueTier") or p.get("league") or {}
    return {"n": p.get("name"), "c": key, "th": p.get("townHallLevel"), "xp": p.get("expLevel"), "role": p.get("role"),
            "tr": p.get("trophies", 0), "best": p.get("bestTrophies", 0), "wsT": p.get("warStars", 0),
            "lg": lt.get("name"), "lgi": (lt.get("iconUrls") or {}).get("medium") or (lt.get("iconUrls") or {}).get("small"),
            "cwl": cwl,
            "war": {"atk": len(war), "tri": sum(1 for a in war if a[1] == 3), "stars": sum(a[1] for a in war),
                    "pct": round(sum(a[2] for a in war) / len(war), 1) if war else 0, "missed": det.get("missed", 0)},
            "army": {"heroes": [lvl(h) + [[[e.get("name"), e.get("level", 0)] for e in h.get("equipment") or []]]
                                for h in home(p.get("heroes"))],
                     "equip": [lvl(e) for e in home(p.get("heroEquipment"))],
                     "troops": [lvl(t) for t in troops if t.get("name") not in PETS | SIEGE | SUPER],
                     "spells": [lvl(t) for t in home(p.get("spells"))],
                     "pets": [lvl(t) for t in troops if t.get("name") in PETS],
                     "siege": [lvl(t) for t in troops if t.get("name") in SIEGE]}}


def season_scores():
    now = datetime.datetime.now(datetime.timezone.utc)
    season = season_start(now)
    old = previous_players()
    same = old.get("season") == season
    base = old.get("base", {}) if same else {}
    cwl_log = old.get("cwlLog", {}) if same else {}
    war_log = old.get("warLog", {}) if same else {}    # guerres classiques de la saison
    raid_log = old.get("raidLog", {}) if same else {}  # week-ends de raid de la saison
    corr = corrections(season)
    corr_done = same and old.get("corrApplied") == season  # recalage des points de départ : une seule fois par saison
    fiches = {}
    out = {"season": season, "updated": data["updated"], "base": base, "cwlLog": cwl_log,
           "warLog": war_log, "raidLog": raid_log, "players": {}}
    season_iso = season.replace("-", "")  # 20261026, comparable aux dates de l'API

    start = datetime.datetime.strptime(season, "%Y-%m-%d").replace(hour=5, tzinfo=datetime.timezone.utc)
    # ClashKing : guerres du joueur depuis le début de la saison (relu au plus toutes les 2 h)
    ck_old = old.get("ck", {}) if same else {}
    ck_fresh = same and old.get("ckAt") and (now - datetime.datetime.fromisoformat(old["ckAt"])) < datetime.timedelta(hours=2)
    ck = dict(ck_old) if ck_fresh else {}
    out["ck"], out["ckAt"] = ck, (old.get("ckAt") if ck_fresh else now.isoformat(timespec="seconds"))
    seen, tracking = activity_days()
    raid_loot = {}

    vals = {k: {} for k in GRID}  # un seul classement pour les deux clans
    tie = {}
    for key, tag, c in (("main", TAG, clan), ("second", TAG2, clan2)):
        if not c:
            continue
        # Ligue de clans : étoiles et destruction de chaque guerre, gardées guerre par guerre
        g = get_or_none(API + f"/clans/{urllib.parse.quote(tag)}/currentwar/leaguegroup")
        for rnd in (g or {}).get("rounds") or []:
            for wt in rnd.get("warTags") or []:
                if not wt or wt == "#0":
                    continue
                cw = get_or_none(API + "/clanwarleagues/wars/" + urllib.parse.quote(wt))
                if not cw or cw.get("state") not in ("inWar", "warEnded"):
                    continue
                side_ = cw["clan"] if (cw.get("clan") or {}).get("tag") == tag else cw.get("opponent") if (cw.get("opponent") or {}).get("tag") == tag else None
                if not side_:
                    continue
                ended = cw.get("state") == "warEnded"
                other = cw["opponent"] if side_ is cw["clan"] else cw["clan"]
                foe = {x["tag"]: x.get("townhallLevel", 0) for x in other.get("members") or []}
                cwl_log[wt] = {m["tag"]: [sum(a.get("stars", 0) for a in m.get("attacks") or []),
                                           sum(a.get("destructionPercentage", 0) for a in m.get("attacks") or []),
                                           bad(m, foe, 0), bad(m, foe, 1),
                                           1 if ended and not m.get("attacks") else 0]
                               for m in side_.get("members") or []}

        # Guerre classique en cours ou juste finie : attaques ratées et attaques oubliées
        cw = get_or_none(API + f"/clans/{urllib.parse.quote(tag)}/currentwar")
        if cw and cw.get("state") in ("inWar", "warEnded") and (cw.get("startTime") or "")[:8] >= season_iso:
            per = cw.get("attacksPerMember") or 2
            ended = cw["state"] == "warEnded"
            foe = {x["tag"]: x.get("townhallLevel", 0) for x in (cw.get("opponent") or {}).get("members") or []}
            war_log[tag + cw["startTime"]] = {m["tag"]: [bad(m, foe, 0), bad(m, foe, 1),
                                                        max(0, per - len(m.get("attacks") or [])) if ended else 0]
                                              for m in (cw.get("clan") or {}).get("members") or []}

        # Raids de la capitale terminés pendant la saison : attaques non jouées par membre
        rs = get_or_none(API + f"/clans/{urllib.parse.quote(tag)}/capitalraidseasons?limit=6") or {}
        for it in rs.get("items") or []:
            if (it.get("startTime") or "")[:8] >= season_iso:  # or de capitale pillé par chacun pendant la saison
                for mm in it.get("members") or []:
                    raid_loot[mm["tag"]] = raid_loot.get(mm["tag"], 0) + (mm.get("capitalResourcesLooted") or 0)
        for it in rs.get("items") or []:
            k = tag + (it.get("startTime") or "")
            if it.get("state") != "ended" or (it.get("startTime") or "")[:8] < season_iso or k in raid_log:
                continue
            done = {m["tag"]: max(0, (m.get("attackLimit") or 5) - (m.get("attacks") or 0)) for m in it.get("members") or []}
            # les membres présents qui n'ont pas joué du tout : 5 attaques perdues
            raid_log[k] = {m["tag"]: done.get(m["tag"], 5) for m in c.get("memberList") or []}

        for m in c.get("memberList") or []:
            p = get_or_none(API + "/players/" + urllib.parse.quote(m["tag"]))
            if not p:
                continue
            t = p["tag"]
            ach = {a.get("name"): a.get("value", 0) for a in p.get("achievements") or []}
            heist = ach.get("Heroic Heist", 0)
            now_v = {"ws": p.get("warStars", 0), "cap": p.get("clanCapitalContributions", 0), "tr": p.get("trophies", 0), "dee": heist,
                     "fin": ach.get("Friend in Need", 0), "agc": ach.get("Aggressive Capitalism", 0)}
            b = base.setdefault(t, dict(now_v))  # nouveau venu : on part de ses chiffres du jour
            for k_b in ("dee", "fin", "agc"):
                b.setdefault(k_b, now_v[k_b])
            cp = corr.get(t) or next((v_ for v_ in corr.values() if v_.get("n") == p.get("name")
                                      and abs((v_.get("th") or p.get("townHallLevel") or 0) - (p.get("townHallLevel") or 0)) <= 1), {})
            if cp and not corr_done:  # recale le point de départ pour retrouver les chiffres de ClashPerk
                if "ws" in cp:
                    b["ws"] = now_v["ws"] - cp["ws"]
                if "don" in cp:
                    b["fin"] = now_v["fin"] - cp["don"]
                if "loot" in cp:
                    b["agc"] = now_v["agc"] - cp["loot"]
            if t not in ck:
                try:
                    ck[t] = ck_warhits(t, start, (TAG, TAG2))
                except Exception as e:
                    print(f"  ClashKing {t} : {e}", file=sys.stderr)
            k_ = ck.get(t)
            if k_:  # guerres de toute la saison, d'après ClashKing
                cs, cd, gs = k_["cs"], k_["cd"], k_["gs"]
            else:   # repli : seulement ce que le script a vu lui-même
                cs = sum(w[t][0] for w in cwl_log.values() if t in w)
                cd = sum(w[t][1] for w in cwl_log.values() if t in w)
                gs = max(0, now_v["ws"] - b["ws"] - cs)
            if cp.get("cwl") and (cp["cwl"][0], cp["cwl"][1]) > (cs, cd):  # Ligue de clans relevée sur ClashPerk
                cs, cd = cp["cwl"][0], cp["cwl"][1]
            gs = max(gs, now_v["ws"] - b["ws"] - cs)                     # étoiles de guerre gagnées, ligue déduite
            sn = seen.get(t) or {}
            act_days = len([d for d in sn.get("md", []) if d >= season]) if sn else None
            lt = p.get("leagueTier") or p.get("league") or {}
            v = {"cwl": cs, "gdc": gs, "cap": max(raid_loot.get(t, 0), now_v["agc"] - b["agc"]),
                 # activité : score façon ClashPerk (+1 par heure où une activité est repérée), sinon les jours actifs
                 "rk": now_v["tr"], "act": (sn.get("ma") if sn.get("ms") == season and sn.get("ma") is not None else act_days) if act_days is not None else p.get("attackWins", 0),
                 "actd": act_days or 0,
                 # dons de la saison, même en changeant de clan (le compteur du jeu repart à zéro à chaque changement)
                 "don": max(p.get("donations", 0), now_v["fin"] - b["fin"])}
            for k in GRID:
                vals[k][t] = v[k]
            tier = league_tier(lt.get("name"))
            vals["rk"][t] = tier * 10000 + now_v["tr"] if tier else 0  # classé : la ligue d'abord, puis les trophées
            tie[t] = cd
            out["players"][t] = {"n": p.get("name"), "c": key, "th": p.get("townHallLevel"), "v": v, "cwlPct": cd,
                                 "lg": lt.get("name"), "lgi": (lt.get("iconUrls") or {}).get("small"),
                                 "dee": max(0, heist - b["dee"]), "hp": hero_progress(p),
                                 # pour la section staff du site : grade et quelques chiffres de carrière
                                 "role": p.get("role"), "wsT": p.get("warStars", 0), "xp": p.get("expLevel")}
            if True:   # fiche pour chaque membre : profil ouvert depuis le staff et depuis « Notre classement »
                try:
                    fiches[t] = fiche(p, k_, key)
                except Exception as e:
                    print(f"  fiche {t} : {e}", file=sys.stderr)

            # Liste noire
            if k_:
                zero, one, missed = k_["zero"], k_["one"], k_["missed"]
            else:
                wars = [w[t] for w in cwl_log.values() if t in w and len(w[t]) >= 5]
                zero = sum(x[2] for x in wars) + sum(w[t][0] for w in war_log.values() if t in w)
                one = sum(x[3] for x in wars) + sum(w[t][1] for w in war_log.values() if t in w)
                missed = sum(x[4] for x in wars) + sum(w[t][2] for w in war_log.values() if t in w)
            # Maître Bivouac : jours sans aucune activité, comptés depuis le début du suivi d'activité
            t0 = max(start, datetime.datetime.fromisoformat(tracking)) if tracking else start
            days = max(0, (now - t0).days)
            m_ = {"rad": max(0, p.get("donationsReceived", 0) - p.get("donations", 0)) // 50,
                  "man": 3 * zero + one,
                  "des": 5 * missed,
                  "piq": sum(r[t] for r in raid_log.values() if t in r),
                  "tou": max(0, days - act_days) if act_days is not None else max(0, days - p.get("attackWins", 0))}
            m_ = {k: min(BLACK[k], v_) for k, v_ in m_.items()}
            out["players"][t]["m"] = m_
            out["players"][t]["bl"] = -sum(m_.values())

    if corr:
        out["corrApplied"] = season
    pts = {k: rank_points(vals[k], GRID[k][1], tie if k == "cwl" else None) for k in GRID}
    tags = list(out["players"])
    for t in tags:
        x = out["players"][t]
        x["p"] = {k: (pts[k][t][0] * GRID[k][0] if t in pts[k] else 0) for k in GRID}
        x["r"] = {k: (pts[k][t][1] if t in pts[k] else None) for k in GRID}
        x["score"] = round(sum(x["p"].values()), 1)
    for i, t in enumerate(sorted(tags, key=lambda t: out["players"][t]["score"], reverse=True)):
        out["players"][t]["rank"] = i + 1
        out["players"][t]["of"] = len(tags)
    # liste noire : le plus gros score négatif est 1er
    for i, t in enumerate(sorted([t for t in tags if out["players"][t]["bl"] < 0], key=lambda t: out["players"][t]["bl"])):
        out["players"][t]["blr"] = i + 1

    # badges affichés sur le site : ceux de la dernière saison terminée, gardés tels quels pendant toute la saison suivante
    # (à la fin de la saison suivante, ils sont remplacés par les siens) ; tant qu'aucune saison n'est figée, la saison en cours
    def bset(x):
        r_ = x.get("r") or {}
        return (["champ"] if x.get("rank") == 1 else []) + [k for k in GRID if r_.get(k) and r_[k] <= 3]
    frozen = old.get("badges") if same else None
    if not same and old.get("players"):
        frozen = {"season": old.get("season"),
                  "p": {t: {"b": bset(x), "r": x.get("r") or {}, "rank": x.get("rank")} for t, x in old["players"].items()}}
    elif not same:
        frozen = old.get("badges")
    if frozen:
        out["badges"] = frozen
        for t in tags:
            fz = frozen["p"].get(t) or {}
            out["players"][t].update(b=fz.get("b", []), br=fz.get("r", {}), brank=fz.get("rank"))

    with open("data/players.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    # fiches du staff : moyennes sur 90 jours, comparaison au reste de Gravaen, historique saison après saison
    prevf = previous_fiches()
    fam = {}
    for t_, kk in ck.items():   # attaques de la saison de chaque membre (ligue + guerre), pour « face à Gravaen »
        d_ = (kk or {}).get("det") or {}
        hits = [(r[1], r[2]) for r in d_.get("cwl") or [] if r[4]] + [(a[1], a[2]) for a in d_.get("war") or []]
        if len(hits) >= 5 and t_ in out["players"]:
            fam[t_] = (sum(1 for h in hits if h[0] == 3) / len(hits) * 100, sum(h[1] for h in hits) / len(hits))
    monday = (now - datetime.timedelta(days=now.weekday())).strftime("%Y-%m-%d")
    for t_, fi in fiches.items():
        pf_ = prevf.get(t_) or {}
        try:   # 90 jours relus au plus toutes les 2 h par joueur (ClashKing), sinon la dernière lecture
            if pf_.get("hitsAt") and pf_.get("hits") and (now - datetime.datetime.fromisoformat(pf_["hitsAt"])) < datetime.timedelta(hours=2):
                fi["hits"], fi["hitsAt"] = pf_["hits"], pf_["hitsAt"]
            else:
                fi["hits"], fi["hitsAt"] = ck_hits90(t_, (TAG, TAG2)), now.isoformat(timespec="seconds")
        except Exception as e:
            print(f"  ClashKing 90 j {t_} : {e}", file=sys.stderr)
            fi["hits"], fi["hitsAt"] = pf_.get("hits") or {"atk": [], "def": []}, pf_.get("hitsAt")
        if t_ in fam and len(fam) > 1:
            me, others = fam[t_], [v_ for k2, v_ in fam.items() if k2 != t_]
            fi["fam"] = {"n": len(fam), "tri": round(me[0]), "triBetter": round(sum(1 for o in others if o[0] < me[0]) / len(others) * 100),
                         "triAvg": round(sum(v_[0] for v_ in fam.values()) / len(fam)), "pct": round(me[1]),
                         "pctBetter": round(sum(1 for o in others if o[1] < me[1]) / len(others) * 100),
                         "pctAvg": round(sum(v_[1] for v_ in fam.values()) / len(fam))}
        x = out["players"].get(t_) or {}
        h_ = (prevf.get(t_) or {}).get("hist") or {"s": {}, "w": {}, "since": now.strftime("%Y-%m-%d")}
        h_["s"][season] = {"score": x.get("score", 0), "rank": x.get("rank"), "of": x.get("of"), "cwl": (x.get("v") or {}).get("cwl", 0),
                           "lg": fi.get("lg"), "lgi": fi.get("lgi"), "tr": fi.get("tr", 0)}
        h_["w"][monday] = [fi.get("lg"), fi.get("lgi"), fi.get("tr", 0)]   # écrasé à chaque passage : reste la valeur de fin de semaine
        h_["s"] = dict(sorted(h_["s"].items())[-12:])
        h_["w"] = dict(sorted(h_["w"].items())[-12:])
        fi["hist"] = h_
    with open("data/fiches.json", "w", encoding="utf-8") as f:   # fiches détaillées du staff (joueur.html)
        json.dump({"season": season, "updated": data["updated"], "players": fiches}, f, ensure_ascii=False, separators=(",", ":"))
    print(f"  players.json : {len(out['players'])} joueurs, saison du {season}")


try:
    season_scores()
except Exception as e:  # le simulateur ne doit jamais bloquer la mise à jour du site
    print(f"  simulateur non mis à jour : {e}", file=sys.stderr)
