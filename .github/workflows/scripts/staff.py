"""Aide à la décision pour le staff, postée sur Discord (salon staff).

Lancé par .github/workflows/site.yml juste après clan.py. Ne fait rien si le secret
DISCORD_STAFF_WEBHOOK n'existe pas.

1. Bilan de guerre : dès qu'une guerre (classique ou de Ligue de clans) est terminée,
   un message avec le résultat, les meilleurs attaquants, les attaques oubliées ou ratées
   et une suggestion pour la prochaine guerre.
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
PAGES = os.environ.get("PAGES_URL", "https://gravaen.github.io/coc/")
HOOK = os.environ.get("DISCORD_STAFF_WEBHOOK", "").strip()
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


def post(msg):
    req = urllib.request.Request(HOOK, data=json.dumps(msg).encode(), method="POST",
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
            s = seen.setdefault(m["tag"], {"since": NOW.isoformat(timespec="seconds"), "h": []})
            if "fp" in s and s["fp"] != fp:
                s["last"] = NOW.isoformat(timespec="seconds")
                if hour not in s["h"]:
                    s["h"].append(hour)
            s["fp"] = fp
            s["h"] = [h for h in s["h"] if h >= limit]
            s.update(n=m.get("name"), r=m.get("role"), c=label, th=m.get("townHallLevel"))
            members[m["tag"]] = s
    state["seen"] = members  # les partis sortent du suivi
    state.setdefault("tracking", NOW.isoformat(timespec="seconds"))


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


def activity_report(state, test=False):
    since = datetime.datetime.fromisoformat(state["tracking"])
    days = max(1, min(7, round((NOW - since).total_seconds() / 86400)))
    tip = {"member": "exclure ?", "admin": "rétrograder en Membre ?", "coLeader": "à contacter", "leader": "—"}
    order = ["leader", "coLeader", "admin", "member"]
    fields, total_zero = [], 0
    for label, _ in CLANS:
        rs = []
        for s in state["seen"].values():
            if s.get("c") != label:
                continue
            sc, d, h = activity(s, days)
            rs.append({**s, "s": sc, "d": d, "hh": h})
        if not rs:
            continue
        avg = round(sum(r["s"] for r in rs) / len(rs))
        zero = sorted([r for r in rs if r["s"] == 0], key=lambda r: order.index(r["r"]) if r["r"] in order else 9)
        low = sorted([r for r in rs if 0 < r["s"] < 40], key=lambda r: r["s"])
        top = sorted([r for r in rs if r["s"] >= 40], key=lambda r: (-r["s"], -r["hh"]))[:5]
        total_zero += len(zero)
        fields.append({"name": f"━━ {label} · activité moyenne {avg}/100 ━━",
                       "value": f"{len(rs)} membres · {len(zero)} inactif(s) · {len(low)} peu actif(s)"})
        fields.append({"name": f"😴 Inactifs (aucune activité en {days} j)",
                       "value": cut([f"• **{r['n']}** ({ROLE.get(r['r'], '?')}, HDV {r['th']}) · {ago(r.get('last'))} → {tip.get(r['r'], '?')}" for r in zero], "Personne 👏")})
        fields.append({"name": "🟠 Peu actifs (moins de 40/100)",
                       "value": cut([f"• **{r['n']}** — **{r['s']}**/100 · actif {r['d']}/{days} j · {ago(r.get('last'))}" for r in low], "Personne")})
        fields.append({"name": "🔥 Les plus actifs",
                       "value": cut([f"{i + 1}. **{r['n']}** — **{r['s']}**/100 · actif {r['d']}/{days} j · {r['hh']} h" for i, r in enumerate(top)], "Personne")})
    note = (f"⚠️ Test : suivi commencé le <t:{int(since.timestamp())}:f>, les scores se précisent avec le temps.\n" if test else "")
    return {
        "username": "Gravaen · staff",
        "embeds": [{
            "author": {"name": ("🧪 TEST · " if test else "") + "Rapport d'activité de la semaine"},
            "title": f"😴 {total_zero} membre(s) sans aucune activité depuis {days} jour(s)",
            "color": 0xC8412F if total_zero else 0x2F8F55,
            "description": (note + f"**Score d'activité sur 100**, sur les {days} derniers jours : relevé toutes les 15 min, "
                            "le joueur est compté actif dès qu'un de ses compteurs bouge (dons, pillage, attaques, capitale, améliorations…).\n"
                            "70 pts = nombre de jours joués · 30 pts = nombre d'heures actives."),
            "fields": fields[:25],
            "footer": {"text": "Rapport automatique du lundi · Gravaen"},
        }],
    }


# ---------------------------------------------------------------------------
# 3. Meilleurs joueurs de la saison : publié une fois, au changement de saison
#    (classement de data/players.json, le même que le simulateur et la page classement)
# ---------------------------------------------------------------------------
CATS = {"cwl": "Ligue de clans", "gdc": "Guerre", "cap": "Capitale", "rk": "Classé", "act": "Activité", "don": "Dons"}
BADGE = (("gdc", "⚔️ Chef de guerre"), ("cwl", "🛡️ Maître de la Ligue"), ("cap", "🏰 Bâtisseur de Capitale"),
         ("rk", "🏆 Compétiteur"), ("act", "🔥 Infatigable"), ("don", "🤝 Cœur du clan"))
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]


def season_end(start):
    """La saison suivante commence le dernier lundi du mois suivant, à 5 h UTC."""
    y, m = (start.year + (start.month == 12), start.month % 12 + 1)
    nxt = datetime.datetime(y + (m == 12), m % 12 + 1, 1, 5, tzinfo=datetime.timezone.utc) - datetime.timedelta(days=1)
    while nxt.weekday() != 0:
        nxt -= datetime.timedelta(days=1)
    return nxt.replace(hour=5)


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

    if not HOOK:
        print("DISCORD_STAFF_WEBHOOK absent : rien n'est posté.")
    else:
        for wid, msg in wars_done(state):
            try:
                post(msg)
                state["wars"].append(wid)
                print("bilan posté :", wid)
            except Exception as e:
                print(f"  bilan {wid} non posté : {e}", file=sys.stderr)
    state["wars"] = state["wars"][-60:]

    track(state)

    # rapport du lundi soir (à partir de 18 h, heure de Paris), une fois par semaine, après 6 jours de suivi
    weekly = state.get("weekly")
    due = NOW.weekday() == 0 and NOW.hour >= 17 and (not weekly or NOW - datetime.datetime.fromisoformat(weekly) > datetime.timedelta(days=6))
    if HOOK and due:
        if NOW - datetime.datetime.fromisoformat(state["tracking"]) >= datetime.timedelta(days=6):
            try:
                post(activity_report(state))
                state["weekly"] = NOW.isoformat(timespec="seconds")
                print("rapport d'activité posté")
            except Exception as e:
                print(f"  rapport d'activité non posté : {e}", file=sys.stderr)
        else:
            print("rapport d'activité : suivi trop récent")

    # rapport de test, lancé à la main depuis l'onglet Actions
    if HOOK and os.environ.get("STAFF_TEST") == "true":
        try:
            post(activity_report(state, test=True))
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
    if HOOK and old_pj.get("season") and new_pj.get("season") and old_pj["season"] != new_pj["season"] and old_pj["season"] not in done:
        try:
            post(season_report(old_pj))
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
    if HOOK and os.environ.get("STAFF_TEST_SAISON") == "true" and new_pj.get("players"):
        try:
            post(season_report(new_pj, test=True))
            print("classement de test posté")
        except Exception as e:
            print(f"  classement de test non posté : {e}", file=sys.stderr)

    os.makedirs("data", exist_ok=True)
    with open("data/staff.json", "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, separators=(",", ":"))


if __name__ == "__main__":
    main()
