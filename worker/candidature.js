// Gravaen · candidature express (Cloudflare Worker)
// Le site envoie { tag, send } en POST.
//   send=false : calcule et renvoie le résumé du joueur (rien n'est posté).
//   send=true  : poste aussi la candidature sur Discord (une seule fois par tag et par 24 h).
// GET /auth?tag=…  : envoie le joueur sur Discord pour confirmer son identité (« Envoyer avec Discord »).
// GET /callback    : retour de Discord ; poste la candidature avec la mention du joueur, puis l'envoie sur le serveur.
// Secrets à créer dans Cloudflare : COC_TOKEN (clé API Clash of Clans, IP 45.79.218.79), DISCORD_WEBHOOK (salon candidatures),
//   DISCORD_STAFF_WEBHOOK (salon staff, facultatif : la même fiche y est aussi postée),
//   DISCORD_FICHES_WEBHOOK (salon #fiches, facultatif : fiche diagnostic publique du joueur, sans la recommandation du staff),
//   DISCORD_CLIENT_ID et DISCORD_CLIENT_SECRET (application Discord), et DISCORD_INVITE (lien d'invitation du serveur).

const API = "https://cocproxy.royaleapi.dev/v1";

// Niveau max des héros par HDV (Hero Hall), sources : cocwarbase.com et 1337wiki, mises à jour TH18 (oct.-nov. 2026)
const HEROES = ["Barbarian King", "Archer Queen", "Minion Prince", "Grand Warden", "Royal Champion", "Dragon Duke"];
const FR = { "Barbarian King": "Roi", "Archer Queen": "Reine", "Minion Prince": "Prince", "Grand Warden": "Gardien", "Royal Champion": "Championne", "Dragon Duke": "Duc" };
const CAPS = {
  7: [10, 0, 0, 0, 0, 0], 8: [20, 10, 0, 0, 0, 0], 9: [30, 30, 10, 0, 0, 0], 10: [40, 40, 20, 0, 0, 0],
  11: [50, 50, 30, 20, 0, 0], 12: [65, 65, 40, 40, 0, 0], 13: [75, 75, 50, 50, 25, 0], 14: [85, 85, 60, 60, 30, 0],
  15: [90, 90, 70, 65, 40, 10], 16: [95, 95, 80, 70, 45, 15], 17: [100, 100, 90, 75, 50, 20], 18: [110, 110, 95, 85, 55, 25],
};
const TIERS = ["Skeleton", "Barbarian", "Archer", "Wizard", "Valkyrie", "Witch", "Golem", "P.E.K.K.A", "Titan", "Dragon", "Electro", "Legend"];

// Barème du score global (sur 100)
const DIM = [
  ["hdv", "Hôtel de ville", 15],
  ["her", "Héros", 25],
  ["cla", "Classé", 15],
  ["gue", "Guerre", 20],
  ["cap", "Capitale", 10],
  ["don", "Dons", 15],
];

const cors = (origin) => ({
  "Access-Control-Allow-Origin": origin || "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
  "Content-Type": "application/json; charset=utf-8",
});
const json = (o, status, origin) => new Response(JSON.stringify(o), { status, headers: cors(origin) });
const clamp = (x) => Math.max(0, Math.min(1, x));
const r1 = (x) => Math.round(x * 10) / 10;
const ach = (p, name) => ((p.achievements || []).find((a) => a.name === name) || {}).value || 0;

function analyse(p) {
  const th = p.townHallLevel || 1;
  const caps = CAPS[Math.min(18, Math.max(7, th))] || CAPS[7];
  const prev = CAPS[Math.min(18, th - 1)] || null;
  const lv = HEROES.map((n) => ((p.heroes || []).find((h) => h.name === n && h.village === "home") || {}).level || 0);

  // héros : progression à son HDV, et « rush » = retard par rapport au max de l'HDV précédent
  const sum = (a) => a.reduce((x, y) => x + y, 0);
  const prog = sum(caps) ? sum(lv.map((l, i) => Math.min(l, caps[i]))) / sum(caps) : 0;
  const rush = prev && sum(prev) ? 1 - sum(lv.map((l, i) => Math.min(l, prev[i]))) / sum(prev) : 0;

  // classé : palier de ligue, sinon trophées
  const tierName = (p.leagueTier && p.leagueTier.name) || (p.league && p.league.name) || "";
  const ti = TIERS.findIndex((t) => tierName.replace(/\./g, "").startsWith(t.replace(/\./g, "")));
  const cla = ti >= 0 ? ti / (TIERS.length - 1) : clamp((p.trophies || 0) / 6000);

  const s = {
    hdv: clamp((th - 6) / 12),
    her: prog,
    cla,
    gue: clamp((p.warStars || 0) / 2000),
    cap: clamp((p.clanCapitalContributions || 0) / 3000000),
    don: clamp(ach(p, "Friend in Need") / 50000),
  };
  const dims = DIM.map(([k, label, max]) => ({ k, label, max, v: r1(s[k] * max) }));
  const raw = r1(dims.reduce((x, d) => x + d.v, 0));
  // rush : héros en retard sur le max de l'HDV précédent. Malus jusqu'à -30 points.
  const malus = rush > 0.05 ? Math.round(Math.min(rush, 0.5) * 60) : 0;
  const total = Math.max(0, r1(raw - malus));
  const rushed = rush > 0.1;
  const tooRushed = rush > 0.25;

  let reco = "Clan secondaire";
  if (th < 7) reco = "HDV trop bas";
  else if (tooRushed) reco = "Non recommandé : compte trop rushé";
  else if (th >= 16 && total >= 60 && !rushed) reco = "Clan principal";

  return {
    tag: p.tag, name: p.name, th, exp: p.expLevel, trophies: p.trophies, league: tierName || "Non classé",
    leagueIcon: (p.leagueTier && p.leagueTier.iconUrls && (p.leagueTier.iconUrls.small || p.leagueTier.iconUrls.large)) || null,
    clan: p.clan ? p.clan.name : null, warStars: p.warStars || 0,
    heroes: HEROES.map((n, i) => ({ n: FR[n], l: lv[i], m: caps[i] })).filter((h) => h.m > 0),
    rush: Math.round(rush * 100), rushed, tooRushed, malus, raw, dims, total, reco,
  };
}

const TH_IMG = (th) => "https://raw.githubusercontent.com/ClashKingInc/ClashKingAssets/main/assets/buildings/home-village/town_hall/level_" + Math.min(18, Math.max(1, th)) + ".webp";
const bar = (pct) => {
  const n = Math.round(pct / 10), c = pct >= 70 ? "🟩" : pct >= 40 ? "🟨" : "🟥";
  return c.repeat(n) + "⬛".repeat(10 - n);
};
const ICO = { hdv: "🏰", her: "👑", cla: "🏆", gue: "⚔️", cap: "🏛️", don: "🤝" };

function embed(a) {
  const ok = a.reco === "Clan principal", mid = a.reco === "Clan secondaire";
  const color = ok ? 0x2f8f55 : mid ? 0xe08a1e : 0xc8412f;
  const recoTxt = (ok ? "🟢 " : mid ? "🟠 " : "🔴 ") + "**" + a.reco + "**";
  const link = "https://link.clashofclans.com/fr?action=OpenPlayerProfile&tag=" + encodeURIComponent(a.tag.replace("#", ""));
  const rushTxt = a.tooRushed ? "🔴 Trop rushé : héros à **" + a.rush + " %** sous le max de l'HDV " + (a.th - 1)
    : a.rushed ? "🟠 Rushé : héros à **" + a.rush + " %** sous le max de l'HDV " + (a.th - 1)
    : "🟢 Non rushé (" + a.rush + " %)";
  const e = {
    author: { name: "Candidature express · Gravaen", ...(a.leagueIcon ? { icon_url: a.leagueIcon } : {}) },
    title: a.name + " souhaite rejoindre votre clan",
    url: link,
    color,
    thumbnail: { url: TH_IMG(a.th) },
    description: "## " + a.total + " / 100\n" + recoTxt + (a.malus ? "\n-# Score brut " + a.raw + " · malus rush -" + a.malus : ""),
    fields: [
      { name: "🏷️ Tag", value: "`" + a.tag + "`", inline: true },
      { name: "🏰 HDV", value: "**" + a.th + "**", inline: true },
      { name: "⭐ Niveau", value: "**" + a.exp + "**", inline: true },
      { name: "🏆 Ligue", value: a.league + "\n" + a.trophies + " trophées", inline: true },
      { name: "⚔️ Étoiles de guerre", value: "**" + a.warStars + "**", inline: true },
      { name: "🛡️ Clan actuel", value: a.clan || "Aucun", inline: true },
      { name: "👑 Héros", value: a.heroes.map((h) => h.n + " **" + h.l + "**/" + h.m).join(" · ") || "—" },
      { name: "📉 Rush", value: rushTxt },
      { name: "📊 Scores sur 100", value: a.dims.map((d) => { const v = Math.round(d.v / d.max * 100); return ICO[d.k] + " " + bar(v) + " **" + v + "** " + d.label; }).join("\n") },
    ],
    timestamp: new Date().toISOString(),
  };
  return { username: "Gravaen · candidatures", embeds: [e] };
}

// Fiche diagnostic publique (salon #fiches) : score, jauges et priorités, sans la recommandation du staff
const TIPS = {
  hdv: "Monter ton hôtel de ville", her: "Monter tes héros au max de ton HDV", cla: "Grimper en classé (ligue)",
  gue: "Gagner des étoiles en guerre", cap: "Participer à la capitale (raids et contributions)", don: "Donner plus de troupes au clan",
};
// objectif presque atteint : « Il te manque 8 points pour Gravaen 1 » (même règle que le site)
function goalTxt(a) {
  if (a.reco !== "Clan secondaire" || a.tooRushed) return "";
  if (a.rushed) return "\n🎯 Rattrape tes héros pour viser **Gravaen 1**";
  if (a.th < 16) return "\n🎯 Monte ton HDV pour viser **Gravaen 1**";
  const m = Math.ceil(60 - a.total);
  return m > 0 ? "\n🎯 Il te manque **" + m + " point" + (m > 1 ? "s" : "") + "** pour Gravaen 1" : "";
}
function fiche(a, user) {
  const pct = (d) => Math.round(d.v / d.max * 100);
  const low = a.dims.slice().sort((x, y) => pct(x) - pct(y)).slice(0, 2);
  const prio = (a.rushed ? ["Rattraper tes héros avant de monter d'HDV"] : []).concat(low.map((d) => TIPS[d.k] + " (" + pct(d) + "/100)"));
  const e = {
    author: { name: "Fiche diagnostic · Gravaen", ...(a.leagueIcon ? { icon_url: a.leagueIcon } : {}) },
    title: "Fiche diagnostic de " + a.name,
    color: 0xf8c801,
    thumbnail: { url: TH_IMG(a.th) },
    description: "## " + a.total + " / 100" + goalTxt(a),
    fields: [
      { name: "🏰 HDV", value: "**" + a.th + "**", inline: true },
      { name: "🏆 Ligue", value: a.league, inline: true },
      { name: "⚔️ Étoiles de guerre", value: "**" + a.warStars + "**", inline: true },
      { name: "👑 Héros", value: a.heroes.map((h) => h.n + " **" + h.l + "**/" + h.m).join(" · ") || "—" },
      { name: "📊 Tes jauges", value: a.dims.map((d) => ICO[d.k] + " " + bar(pct(d)) + " **" + pct(d) + "** " + d.label).join("\n") },
      { name: "🎯 À travailler en priorité", value: prio.map((t, i) => (i + 1) + ". " + t).join("\n") },
    ],
    timestamp: new Date().toISOString(),
  };
  const msg = { username: "Gravaen · fiches", embeds: [e] };
  if (user) {
    msg.content = "<@" + user.id + ">, voici ta fiche diagnostic 👇";
    msg.allowed_mentions = { users: [user.id] };
  }
  return msg;
}

// « ⚔️ Prochaine guerre de Gravaen 1 dans 6 h : on t'attend ! » (clan conseillé, rien si le profil n'est pas recommandé)
async function warLine(a, env) {
  if (a.reco !== "Clan principal" && a.reco !== "Clan secondaire") return "";
  const main = a.reco === "Clan principal", name = main ? "Gravaen 1" : "Gravaen 2";
  try {
    const r = await fetch(API + "/clans/" + encodeURIComponent(main ? "#2C0CVRCPV" : "#2J0UPJVQJ") + "/currentwar", { headers: { Authorization: "Bearer " + env.COC_TOKEN } });
    if (!r.ok) return "";
    const w = await r.json();
    const t = (s) => new Date(s.replace(/^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2}).*$/, "$1-$2-$3T$4:$5:$6Z"));
    if (w.state === "preparation") return "⚔️ Prochaine guerre de " + name + " dans " + Math.max(1, Math.round((t(w.startTime) - Date.now()) / 36e5)) + " h : on t'attend !";
    if (w.state === "inWar") return "⚔️ Une guerre est en cours dans " + name + " : tu joueras la prochaine avec nous !";
  } catch (e) {}
  return "";
}

const cleanTag = (t) => "#" + String(t || "").toUpperCase().replace(/[^0-9A-Z]/g, "").replace(/O/g, "0");
const okTag = (t) => t.length >= 4 && t.length <= 13;
const redirect = (url) => Response.redirect(url, 302);
const page = (msg) => new Response('<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Gravaen</title><body style="font:18px system-ui;background:#212320;color:#FFFDF5;display:grid;place-items:center;min-height:90vh;text-align:center;padding:20px"><p>' + msg + '</p>', { status: 400, headers: { "Content-Type": "text/html; charset=utf-8" } });

async function player(tag, env) {
  const r = await fetch(API + "/players/" + encodeURIComponent(tag), { headers: { Authorization: "Bearer " + env.COC_TOKEN } });
  if (r.status === 404) throw Object.assign(new Error("Joueur introuvable"), { code: 404 });
  if (!r.ok) throw Object.assign(new Error("API Clash of Clans indisponible (" + r.status + ")"), { code: 502 });
  return analyse(await r.json());
}

// poste la candidature (une seule fois par tag et par 24 h) ; user = compte Discord du joueur, s'il est connu
async function post(a, env, user) {
  const key = new Request("https://gravaen.cache/sent/" + a.tag.slice(1));
  const cache = caches.default;
  if (await cache.match(key)) return { already: true };
  const msg = embed(a);
  if (user) {
    const name = user.global_name || user.username;
    msg.content = "<@" + user.id + "> souhaite rejoindre votre clan";
    msg.allowed_mentions = { parse: [] }; // affiche la mention sans notifier
    msg.embeds[0].fields.unshift({ name: "💬 Discord", value: "<@" + user.id + "> · **" + name + "** (@" + user.username + ")\n[Ouvrir son profil et lui écrire](https://discord.com/users/" + user.id + ")" });
  }
  const d = await fetch(env.DISCORD_WEBHOOK, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(msg) });
  if (!d.ok) throw new Error("Envoi sur Discord impossible");
  // même fiche dans le salon staff, si le webhook est configuré (un échec ici ne bloque pas la candidature)
  if (env.DISCORD_STAFF_WEBHOOK) {
    try {
      await fetch(env.DISCORD_STAFF_WEBHOOK, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(msg) });
    } catch (e) {}
  }
  // fiche diagnostic publique dans #fiches, si le webhook est configuré
  if (env.DISCORD_FICHES_WEBHOOK) {
    try {
      const f = fiche(a, user);
      const w = await warLine(a, env);   // fin mémorable : la prochaine guerre du clan conseillé
      if (w) f.content = (f.content ? f.content + "\n" : "") + w;
      await fetch(env.DISCORD_FICHES_WEBHOOK, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(f) });
    } catch (e) {}
  }
  await cache.put(key, new Response("1", { headers: { "Cache-Control": "max-age=86400" } }));
  return { already: false };
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    const origin = req.headers.get("Origin") || "*";
    const callback = url.origin + "/callback";
    const invite = env.DISCORD_INVITE || "https://discord.gg/XAUWg3rnj";

    // 1) « Envoyer avec Discord » : on part sur la page d'accord de Discord (le tag voyage dans « state »)
    if (req.method === "GET" && url.pathname === "/auth") {
      const tag = cleanTag(url.searchParams.get("tag"));
      if (!okTag(tag)) return page("Tag invalide.");
      if (!env.DISCORD_CLIENT_ID) return page("Connexion Discord pas encore configurée.");
      const q = new URLSearchParams({ client_id: env.DISCORD_CLIENT_ID, response_type: "code", redirect_uri: callback, scope: "identify", state: tag.slice(1), prompt: "none" });
      return redirect("https://discord.com/oauth2/authorize?" + q);
    }

    // 2) retour de Discord : on récupère son compte, on poste la candidature, puis direction le serveur
    if (req.method === "GET" && url.pathname === "/callback") {
      const tag = cleanTag(url.searchParams.get("state"));
      const code = url.searchParams.get("code");
      if (!okTag(tag)) return page("Candidature introuvable, recommence depuis le site.");
      if (!code) return page("Connexion Discord annulée. Reviens sur le site pour réessayer.");
      try {
        const t = await fetch("https://discord.com/api/oauth2/token", {
          method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: new URLSearchParams({ client_id: env.DISCORD_CLIENT_ID, client_secret: env.DISCORD_CLIENT_SECRET, grant_type: "authorization_code", code, redirect_uri: callback }),
        });
        if (!t.ok) throw new Error("Connexion Discord refusée");
        const tok = await t.json();
        const u = await fetch("https://discord.com/api/users/@me", { headers: { Authorization: "Bearer " + tok.access_token } });
        if (!u.ok) throw new Error("Compte Discord illisible");
        const user = await u.json();
        await post(await player(tag, env), env, user);
        return redirect(invite);
      } catch (e) {
        return page("Oups : " + e.message + ". Reviens sur le site pour réessayer.");
      }
    }

    if (req.method === "OPTIONS") return new Response(null, { headers: cors(origin) });
    if (req.method !== "POST") return json({ error: "POST attendu" }, 405, origin);

    // 3) le site demande le résumé du joueur (send=false), ou l'envoi sans Discord (send=true)
    let body;
    try { body = await req.json(); } catch { return json({ error: "Requête invalide" }, 400, origin); }
    const tag = cleanTag(body.tag);
    if (!okTag(tag)) return json({ error: "Tag invalide" }, 400, origin);
    try {
      const a = await player(tag, env);
      if (body.send) { const r = await post(a, env, null); return json({ ...a, sent: true, already: r.already }, 200, origin); }
      return json({ ...a, discord: !!env.DISCORD_CLIENT_ID }, 200, origin);
    } catch (e) {
      return json({ error: e.message }, e.code || 502, origin);
    }
  },
};
