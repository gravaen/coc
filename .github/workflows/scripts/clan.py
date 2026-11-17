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

# tuiles du haut : dons de la saison et HDV moyen des membres du clan principal
_members = clan.get("memberList") or []
if _members:
    data["donations"] = sum(m.get("donations", 0) for m in _members)
    _ths = [m.get("townHallLevel") for m in _members if m.get("townHallLevel")]
    if _ths:
        data["thAvg"] = round(sum(_ths) / len(_ths), 1)

def conditions(c):
    """Infos pratiques des cartes : HDV requis, ligue classée requise, membres."""
    out = {"th": c.get("requiredTownhallLevel"), "members": c.get("members"), "wf": c.get("warFrequency")}
    if "requiredLeagueTier" in c:  # absent sur les anciennes réponses : la page garde alors son texte
        out["league"] = (c.get("requiredLeagueTier") or {}).get("name") or "Unranked"
    return out


data["clans"] = {"main": conditions(clan)}
clan2 = None
try:
    clan2 = get_json(API + "/clans/" + urllib.parse.quote(TAG2))
    data["clans"]["second"] = conditions(clan2)
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


def war_of(tag):
    """Pastille des cartes : la guerre en cours, sinon la dernière guerre terminée (None si le journal est privé)."""
    q = urllib.parse.quote(tag)
    cw = get_or_none(API + f"/clans/{q}/currentwar")
    if cw and cw.get("state") in ("preparation", "inWar", "warEnded"):
        us, them = cw.get("clan") or {}, cw.get("opponent") or {}
        w = {"state": cw["state"], "start": when(cw.get("startTime")), "end": when(cw.get("endTime")), "opponent": them.get("name")}
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
PAGES = os.environ.get("PAGES_URL", "https://gravaen.github.io/coc/")
GRID = {"cwl": (5, 15), "gdc": (4, 10), "cap": (3, 10), "rk": (2, 10), "act": (1.5, 10), "don": (1, 10)}
# Liste noire : points retirés par faute, avec un plafond par faute (total au plus -100)
BLACK = {"rad": 30, "man": 25, "des": 25, "piq": 10, "tou": 10}


def season_start(now):
    """Les saisons de Clash of Clans changent le dernier lundi du mois à 5 h UTC."""
    def last_monday(y, m):
        nxt = datetime.datetime(y + (m == 12), m % 12 + 1, 1, 5, tzinfo=datetime.timezone.utc)
        d = nxt - datetime.timedelta(days=1)
        while d.weekday() != 0:
            d -= datetime.timedelta(days=1)
        return d.replace(hour=5)
    s = last_monday(now.year, now.month)
    if now < s:
        y, m = (now.year - 1, 12) if now.month == 1 else (now.year, now.month - 1)
        s = last_monday(y, m)
    return s.strftime("%Y-%m-%d")


def previous_players():
    try:
        with urllib.request.urlopen(PAGES + "data/players.json?ts=" + str(int(datetime.datetime.now().timestamp())), timeout=20) as r:
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


def season_scores():
    now = datetime.datetime.now(datetime.timezone.utc)
    season = season_start(now)
    old = previous_players()
    same = old.get("season") == season
    base = old.get("base", {}) if same else {}
    cwl_log = old.get("cwlLog", {}) if same else {}
    war_log = old.get("warLog", {}) if same else {}    # guerres classiques de la saison
    raid_log = old.get("raidLog", {}) if same else {}  # week-ends de raid de la saison
    out = {"season": season, "updated": data["updated"], "base": base, "cwlLog": cwl_log,
           "warLog": war_log, "raidLog": raid_log, "players": {}}
    season_iso = season.replace("-", "")  # 20261026, comparable aux dates de l'API

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
        rs = get_or_none(API + f"/clans/{urllib.parse.quote(tag)}/capitalraidseasons?limit=5") or {}
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
            now_v = {"ws": p.get("warStars", 0), "cap": p.get("clanCapitalContributions", 0), "tr": p.get("trophies", 0)}
            b = base.setdefault(t, now_v)  # nouveau venu : on part de ses chiffres du jour
            cs = sum(w[t][0] for w in cwl_log.values() if t in w)
            cd = sum(w[t][1] for w in cwl_log.values() if t in w)
            v = {"cwl": cs, "gdc": max(0, now_v["ws"] - b["ws"] - cs), "cap": max(0, now_v["cap"] - b["cap"]),
                 "rk": max(0, now_v["tr"] - b["tr"]), "act": p.get("attackWins", 0), "don": p.get("donations", 0)}
            for k in GRID:
                vals[k][t] = v[k]
            tie[t] = cd
            out["players"][t] = {"n": p.get("name"), "c": key, "th": p.get("townHallLevel"), "v": v, "cwlPct": cd}

            # Liste noire
            wars = [w[t] for w in cwl_log.values() if t in w and len(w[t]) >= 5]
            zero = sum(x[2] for x in wars) + sum(w[t][0] for w in war_log.values() if t in w)
            one = sum(x[3] for x in wars) + sum(w[t][1] for w in war_log.values() if t in w)
            missed = sum(x[4] for x in wars) + sum(w[t][2] for w in war_log.values() if t in w)
            days = (now - datetime.datetime.strptime(season, "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)).days
            m_ = {"rad": max(0, p.get("donationsReceived", 0) - p.get("donations", 0)) // 50,
                  "man": 3 * zero + one,
                  "des": 5 * missed,
                  "piq": sum(r[t] for r in raid_log.values() if t in r),
                  "tou": max(0, days - p.get("attackWins", 0))}
            m_ = {k: min(BLACK[k], v_) for k, v_ in m_.items()}
            out["players"][t]["m"] = m_
            out["players"][t]["bl"] = -sum(m_.values())

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

    with open("data/players.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print(f"  players.json : {len(out['players'])} joueurs, saison du {season}")


try:
    season_scores()
except Exception as e:  # le simulateur ne doit jamais bloquer la mise à jour du site
    print(f"  simulateur non mis à jour : {e}", file=sys.stderr)
