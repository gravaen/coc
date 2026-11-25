"""Aide à la décision pour le staff, postée sur Discord (salon staff).

Lancé par .github/workflows/site.yml juste après clan.py. Ne fait rien si le secret
DISCORD_STAFF_WEBHOOK n'existe pas.

1. Bilan de guerre : dès qu'une guerre (classique ou de Ligue de clans) est terminée,
   un message avec le résultat, les meilleurs attaquants, les attaques oubliées ou ratées
   et une suggestion pour la prochaine guerre.
   Rappel à 6 h de la fin de chaque guerre (#général) : qui n'a pas encore attaqué.
   Nouvel arrivant (salon staff) : analyse façon candidature express + action conseillée ; rien si le joueur est déjà connu.
2. Activité (façon ClashPerk) : à chaque passage, les compteurs de chaque membre sont relus ;
   dès que l'un bouge, le joueur était en ligne. Chaque lundi soir : « vu il y a… »,
   score d'activité sur 7 jours, inactifs et peu actifs en premier, suggestion selon le grade.

Mémoire d'un passage à l'autre : data/staff.json (publié avec le site, relu au passage suivant).
"""
import datetime
import json
import os
import sys
import urllib.parse
import urllib.request

CLANS = (("Clan principal", "#2C0CVRCPV"), ("Clan secondaire", "#2J0UPJVQJ"))
API = os.environ.get("COC_API_BASE", "https://cocproxy.royaleapi.dev/v1")
PAGES = os.environ.get("PAGES_URL", "https://gravaen.pages.dev/")
HOOK = os.environ.get("DISCORD_STAFF_WEBHOOK", "").strip()
# salon général : bilans de guerre et meilleurs joueurs (à défaut, salon staff)
GEN = os.environ.get("DISCORD_GENERAL_WEBHOOK", "").strip() or HOOK
NOW = datetime.datetime.now(datetime.timezone.utc)
ROLE = {"member": "Membre", "admin": "Aîné", "coLeader": "Adjoint", "leader": "Chef"}


def api(path):
    req = urllib.request.Request(API + path, headers={"Authorization": "Bearer " + os.environ["COC_TOKEN"], "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def api_or_none(path):
    try:
        return api(path)
    except Exception as e:
        print(f"  {path} : {e}", file=sys.stderr)
        return None


def q(tag):
    return urllib.parse.quote(tag)


def ts(t):
    """20261112T180000.000Z -> datetime"""
    return datetime.datetime.strptime(t[:15], "%Y%m%dT%H%M%S").replace(tzinfo=datetime.timezone.utc)


def post(msg, hook=None):
    req = urllib.request.Request(hook or HOOK, data=json.dumps(msg).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "User-Agent": "DiscordBot (gravaen, 1)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        r.read()


def cut(lines, empty="Aucun"):
    """Liste en texte, sans dépasser la limite d'un champ Discord."""
    out, n = [], 0
    for i, line in enumerate(lines):
        if n + len(line) + 1 > 980:
            out.append(f"… et {len(lines) - i} autres")
            break
        out.append(line)
        n += len(line) + 1
    return "\n".join(out) or empty


def load_state():
    try:
        with urllib.request.urlopen(PAGES + "data/staff.json?ts=" + str(int(NOW.timestamp())), timeout=20) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print(f"  staff.json précédent introuvable : {e}", file=sys.stderr)
        return {}


# ---------------------------------------------------------------------------
# 1. Bilan de guerre
# ---------------------------------------------------------------------------
def war_report(war, our_tag, clan_label, kind):
    us, them = war["clan"], war["opponent"]
    if us.get("tag") != our_tag:
        us, them = them, us
    per = war.get("attacksPerMember") or 1
    foe_th = {m["tag"]: m.get("townhallLevel", 0) for m in them.get("members") or []}
    s1, s2 = us.get("stars", 0), them.get("stars", 0)
    d1, d2 = us.get("destructionPercentage", 0), them.get("destructionPercentage", 0)
    if (s1, d1) > (s2, d2):
        title, color = "✅ Victoire", 0x2F8F55
    elif (s1, d1) < (s2, d2):
        title, color = "❌ Défaite", 0xC8412F
    else:
        title, color = "🤝 Égalité", 0xE08A1E

    rows = []
    for m in us.get("members") or []:
        atks = m.get("attacks") or []
        stars = sum(a.get("stars", 0) for a in atks)
        dest = sum(a.get("destructionPercentage", 0) for a in atks)
        bad = [a for a in atks if a.get("stars", 0) <= 1 and foe_th.get(a.get("defenderTag"), 99) <= m.get("townhallLevel", 0)]
        rows.append({"n": m.get("name"), "th": m.get("townhallLevel"), "stars": stars, "dest": dest,
                     "used": len(atks), "missed": per - len(atks), "bad": len(bad),
                     "triple": sum(1 for a in atks if a.get("stars") == 3)})

    top = sorted([r for r in rows if r["used"]], key=lambda r: (-r["stars"], -r["dest"]))[:5]
    missed = sorted([r for r in rows if r["missed"] > 0], key=lambda r: -r["missed"])
    bad = sorted([r for r in rows if r["bad"] > 0], key=lambda r: -r["bad"])
    used = sum(r["used"] for r in rows)

    tips = []
    for r in missed:
        if r["used"] == 0:
            tips.append(f"• **{r['n']}** : aucune attaque jouée, à sortir de la prochaine guerre")
        else:
            tips.append(f"• **{r['n']}** : {r['missed']} attaque(s) oubliée(s), à relancer")
    for r in bad:
        if r["bad"] >= 2 or (per == 1 and r["bad"] >= 1):
            tips.append(f"• **{r['n']}** : {r['bad']} attaque(s) ratée(s) sur plus faible ou égal, à accompagner")
    if not tips:
        tips.append("• Rien à signaler, tout le monde a joué. Bravo à l'équipe !")

    end = ts(war["endTime"])
    score_line = (f"**{us.get('name')}** {s1} ⭐ · {d1:.1f} %   —   {s2} ⭐ · {d2:.1f} % **{them.get('name')}**").replace(".", ",")
    return {
        "username": "Gravaen · staff",
        "embeds": [{
            "author": {"name": f"Bilan · {kind} · {clan_label}"},
            "title": f"{title} contre {them.get('name', '?')}",
            "color": color,
            "description": (score_line + "\n"
                            f"{war.get('teamSize')} contre {war.get('teamSize')} · {used}/{len(rows) * per} attaques jouées · fin <t:{int(end.timestamp())}:f>"),
            "fields": [
                {"name": "🏅 Meilleurs attaquants", "value": cut([f"{r['n']} — **{r['stars']}** ⭐ ({r['triple']}× 3 ⭐, HDV {r['th']})" for r in top])},
                {"name": "⏰ Attaques oubliées", "value": cut([f"{r['n']} — {r['missed']}" for r in missed]), "inline": True},
                {"name": "🥶 Attaques ratées (0–1 ⭐ sur plus faible ou égal)", "value": cut([f"{r['n']} — {r['bad']}" for r in bad]), "inline": True},
                {"name": "💡 Suggestion pour la prochaine guerre", "value": cut(tips)},
            ],
            "footer": {"text": "Bilan automatique · Gravaen"},
        }],
    }


def wars_done(state):
    """Guerres terminées depuis moins de 48 h, pas encore annoncées."""
    seen = set(state.get("wars", []))
    found = []
    for label, tag in CLANS:
        cw = api_or_none(f"/clans/{q(tag)}/currentwar")
        if cw and cw.get("state") == "warEnded" and cw.get("endTime"):
            found.append((tag + cw["startTime"], cw, tag, label, "Guerre"))
        lg = api_or_none(f"/clans/{q(tag)}/currentwar/leaguegroup")
        if lg and lg.get("state") in ("inWar", "ended"):
            for i, rnd in enumerate(lg.get("rounds") or []):
                for wt in rnd.get("warTags") or []:
                    if wt == "#0":
                        continue
                    w = api_or_none(f"/clanwarleagues/wars/{q(wt)}")
                    if not w or tag not in ((w.get("clan") or {}).get("tag"), (w.get("opponent") or {}).get("tag")):
                        continue
                    if w.get("state") == "warEnded" and w.get("endTime"):
                        found.append((wt, w, tag, label, f"Ligue de clans · manche {i + 1}"))
    out = []
    for wid, w, tag, label, kind in found:
        if wid in seen or NOW - ts(w["endTime"]) > datetime.timedelta(hours=48):
            continue
        out.append((wid, war_report(w, tag, label, kind)))
    return out


# ---------------------------------------------------------------------------
# 1 bis. Rappel de fin de guerre (#général) : à 6 h de la fin, qui n'a pas encore attaqué
# ---------------------------------------------------------------------------
NOM = {"#2C0CVRCPV": "Gravaen 1", "#2J0UPJVQJ": "Gravaen 2"}


def late_list(war, our_tag):
    side = war["clan"] if (war.get("clan") or {}).get("tag") == our_tag else war.get("opponent") or {}
    per = war.get("attacksPerMember") or 1
    out = []
    for m in sorted(side.get("members") or [], key=lambda m: m.get("mapPosition", 99)):
        done = len(m.get("attacks") or [])
        if done < per:
            out.append(m.get("name", "?") + (f" ({done}/{per})" if done else ""))
    return out


def end_reminders(state):
    """Guerres en cours (classique ou ligue) qui finissent dans moins de 6 h, rappel pas encore envoyé."""
    sent = set(state.get("reminders", []))
    found = []
    for label, tag in CLANS:
        cw = api_or_none(f"/clans/{q(tag)}/currentwar")
        if cw and cw.get("state") == "inWar":
            found.append((tag + cw["startTime"], cw, tag))
        lg = api_or_none(f"/clans/{q(tag)}/currentwar/leaguegroup")
        if lg and lg.get("state") == "inWar":
            for rnd in lg.get("rounds") or []:
                for wt in rnd.get("warTags") or []:
                    if wt == "#0":
                        continue
                    w = api_or_none(f"/clanwarleagues/wars/{q(wt)}")
                    if w and w.get("state") == "inWar" and tag in ((w.get("clan") or {}).get("tag"), (w.get("opponent") or {}).get("tag")):
                        found.append((wt, w, tag))
    out = []
    for wid, w, tag in found:
        left = ts(w["endTime"]) - NOW
        if wid in sent or not (datetime.timedelta(0) < left <= datetime.timedelta(hours=6)):
            continue
        late = late_list(w, tag)
        if not late:
            out.append((wid, None))   # tout le monde a attaqué : rien à poster
            continue
        h = max(1, round(left.total_seconds() / 3600))
        out.append((wid, {
            "username": "Gravaen",
            "embeds": [{
                "description": f"⏰ **{NOM.get(tag, tag)} · fin de guerre dans {h} h**\nPas encore attaqué : " + ", ".join(late),
                "color": 0xF8C801,
            }],
        }))
    return out


# ---------------------------------------------------------------------------
# 1 ter. Nouvel arrivant (#staff) : même analyse que la candidature express, avec l'action conseillée
# ---------------------------------------------------------------------------
HEROES = ("Barbarian King", "Archer Queen", "Minion Prince", "Grand Warden", "Royal Champion", "Dragon Duke")
HERO_FR = ("Roi", "Reine", "Prince", "Gardien", "Championne", "Duc")
CAPS = {7: (10, 0, 0, 0, 0, 0), 8: (20, 10, 0, 0, 0, 0), 9: (30, 30, 10, 0, 0, 0), 10: (40, 40, 20, 0, 0, 0),
        11: (50, 50, 30, 20, 0, 0), 12: (65, 65, 40, 40, 0, 0), 13: (75, 75, 50, 50, 25, 0), 14: (85, 85, 60, 60, 30, 0),
        15: (90, 90, 70, 65, 40, 10), 16: (95, 95, 80, 70, 45, 15), 17: (100, 100, 90, 75, 50, 20), 18: (110, 110, 95, 85, 55, 25)}
TIERS = ("Skeleton", "Barbarian", "Archer", "Wizard", "Valkyrie", "Witch", "Golem", "P.E.K.K.A", "Titan", "Dragon", "Electro", "Legend")
DIM = (("hdv", "Hôtel de ville", 15, "🏰"), ("her", "Héros", 25, "👑"), ("cla", "Classé", 15, "🏆"),
       ("gue", "Guerre", 20, "⚔️"), ("cap", "Capitale", 10, "🏛️"), ("don", "Dons", 15, "🤝"))


def analyse(p):
    """Même calcul que le Worker de la candidature express : score /100, rush, recommandation."""
    clamp = lambda x: max(0.0, min(1.0, x))
    th = p.get("townHallLevel") or 1
    caps = CAPS[min(18, max(7, th))]
    prev = CAPS.get(min(18, th - 1))
    lv = [next((h.get("level", 0) for h in p.get("heroes") or [] if h.get("name") == n and h.get("village") == "home"), 0) for n in HEROES]
    prog = sum(min(l, c) for l, c in zip(lv, caps)) / sum(caps) if sum(caps) else 0
    rush = 1 - sum(min(l, c) for l, c in zip(lv, prev)) / sum(prev) if prev and sum(prev) else 0
    tier = ((p.get("leagueTier") or {}).get("name")) or ((p.get("league") or {}).get("name")) or ""
    t0 = tier.replace(".", "")
    ti = next((i for i, t in enumerate(TIERS) if t0.startswith(t.replace(".", ""))), -1)
    cla = ti / (len(TIERS) - 1) if ti >= 0 else clamp((p.get("trophies") or 0) / 6000)
    ach = {a["name"]: a.get("value", 0) for a in p.get("achievements") or []}
    sc = {"hdv": clamp((th - 6) / 12), "her": prog, "cla": cla, "gue": clamp((p.get("warStars") or 0) / 2000),
          "cap": clamp((p.get("clanCapitalContributions") or 0) / 3000000), "don": clamp(ach.get("Friend in Need", 0) / 50000)}
    dims = [(k, lab, mx, ic, round(sc[k] * mx, 1)) for k, lab, mx, ic in DIM]
    raw = round(sum(d[4] for d in dims), 1)
    malus = round(min(rush, 0.5) * 60) if rush > 0.05 else 0
    total = max(0, round(raw - malus, 1))
    rushed, too = rush > 0.1, rush > 0.25
    if th < 7:
        reco = "HDV trop bas"
    elif too:
        reco = "Non recommandé : compte trop rushé"
    elif th >= 16 and total >= 60 and not rushed:
        reco = "Clan principal"
    else:
        reco = "Clan secondaire"
    return {"th": th, "total": total, "raw": raw, "malus": malus, "rush": round(rush * 100), "rushed": rushed, "too": too,
            "reco": reco, "tier": tier or "Non classé", "dims": dims, "lv": lv, "caps": caps}


def action(a, tag):
    """Action conseillée pour le staff selon le clan rejoint (même logique que la candidature express)."""
    r = a["reco"]
    if r == "HDV trop bas":
        return "🚫 **Exclure** : HDV trop bas", 0xC8412F
    if r.startswith("Non recommandé"):
        return "🚫 **Exclure** : compte trop rushé", 0xC8412F
    if tag == CLANS[0][1]:
        return ("✅ **Garder** : profil au niveau du principal", 0x2F8F55) if r == "Clan principal" else \
               ("↘️ **Déplacer vers Gravaen 2** : pas encore le niveau du principal", 0xE08A1E)
    return ("↗️ **Proposer pour Gravaen 1** : profil au niveau du principal", 0x2F8F55) if r == "Clan principal" else \
           ("✅ **Garder** : bien placé dans Gravaen 2", 0x2F8F55)


def join_message(tag, clan_tag, p):
    a = analyse(p)
    act, color = action(a, clan_tag)
    bar = lambda v: ("🟩" if v >= 70 else "🟨" if v >= 40 else "🟥") * round(v / 10) + "⬛" * (10 - round(v / 10))
    heroes = " · ".join(f"{HERO_FR[i]} **{a['lv'][i]}**/{a['caps'][i]}" for i in range(6) if a["caps"][i] > 0) or "—"
    rush = (f"🔴 Trop rushé : héros à **{a['rush']} %** sous le max de l'HDV {a['th'] - 1}" if a["too"]
            else f"🟠 Rushé : héros à **{a['rush']} %** sous le max de l'HDV {a['th'] - 1}" if a["rushed"]
            else f"🟢 Non rushé ({a['rush']} %)")
    link = "https://link.clashofclans.com/fr?action=OpenPlayerProfile&tag=" + urllib.parse.quote(tag.replace("#", ""))
    ico = (p.get("leagueTier") or {}).get("iconUrls") or {}
    icon = ico.get("small") or ico.get("large")
    return {
        "username": "Gravaen · arrivées",
        "embeds": [{
            "author": {"name": f"Nouvel arrivant · {NOM.get(clan_tag, clan_tag)}",
                       **({"icon_url": icon} if icon else {})},
            "thumbnail": {"url": "https://raw.githubusercontent.com/ClashKingInc/ClashKingAssets/main/assets/buildings/home-village/town_hall/level_"
                                 + str(min(18, max(1, a["th"]))) + ".webp"},
            "title": f"{p.get('name', '?')} a rejoint {NOM.get(clan_tag, clan_tag)}",
            "url": link,
            "color": color,
            "description": f"## {a['total']} / 100\n{act}" + (f"\n-# Score brut {a['raw']} · malus rush -{a['malus']}" if a["malus"] else ""),
            "fields": [
                {"name": "🏷️ Tag", "value": f"`{tag}`", "inline": True},
                {"name": "🏰 HDV", "value": f"**{a['th']}**", "inline": True},
                {"name": "⭐ Niveau", "value": f"**{p.get('expLevel', '?')}**", "inline": True},
                {"name": "🏆 Ligue", "value": f"{a['tier']}\n{p.get('trophies', 0)} trophées", "inline": True},
                {"name": "⚔️ Étoiles de guerre", "value": f"**{p.get('warStars', 0)}**", "inline": True},
                {"name": "🛡️ Rôle", "value": ROLE.get(p.get("role"), "Membre"), "inline": True},
                {"name": "👑 Héros", "value": heroes},
                {"name": "📉 Rush", "value": rush},
                {"name": "📊 Scores sur 100", "value": "\n".join(
                    f"{ic} {bar(round(v / mx * 100))} **{round(v / mx * 100)}** {lab}" for k, lab, mx, ic, v in a["dims"])},
            ],
            "footer": {"text": "Arrivée détectée en jeu · premier passage dans nos clans"},
            "timestamp": NOW.isoformat(timespec="seconds"),
        }],
    }


# ---------------------------------------------------------------------------
# 2. Activité, façon ClashPerk : à chaque passage (toutes les 15 min), on relit les compteurs
#    de chaque membre ; dès qu'un compteur bouge, le joueur était en ligne.
#    On en tire « vu il y a… » et un score d'activité sur les 7 derniers jours.
# ---------------------------------------------------------------------------
# succès du jeu qui bougent quand le joueur joue (pillage, dons, obstacles, capitale, jeux de clan…)
ACHV = ("Gold Grab", "Elixir Escapade", "Heroic Heist", "Friend in Need", "Sharing is caring", "Siege Sharer",
        "Nice and Tidy", "Conqueror", "War Hero", "War League Legend", "Games Champion", "Aggressive Capitalism",
        "Most Valuable Clanmate", "Well Seasoned", "Un-Build It", "Superb Work", "Counterspell", "Monolith Masher",
        "Get those Goblins!", "Bust This!", "Humiliator")


def fingerprint(p):
    a = {x["name"]: x.get("value", 0) for x in p.get("achievements") or []}
    keys = [p.get(k, 0) for k in ("donations", "donationsReceived", "attackWins", "warStars", "clanCapitalContributions",
                                  "expLevel", "builderBaseTrophies", "townHallLevel")]
    keys += [a.get(n, 0) for n in ACHV]
    keys += [sum(h.get("level", 0) for h in p.get("heroes") or []), sum(t.get("level", 0) for t in p.get("troops") or []),
             sum(t.get("level", 0) for t in p.get("spells") or []), p.get("name")]
    return "|".join(map(str, keys))


def track(state):
    """Met à jour, pour chaque membre, son empreinte, sa dernière activité et ses heures d'activité."""
    seen = state.setdefault("seen", {})
    before = set(seen)          # membres connus au passage précédent
    newbies = []                # (tag, clan, profil) des membres absents au passage précédent
    hour = NOW.strftime("%Y-%m-%dT%H")
    limit = (NOW - datetime.timedelta(days=8)).strftime("%Y-%m-%dT%H")
    members = {}
    for label, tag in CLANS:
        c = api_or_none(f"/clans/{q(tag)}") or {}
        for m in c.get("memberList") or []:
            p = api_or_none(f"/players/{q(m['tag'])}")
            if not p:
                continue
            fp = fingerprint(p)
            if m["tag"] not in before:
                newbies.append((m["tag"], tag, p))
            s = seen.setdefault(m["tag"], {"since": NOW.isoformat(timespec="seconds"), "h": []})
            season = NOW.strftime("%Y-%m-01") if NOW.day > 1 or NOW.hour >= 5 else (NOW - datetime.timedelta(days=1)).strftime("%Y-%m-01")
            if s.get("ms") != season:  # nouvelle saison : on repart de zéro
                s["ms"], s["md"] = season, []
            if "fp" in s and s["fp"] != fp:
                s["last"] = NOW.isoformat(timespec="seconds")
                if hour not in s["h"]:
                    s["h"].append(hour)
                if NOW.strftime("%Y-%m-%d") not in s["md"]:
                    s["md"].append(NOW.strftime("%Y-%m-%d"))
            s["fp"] = fp
            s["h"] = [h for h in s["h"] if h >= limit]
            s.update(n=m.get("name"), r=m.get("role"), c=label, th=m.get("townHallLevel"), don=p.get("donations", 0))
            members[m["tag"]] = s
    state["seen"] = members  # les partis sortent du suivi
    state.setdefault("tracking", NOW.isoformat(timespec="seconds"))

    # Arrivées : seul un joueur jamais vu dans Gravaen 1 ni Gravaen 2 est signalé.
    # Un joueur déjà passé chez nous (parti puis revenu, ou changé de clan) a un profil connu : aucun message.
    # Au tout premier passage, on mémorise simplement tout le monde.
    ready = "known" in state
    known = set(state.get("known") or []) | before | set(members)
    joins = [(t, c, p) for t, c, p in newbies if ready and t not in set(state.get("known") or [])]
    state["known"] = sorted(known)[-3000:]
    return joins


def ago(iso):
    if not iso:
        return "pas vu depuis le début du suivi"
    d = NOW - datetime.datetime.fromisoformat(iso)
    if d < datetime.timedelta(hours=1):
        return "vu il y a moins d'1 h"
    if d < datetime.timedelta(days=1):
        return f"vu il y a {int(d.total_seconds() // 3600)} h"
    return f"vu il y a {d.days} j"


def activity(s, days):
    """Score sur 100 : jours où il a joué (70 pts) + nombre d'heures actives (30 pts), sur la période."""
    start = (NOW - datetime.timedelta(days=days)).strftime("%Y-%m-%dT%H")
    hrs = [h for h in s["h"] if h >= start]
    d = len({h[:10] for h in hrs})
    return round(70 * min(1, d / days) + 30 * min(1, len(hrs) / (3 * days))), d, len(hrs)


def best_of_season():
    """Meilleur joueur de la saison en cours, par clan (data/players.json, même classement que le site)."""
    try:
        with open("data/players.json", encoding="utf-8") as f:
            pl = (json.load(f).get("players") or {})
    except Exception:
        return {}
    best = {}
    for tag, x in pl.items():
        c = x.get("c")
        if c and (c not in best or (x.get("score") or 0) > (best[c][1] or 0)):
            best[c] = (tag, x.get("score") or 0)
    return {("Clan principal" if c == "main" else "Clan secondaire"): t for c, (t, _) in best.items()}


def activity_report(state, test=False):
    """Rapport du lundi, un message par clan (Clan 1 = principal, Clan 2 = secondaire), ultra court :
    qui exclure, rétrograder, promouvoir, selon nos règles.
    Exclusion = Membre inactif 4 jours, Aîné inactif 7 jours (le non-respect de la stratégie reste à l'appréciation du chef).
    Aîné = très actif et 3 guerres de clans · Adjoint = 3 mois dans le clan et meilleur joueur de la saison."""
    since = datetime.datetime.fromisoformat(state["tracking"])
    days = max(1, min(7, round((NOW - since).total_seconds() / 86400)))
    best = best_of_season()
    num = {"Clan principal": "Clan 1", "Clan secondaire": "Clan 2"}
    out = []
    for label, tag_clan in CLANS:
        rs = []
        for tag, s in state["seen"].items():
            if s.get("c") == label:
                sc, d, _h = activity(s, days)
                rs.append((tag, s, sc, d))
        if not rs:
            continue
        excl, demote, promo, adj = [], [], [], []
        for tag, s, sc, d in rs:
            n, r = s.get("n", "?"), s.get("r")
            who = f"**{n}**"
            ref = s.get("last") or s.get("since") or state["tracking"]
            idle = (NOW - datetime.datetime.fromisoformat(ref)).days
            idle_txt = f"inactif depuis {idle} j" if s.get("last") else f"aucune activité depuis {idle} j (début du suivi)"
            months = (NOW - datetime.datetime.fromisoformat(s.get("since", state["tracking"]))).days / 30.4
            if r == "member" and idle >= 4:
                excl.append(f"{who} Membre · {idle_txt}")
            elif r == "admin" and idle >= 7:
                excl.append(f"{who} Aîné · {idle_txt}")
            elif r == "coLeader" and idle >= 7:
                demote.append(f"{who} Adjoint → Aîné · {idle_txt}")
            elif r == "admin" and sc < 40:
                demote.append(f"{who} Aîné → Membre · actif {d}/{days} j seulement")
            elif r == "member" and sc >= 70:
                promo.append(f"{who} Membre → Aîné · actif {d}/{days} j · *vérifier 3 GDC*")
            if r == "admin" and best.get(label) == tag:
                anc = "3 mois ✓" if months >= 3 else ("ancienneté à vérifier" if (NOW - since).days < 92 else f"{months:.0f} mois ✗")
                adj.append(f"{who} Aîné → Adjoint · meilleur joueur de la saison · {anc}")
        total = len(excl) + len(demote) + len(promo) + len(adj)
        f = lambda xs: "\n".join("• " + x for x in xs[:15]) + (f"\n… et {len(xs) - 15} autre(s)" if len(xs) > 15 else "")
        fields = []
        if excl:
            fields.append({"name": f"🔴 Exclure · {len(excl)}", "value": f(excl)})
        if demote:
            fields.append({"name": f"🟠 Rétrograder · {len(demote)}", "value": f(demote)})
        if promo:
            fields.append({"name": f"🟢 Promouvoir Aîné · {len(promo)}", "value": f(promo)})
        if adj:
            fields.append({"name": f"⭐ Promouvoir Adjoint · {len(adj)}", "value": f(adj)})
        avg = round(sum(r[2] for r in rs) / len(rs))
        note = (f"🧪 Test · suivi depuis le <t:{int(since.timestamp())}:d>\n" if test else "")
        out.append({
            "username": "Gravaen · staff",
            "embeds": [{
                "author": {"name": ("🧪 TEST · " if test else "") + f"{num[label]} · {tag_clan} · recommandations de la semaine"},
                "title": (f"{total} décision(s) à prendre" if total else "✅ Rien à faire cette semaine"),
                "color": 0xC8412F if excl else (0xE08A1E if demote else 0x2F8F55),
                "description": note + f"{len(rs)} membres · activité moyenne {avg}/100 (sur {days} j)",
                "fields": fields,
                "footer": {"text": "Exclusion : 4 j d'inactivité (Membre), 7 j (Aîné) · Aîné = actif + 3 GDC · Adjoint = 3 mois + meilleur joueur"},
            }],
        })
    return out


# ---------------------------------------------------------------------------
# 3. Meilleurs joueurs de la saison : publié une fois, au changement de saison
#    (classement de data/players.json, le même que le simulateur et la page classement)
# ---------------------------------------------------------------------------
CATS = {"cwl": "Ligue de clans", "gdc": "Guerre", "cap": "Capitale", "rk": "Classé", "act": "Activité", "don": "Dons"}
BADGE = (("gdc", "⚔️ Chef de guerre"), ("cwl", "🛡️ Maître de la Ligue"), ("cap", "🏰 Bâtisseur de Capitale"),
         ("rk", "🏆 Compétiteur"), ("act", "🔥 Infatigable"), ("don", "🤝 Cœur du clan"))
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]


def season_end(start):
    """La saison suivante commence le 1er du mois suivant, à 5 h UTC."""
    return datetime.datetime(start.year + (start.month == 12), start.month % 12 + 1, 1, 5, tzinfo=datetime.timezone.utc)


def pts(x):
    return (f"{x:.1f}".rstrip("0").rstrip(".")).replace(".", ",")


def rang(r):
    return "1er" if r == 1 else f"{r}e"


def phrase(i, x, poly):
    rk = sorted([(r, k) for k, r in (x.get("r") or {}).items() if r], key=lambda t: t[0])
    PREP = {"cwl": "en Ligue de clans", "gdc": "en Guerre", "cap": "en Capitale", "rk": "aux trophées", "act": "en Activité", "don": "aux dons"}
    groups = {}
    for r, k in rk[:3]:
        groups.setdefault(r, []).append(PREP[k])
    bits = []
    for r, ks in groups.items():
        bits.append(rang(r) + " " + (", ".join(ks[:-1]) + " et " + ks[-1] if len(ks) > 1 else ks[0]))
    if poly:
        bits.append("classé dans les 6 catégories")
    if (x.get("hp") or 0) >= 0.97:
        bits.append(f"HDV {x.get('th')} aux héros au max")
    if not bits:
        return ""
    txt = ", ".join(bits)
    lead = "Saison monstrueuse : " if i == 0 else "Très grosse saison : " if i < 3 else "Saison solide : " if i < 6 else ""
    txt = lead + txt
    end = ". Il porte Gravaen au sommet." if i == 0 else "."
    return "> " + txt[0].upper() + txt[1:] + end


def season_report(pj, test=False):
    players = sorted((pj.get("players") or {}).values(), key=lambda x: -(x.get("score") or 0))
    players = [x for x in players if (x.get("score") or 0) > 0]
    start = datetime.datetime.strptime(pj["season"], "%Y-%m-%d").replace(hour=5, tzinfo=datetime.timezone.utc)
    end = season_end(start)
    name = MOIS[(end - datetime.timedelta(days=3)).month - 1].capitalize() + f" {(end - datetime.timedelta(days=3)).year}"
    heist = sorted([x for x in players if (x.get("dee") or 0) > 0], key=lambda x: -x["dee"])[:3]
    heist_names = {x["n"] for x in heist}
    lines = []
    medal = ["### 🥇 ", "### 🥈 ", "### 🥉 "]
    for i, x in enumerate(players[:10]):
        poly = sum(1 for v in (x.get("p") or {}).values() if v > 0) >= 6
        badges = (["👑 Champion de la saison"] if i == 0 else []) + [b for k, b in BADGE if (x.get("r") or {}).get(k) == 1]
        if poly:
            badges.append("🌟 Polyvalent")
        if (x.get("hp") or 0) >= 0.97:
            badges.append("💎 Compte accompli")
        if x["n"] in heist_names:
            badges.append("💰 Braqueur")
        head = (medal[i] if i < 3 else f"### {i + 1}. ") + f"{x['n']} — {pts(x['score'])} pts"
        lines.append("\n".join([head] + badges + ([phrase(i, x, poly)] if phrase(i, x, poly) else [])))
    top10 = {x["n"] for x in players[:10]}
    out = [x["n"] for x in heist if x["n"] not in top10]
    body = "\n\n".join(lines)
    if out:
        body += "\n\n-# 💰 Braqueur hors top 10 : " + ", ".join(out)
    ab = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]
    sub = f"-# Saison du {start.day} {ab[start.month - 1]} au {end.day} {ab[end.month - 1]} · {len(players)} joueurs classés · deux clans réunis"
    return {
        "username": "Gravaen · staff",
        "embeds": [{
            "title": ("🧪 TEST · " if test else "") + f"🏆 Meilleurs joueurs – {name}",
            "color": 0xF8C801,
            "description": (sub + ("\n-# ⚠️ Saison en cours : classement provisoire" if test else "") + "\n\n" + (body or "Aucun joueur classé cette saison."))[:4096],
            "footer": {"text": "Classement de la saison · Gravaen"},
        }],
    }


def main():
    state = load_state()
    state.setdefault("wars", [])
    state.pop("snaps", None)  # ancienne méthode (photo quotidienne), remplacée par le suivi continu

    if not GEN:
        print("Aucun webhook Discord : rien n'est posté.")
    else:
        for wid, msg in wars_done(state):
            try:
                post(msg, GEN)
                state["wars"].append(wid)
                print("bilan posté :", wid)
            except Exception as e:
                print(f"  bilan {wid} non posté : {e}", file=sys.stderr)
    state["wars"] = state["wars"][-60:]

    rem = state.setdefault("reminders", [])
    if GEN:
        for wid, msg in end_reminders(state):
            try:
                if msg:
                    post(msg, GEN)
                    print("rappel de fin de guerre posté :", wid)
                rem.append(wid)
            except Exception as e:
                print(f"  rappel {wid} non posté : {e}", file=sys.stderr)
    state["reminders"] = rem[-60:]

    joins = track(state)
    if HOOK:
        for t, c, p in joins:
            try:
                post(join_message(t, c, p))
                print("arrivée signalée :", t)
            except Exception as e:
                print(f"  arrivée {t} non signalée : {e}", file=sys.stderr)

    # rapport du lundi soir (à partir de 18 h, heure de Paris), une fois par semaine, après 6 jours de suivi
    weekly = state.get("weekly")
    due = NOW.weekday() == 0 and NOW.hour >= 17 and (not weekly or NOW - datetime.datetime.fromisoformat(weekly) > datetime.timedelta(days=6))
    if HOOK and due:
        if NOW - datetime.datetime.fromisoformat(state["tracking"]) >= datetime.timedelta(days=6):
            try:
                for _m in activity_report(state):
                    post(_m)
                state["weekly"] = NOW.isoformat(timespec="seconds")
                print("rapport d'activité posté")
            except Exception as e:
                print(f"  rapport d'activité non posté : {e}", file=sys.stderr)
        else:
            print("rapport d'activité : suivi trop récent")

    # rapport de test, lancé à la main depuis l'onglet Actions
    if HOOK and os.environ.get("STAFF_TEST") == "true":
        try:
            for _m in activity_report(state, test=True):
                post(_m)
            print("rapport de test posté")
        except Exception as e:
            print(f"  rapport de test non posté : {e}", file=sys.stderr)

    # meilleurs joueurs : la saison vient de changer (clan.py a déjà écrit la nouvelle) → on publie l'ancienne
    try:
        with urllib.request.urlopen(PAGES + "data/players.json?ts=" + str(int(NOW.timestamp())), timeout=20) as r:
            old_pj = json.loads(r.read().decode())
    except Exception:
        old_pj = {}
    try:
        with open("data/players.json", encoding="utf-8") as f:
            new_pj = json.load(f)
    except Exception:
        new_pj = {}
    done = state.setdefault("seasons", [])
    if GEN and old_pj.get("season") and new_pj.get("season") and old_pj["season"] != new_pj["season"] and old_pj["season"] not in done:
        try:
            post(season_report(old_pj), GEN)
            done.append(old_pj["season"])
            print("meilleurs joueurs de la saison postés :", old_pj["season"])
        except Exception as e:
            print(f"  meilleurs joueurs non postés : {e}", file=sys.stderr)
    if os.environ.get("STAFF_TEST_SAISON") == "true":  # diagnostic dans le journal
        from collections import Counter
        P = new_pj.get("players") or {}
        print("joueurs par clan :", dict(Counter(x.get("c") for x in P.values())))
        for x in sorted(P.values(), key=lambda x: -(x.get("score") or 0))[:15]:
            print("  ", x.get("c"), x.get("n"), x.get("score"), x.get("v"))
        for x in [x for x in P.values() if x.get("c") == "main"][:8]:
            print("  main", x.get("n"), x.get("score"), x.get("v"), x.get("p"))
    if GEN and os.environ.get("STAFF_TEST_SAISON") == "true" and new_pj.get("players"):
        try:
            post(season_report(new_pj, test=True), GEN)
            print("classement de test posté")
        except Exception as e:
            print(f"  classement de test non posté : {e}", file=sys.stderr)

    os.makedirs("data", exist_ok=True)
    with open("data/staff.json", "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, separators=(",", ":"))


if __name__ == "__main__":
    main()
