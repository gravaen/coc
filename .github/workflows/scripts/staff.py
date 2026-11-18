"""Aide à la décision pour le staff, postée sur Discord (salon staff).

Lancé par .github/workflows/site.yml juste après clan.py. Ne fait rien si le secret
DISCORD_STAFF_WEBHOOK n'existe pas.

1. Bilan de guerre : dès qu'une guerre (classique ou de Ligue de clans) est terminée,
   un message avec le résultat, les meilleurs attaquants, les attaques oubliées ou ratées
   et une suggestion pour la prochaine guerre.
2. Inactivité : chaque lundi soir, la liste des membres qui n'ont rien fait depuis 7 jours
   (aucun don, aucune victoire, aucune étoile de guerre, aucun or de capitale),
   avec une suggestion selon leur grade.

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
# 2. Inactivité
# ---------------------------------------------------------------------------
def snapshot():
    """Compteurs de chaque membre : dons, victoires, étoiles de guerre, or de capitale."""
    snap = {}
    for label, tag in CLANS:
        c = api_or_none(f"/clans/{q(tag)}") or {}
        for m in c.get("memberList") or []:
            p = api_or_none(f"/players/{q(m['tag'])}") or {}
            snap[m["tag"]] = {"n": m.get("name"), "r": m.get("role"), "c": label, "th": m.get("townHallLevel"),
                              "don": p.get("donations", m.get("donations", 0)), "win": p.get("attackWins", 0),
                              "ws": p.get("warStars", 0), "cap": p.get("clanCapitalContributions", 0)}
    return snap


# Score d'activité de la semaine, sur 100 : ce qui compte pour le clan, avec un plafond par critère
ACT = (("don", "Dons", 30, 350), ("win", "Victoires", 25, 14), ("ws", "Guerre", 30, 6), ("cap", "Capitale", 15, 25000))


def delta(o, n, k):
    """Progression sur la semaine ; dons et victoires repartent à zéro à chaque saison."""
    d = n.get(k, 0) - o.get(k, 0)
    return n.get(k, 0) if d < 0 else d


def act_score(o, n):
    return round(sum(w * min(1, delta(o, n, k) / cap) for k, _, w, cap in ACT))


def inactive_report(old, new, days):
    """Score d'activité de chacun, avec en premier les inactifs (rien fait) et les peu actifs."""
    tip = {"member": "exclure ?", "admin": "rétrograder en Membre ?", "coLeader": "à contacter", "leader": "—"}
    order = ["leader", "coLeader", "admin", "member"]
    rows = []
    for tag, n in new.items():
        o = old.get(tag)
        if not o:
            continue  # arrivé dans la semaine : pas encore de recul
        d = {k: delta(o, n, k) for k, *_ in ACT}
        rows.append({**n, "s": act_score(o, n), "d": d})

    def detail(r):
        return f"{r['d']['don']} dons · {r['d']['win']} vict. · {r['d']['ws']} ⭐ · {r['d']['cap'] // 1000}k or"

    fields, total_zero = [], 0
    for label, _ in CLANS:
        rs = [r for r in rows if r["c"] == label]
        if not rs:
            continue
        avg = round(sum(r["s"] for r in rs) / len(rs))
        zero = sorted([r for r in rs if r["s"] == 0], key=lambda r: order.index(r["r"]) if r["r"] in order else 9)
        low = sorted([r for r in rs if 0 < r["s"] < 30], key=lambda r: r["s"])
        top = sorted([r for r in rs if r["s"] > 0], key=lambda r: -r["s"])[:5]
        total_zero += len(zero)
        fields.append({"name": f"━━ {label} · activité moyenne {avg}/100 ━━", "value": f"{len(rs)} membres suivis · {len(zero)} inactif(s) · {len(low)} peu actif(s)"})
        fields.append({"name": "😴 Inactifs (0/100)",
                       "value": cut([f"• **{r['n']}** ({ROLE.get(r['r'], '?')}, HDV {r['th']}) → {tip.get(r['r'], '?')}" for r in zero], "Personne 👏")})
        fields.append({"name": "🟠 Peu actifs (moins de 30/100)",
                       "value": cut([f"• **{r['n']}** — **{r['s']}**/100 ({ROLE.get(r['r'], '?')}) · {detail(r)}" for r in low], "Personne")})
        fields.append({"name": "🔥 Les plus actifs",
                       "value": cut([f"{i + 1}. **{r['n']}** — **{r['s']}**/100 · {detail(r)}" for i, r in enumerate(top)], "Personne")})
    return {
        "username": "Gravaen · staff",
        "embeds": [{
            "author": {"name": "Rapport d'activité de la semaine"},
            "title": f"😴 {total_zero} membre(s) sans aucune activité depuis {days} jours",
            "color": 0xC8412F if total_zero else 0x2F8F55,
            "description": ("**Score d'activité sur 100**, calculé sur les 7 derniers jours :\n"
                            "dons 30 pts (350 troupes) · victoires 25 pts (14) · étoiles de guerre 30 pts (6) · or de capitale 15 pts (25 000)."),
            "fields": fields[:25],
            "footer": {"text": "Rapport automatique du lundi · Gravaen"},
        }],
    }


def main():
    state = load_state()
    state.setdefault("wars", [])
    state.setdefault("snaps", [])

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

    # une photo des compteurs par jour, gardée 10 jours
    last = state["snaps"][-1]["t"] if state["snaps"] else None
    if not last or NOW - datetime.datetime.fromisoformat(last) > datetime.timedelta(hours=20):
        state["snaps"].append({"t": NOW.isoformat(timespec="seconds"), "p": snapshot()})
        state["snaps"] = state["snaps"][-10:]

    # rapport du lundi soir (à partir de 18 h, heure de Paris), une fois par semaine
    weekly = state.get("weekly")
    due = NOW.weekday() == 0 and NOW.hour >= 17 and (not weekly or NOW - datetime.datetime.fromisoformat(weekly) > datetime.timedelta(days=6))
    if HOOK and due:
        olds = [s for s in state["snaps"] if datetime.timedelta(days=6, hours=12) <= NOW - datetime.datetime.fromisoformat(s["t"]) <= datetime.timedelta(days=9)]
        if olds:
            o = olds[0]
            days = round((NOW - datetime.datetime.fromisoformat(o["t"])).total_seconds() / 86400)
            try:
                post(inactive_report(o["p"], state["snaps"][-1]["p"], days))
                state["weekly"] = NOW.isoformat(timespec="seconds")
                print("rapport d'activité posté")
            except Exception as e:
                print(f"  rapport d'activité non posté : {e}", file=sys.stderr)
        else:
            print("rapport d'activité : pas encore 7 jours d'historique")

    os.makedirs("data", exist_ok=True)
    with open("data/staff.json", "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, separators=(",", ":"))


if __name__ == "__main__":
    main()
