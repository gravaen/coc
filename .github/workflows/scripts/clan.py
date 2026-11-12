"""Récupère les chiffres du clan Gravaen et les écrit dans data/clan.json.

Lancé chaque jour par .github/workflows/site.yml. La clé de l'API Clash of Clans
est lue dans la variable d'environnement COC_TOKEN (secret GitHub), jamais écrite ici.
"""
import datetime
import json
import os
import urllib.parse
import urllib.request

TAG = "#2C0CVRCPV"  # clan principal
URL = "https://cocproxy.royaleapi.dev/v1/clans/" + urllib.parse.quote(TAG)

req = urllib.request.Request(URL, headers={
    "Authorization": "Bearer " + os.environ["COC_TOKEN"],
    "Accept": "application/json",
})
with urllib.request.urlopen(req, timeout=30) as r:
    clan = json.load(r)

data = {
    "updated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    "clanLevel": clan.get("clanLevel"),
    "warLeague": (clan.get("warLeague") or {}).get("name"),
    "capitalLeague": (clan.get("capitalLeague") or {}).get("name"),
    "warWinStreak": clan.get("warWinStreak"),
    "warWins": clan.get("warWins"),
    # présent seulement si le journal de guerre du clan est public
    "warLosses": clan.get("warLosses"),
}

os.makedirs("data", exist_ok=True)
with open("data/clan.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=1)
print(json.dumps(data, ensure_ascii=False))
