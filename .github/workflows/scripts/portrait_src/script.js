(function(){
var root=document.getElementById('fiche');
var esc=function(t){return String(t==null?'':t).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})};
var nb=function(n){return Number(n||0).toLocaleString('fr-FR',{maximumFractionDigits:1})};
var FR={Legend:'Légende',Electro:'Électro',Dragon:'Dragon',Titan:'Titan',Golem:'Golem',Witch:'Sorcière',Valkyrie:'Valkyrie',Wizard:'Sorcier',Archer:'Archère',Barbarian:'Barbare',Skeleton:'Squelette'};
var lig=function(n){n=String(n||'');var m=n.match(/^(.+?)\s*League\s*(.*)$/);return m?((FR[m[1]]||m[1])+(m[2]?' '+m[2]:'')):(n&&!/Unranked/.test(n)?n:'Non classé')};
var G={cwl:['Ligue de clans',5,15],gdc:['Guerre',4,10],cap:['Capitale',3,10],rk:['Classé',2,10],act:['Activité',1.5,10],don:['Dons',1,10]};
var COL={cwl:'#212320',gdc:'#4A4B45',cap:'#76776F',rk:'#9C9A90',act:'#BDB9AC',don:'#DCD6C6'};
var I={cwl:['Leader technique','tire le clan vers le haut en Ligue de clans'],gdc:['Attaquant sur qui on compte','assure les étoiles en guerre'],cap:['Moteur de la capitale','fait grandir la capitale à chaque raid'],rk:['Vitrine du clan','montre jusqu’où un joueur de Gravaen peut aller'],act:['Repère du clan','garde le rythme du clan au quotidien'],don:['Soutien de l’équipe','permet à chacun d’attaquer à pleine puissance']};
var B={champ:['Champion de la saison','M3.5 8.5l4.2 3.3L12 5.5l4.3 6.3 4.2-3.3-1.8 10H5.3z'],cwl:['Maître de la Ligue','M12 3l7 3v5.5c0 4.3-2.9 7.6-7 9.5-4.1-1.9-7-5.2-7-9.5V6z M9 12l2 2 4-4'],gdc:['Chef de guerre','M14.5 17.5L3 6V3h3l11.5 11.5M13 19l6-6M16 16l4 4M19 21l2-2M14.5 6.5L18 3h3v3l-3.5 3.5M5 14l4 4M7 17l-3 3M3 19l2 2'],cap:['Bâtisseur de capitale','M4 21V9h3V5h2v4h2V5h2v4h2V5h2v4h3v12z M10 21v-4a2 2 0 014 0v4'],rk:['Compétiteur','M8 4h8v4a4 4 0 01-8 0z M8 6H5c0 2 1.3 3.6 3.2 4 M16 6h3c0 2-1.3 3.6-3.2 4 M12 12v4 M8.5 20h7 M10 16h4l.5 4h-5z'],act:['Infatigable','M12 3c1.2 3 4.5 5 4.5 9.5a4.5 4.5 0 01-9 0c0-2.2 1.1-3.6 2.3-4.6 0 2 .9 3.3 2.2 3.6-.9-3-.2-6.1 0-8.5z'],don:['Cœur du clan','M12 20s-7-4.4-7-10a4 4 0 017-2.7A4 4 0 0119 10c0 5.6-7 10-7 10z']};
var force=function(p,k){var r=(p.r||{})[k];return r?(G[k][2]+1-r)/G[k][2]:0};
var MOIS=['janvier','février','mars','avril','mai','juin','juillet','août','septembre','octobre','novembre','décembre'],MC=['janv.','févr.','mars','avr.','mai','juin','juil.','août','sept.','oct.','nov.','déc.'];
var CRT={'Légende':'Lég.','Électro':'Élec.','Dragon':'Drag.','Sorcière':'Sorc.','Sorcier':'Sorc.','Valkyrie':'Valk.','Archère':'Arch.','Barbare':'Barb.','Squelette':'Squel.'};
function court(n){var l=lig(n);var w=l.split(' ');if(CRT[w[0]])w[0]=CRT[w[0]];return w.join(' ')}
var TRO='<svg class="pt-ti" viewBox="0 0 24 24" aria-hidden="true"><path d="M8 4h8v4a4 4 0 01-8 0z M8 6H5c0 2 1.3 3.6 3.2 4 M16 6h3c0 2-1.3 3.6-3.2 4 M12 12v4 M8.5 20h7 M10 16h4l.5 4h-5z"/></svg>';
function svg(d){return '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="'+d+'"/></svg>'}
function stars(n){var s='';for(var i=0;i<3;i++)s+=i<n?'★':'<i>★</i>';return s}
function head(t,d){return '<div class="head"><h2 class="eyeb"><i>—</i>'+t+'</h2>'+(d?'<p class="head-desc">'+d+'</p>':'')+'</div>'}
function facts(a){return '<dl class="facts">'+a.map(function(x){return '<div><dt>'+x[0]+'</dt><dd>'+x[1]+'</dd></div>'}).join('')+'</dl>'}
function tabs(id,items,on){return '<div class="pseg pt-tabs" id="'+id+'" role="tablist"><span class="ps-ind" aria-hidden="true"></span>'+items.map(function(x){return '<button type="button" role="tab" class="ps-b" data-v="'+x[0]+'" aria-selected="'+(x[0]===on)+'">'+x[1]+'</button>'}).join('')+'</div>'}
function tabsOn(id,fn){var g=document.getElementById(id);if(!g)return;var ind=g.querySelector('.ps-ind');
 function mv(){var b=g.querySelector('[aria-selected="true"]');if(b&&ind){ind.style.width=b.offsetWidth+'px';ind.style.transform='translateX('+(b.offsetLeft-4)+'px)'}}
 g.querySelectorAll('.ps-b').forEach(function(b){b.addEventListener('click',function(){g.querySelectorAll('.ps-b').forEach(function(x){x.setAttribute('aria-selected',x===b)});mv();fn(b.dataset.v)})});
 mv();window.addEventListener('resize',mv)}
function fail(msg){root.innerHTML='<section class="s pt"><div class="wrap"><p class="pt-empty">'+msg+'</p><p><a class="cta" href="./#staff">Voir le staff</a></p></div></section>'}
var q=new URLSearchParams(location.search).get('t')||'';if(q&&q.charAt(0)!=='#')q='#'+q;
Promise.all(['data/fiches.json','data/players.json'].map(function(u){return fetch(u,{cache:'no-store'}).then(function(r){if(!r.ok)throw 0;return r.json()})})).then(function(res){
 var F=res[0].players||{},P=res[1].players||{},season=res[1].season||res[0].season||'';
 var staff=Object.keys(P).filter(function(t){return P[t].role==='leader'||P[t].role==='coLeader'}).map(function(t){var x=P[t];x._t=t;return x}).sort(function(a,b){return (a.role==='leader'?0:1)-(b.role==='leader'?0:1)||(b.score||0)-(a.score||0)});
 var used={};staff.forEach(function(p){var c=Object.keys(I).filter(function(k){return force(p,k)>0}).sort(function(a,b){return force(p,b)-force(p,a)});var m=c.filter(function(k){return !used[k]})[0]||c[0];if(m)used[m]=1;p._c=m?[m].concat(c.filter(function(k){return k!==m}).slice(0,1)):[]});
 if(!q){if(!staff[0])return fail('Le staff s’affichera ici dès le prochain relevé.');q=staff[0]._t}
 var f=F[q],p=P[q];if(!f&&!p)return fail('Ce portrait n’existe pas, ou ce joueur ne fait plus partie du staff.');
 f=f||{};p=p||{v:{}};var v=p.v||{};
 var name=f.n||p.n,th=f.th||p.th,chef=(f.role||p.role)==='leader',clan=(f.c||p.c)==='second'?'Gravaen 2':'Gravaen 1';
 document.title=name+' · Gravaen';
 var cats=(staff.filter(function(x){return x._t===q})[0]||{})._c||[];
 var prof=cats.length?(function(){var a=I[cats[0]],b=cats[1]?I[cats[1]]:null;return a[0]+(b?' et '+b[0].charAt(0).toLowerCase()+b[0].slice(1):'')+'&nbsp;: '+a[1]+'.'})():'Garant de l’organisation&nbsp;: lance les guerres et valide les montées.';
 var bd=[];if(p.rank===1)bd.push('champ');Object.keys(G).forEach(function(k){var r=(p.r||{})[k];if(r&&r<=3)bd.push(k)});
 var link='https://link.clashofclans.com/fr?action=OpenPlayerProfile&tag='+encodeURIComponent(q.replace('#',''));
 var lgi=f.lgi||p.lgi,lgn=lig(f.lg||p.lg),tr=f.tr!=null?f.tr:(v.rk||0);
 var mo=season?MOIS[+season.slice(5,7)-1]+' '+season.slice(0,4):'';
 var h='';
 /* 1. En-tête sombre : identité, blason de classé, badges, profil */
 var w=f.war||{},atk=w.atk||0,play=atk+(w.missed||0),HT=f.hits||{atk:[],def:[]},FA=f.fam;
 h+='<section class="pt-hero"><div class="wrap"><a class="pt-back" href="./#staff">← Le staff</a><div class="pt-hgrid"><div class="pt-left"><div class="pt-who">';
 var hdvf='hdv-'+Math.max(1,Math.min(18,+th||1))+'.webp';h+='<img class="pt-hdv" src="'+((window.__IMG||{})[hdvf]||hdvf)+'" alt="Hôtel de ville niveau '+esc(th)+'" width="84" height="98"><div class="pt-nm"><p class="pt-role">'+(chef?'Chef':'Chef adjoint')+' · HDV '+esc(th)+'</p><h1>'+esc(name)+'</h1>';
 h+='<button class="pt-tag copytag" type="button" data-copy="'+esc(q)+'" aria-label="Copier le tag '+esc(q)+'"><span class="tt">'+esc(q)+'</span><svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="9" y="9" width="11" height="11" rx="1.5"/><path d="M5 15V5a1 1 0 0 1 1-1h10"/></svg></button>'+(f.xp?'<span class="pt-xp">Niveau '+esc(f.xp)+'</span>':'')+'</div></div>';
 if(bd.length)h+='<div class="pt-bd">'+bd.map(function(k){return '<span class="bdg" tabindex="0" role="img" aria-label="'+B[k][0]+'" data-tip="'+B[k][0]+'">'+svg(B[k][1])+'</span>'}).join('')+'</div>';
 h+='<p class="pt-prof">'+prof+'</p><div class="pt-acts"><a class="cta" href="'+link+'" target="_blank" rel="noopener">Ouvrir dans le jeu<svg class="pt-ext" viewBox="0 0 24 24" aria-hidden="true"><path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 01-1 1H5a1 1 0 01-1-1V7a1 1 0 011-1h5"/></svg></a></div></div>';
 h+='<div class="pt-lg">'+(lgi?'<img src="'+esc(lgi)+'" alt="Blason '+esc(lgn)+'">':'<span class="pt-lgph" aria-hidden="true"></span>')+'<div><b>'+esc(lgn).toUpperCase()+'</b><span>'+nb(tr)+' trophée'+(tr>1?'s':'')+'</span>'+(f.best?'<span>Record&nbsp;: '+nb(f.best)+'</span>':'')+'</div></div></div></div></section>';
 /* chiffres clés + d'où viennent les points */
 var triR=FA?FA.tri:(atk?Math.round((w.tri||0)/atk*100):null);
 h+='<section class="s pt pt-k"><div class="wrap"><div class="pt-card">'+facts([['Points de la saison',nb(p.score||0)],['Étoiles en ligue',nb(v.cwl||0)],['Étoiles en guerre',nb(v.gdc||0)],['Taux de triples',triR!=null?triR+'&nbsp;%':'—']]);
 var tot=Object.keys(G).reduce(function(a,k){return a+((p.p||{})[k]||0)},0);
 if(tot)h+='<p class="pt-mini" style="margin-top:16px">D’où viennent ses points</p><div class="pt-split">'+Object.keys(G).map(function(k){var x=(p.p||{})[k]||0;return x?'<i style="width:'+(x/tot*100)+'%;background:'+COL[k]+'" title="'+G[k][0]+'"></i>':''}).join('')+'</div><div class="pt-leg">'+Object.keys(G).filter(function(k){return (p.p||{})[k]}).map(function(k){return '<span><u style="background:'+COL[k]+'"></u>'+G[k][0]+' <b>'+nb(p.p[k])+'</b></span>'}).join('')+'</div>';
 h+='</div></div></section>';
 /* 2. Ligue de clans */
 var rd=f.cwl||[];
 h+='<section class="s pt"><div class="wrap">'+head('Ligue de clans','Sa ligue chez Gravaen en '+esc(mo)+', manche par manche.')+'<div class="pt-card">';
 if(rd.length){var tiles='';for(var i=0;i<7;i++){var r=rd[i];if(!r){tiles+='<div class="pt-rd off"><span class="n">M'+(i+1)+'</span><span class="p">Pas aligné</span></div>';continue}
   if(!r[3]){tiles+='<div class="pt-rd off"><span class="n">M'+(i+1)+'</span><span class="st">'+stars(0)+'</span><span class="p">Pas jouée</span></div>';continue}
   tiles+='<div class="pt-rd'+(r[0]===3?' tri':'')+'"><span class="n">M'+(i+1)+'</span><span class="st">'+stars(r[0])+'</span><span class="p">'+Math.round(r[1])+'&nbsp;%</span><span class="h">HDV '+esc(r[2])+'</span></div>'}
  var pl=rd.filter(function(r){return r[3]}),tri=pl.filter(function(r){return r[0]===3}).length,pc=pl.length?pl.reduce(function(a,r){return a+r[1]},0)/pl.length:0;
  h+='<div class="pt-rounds">'+tiles+'</div>'+facts([['Étoiles',nb(v.cwl||pl.reduce(function(a,r){return a+r[0]},0))],['Attaques',pl.length+'/'+rd.length],['Triples',tri],['Destruction',nb(Math.round(pc*10)/10)+'&nbsp;%']]);
 }else h+=facts([['Étoiles',nb(v.cwl||0)],['Destruction',nb(p.cwlPct||0)+'&nbsp;%']])+'<p class="pt-note">Le détail manche par manche arrive au prochain relevé.</p>';
 h+='</div></div></section>';
 /* 3. Guerre et moyennes, combat par combat */
 h+='<section class="s pt"><div class="wrap">'+head('Guerre','Ses guerres et ses moyennes, combat par combat.')+'<div class="pt-card">'+facts([['Étoiles cette saison',nb(v.gdc||0)],['Triples',nb(w.tri||0)+' sur '+nb(atk)],['Destruction moyenne',nb(w.pct||0)+'&nbsp;%'],['Attaques jouées',play?Math.round(atk/play*100)+'&nbsp;%':'—']])+'</div>';
 h+='<div class="pt-card" style="margin-top:12px">'+tabs('sm',[['war','Guerre'],['cwl','Ligue de clans']],'war')+tabs('sp',[['7','7 jours'],['30','30 jours'],['90','90 jours']],'30')+'<div id="stats"></div></div>';
 if(FA)h+='<div class="pt-card" style="margin-top:12px"><p class="pt-h">Face à Gravaen</p>'+[['Taux de triples',FA.tri,FA.triBetter,FA.triAvg],['Destruction moyenne',FA.pct,FA.pctBetter,FA.pctAvg]].map(function(x){return '<div class="pt-fm"><div class="t">'+x[0]+'<span>'+x[1]+'&nbsp;%</span></div><div class="tr"><i style="width:'+Math.min(100,x[1])+'%"></i><em style="left:'+Math.min(99,x[3])+'%"></em></div><div class="d">Meilleur que <b>'+x[2]+'&nbsp;%</b> des joueurs de Gravaen · moyenne du clan&nbsp;: '+x[3]+'&nbsp;%</div></div>'}).join('')+'<p class="pt-note">Parmi les '+FA.n+' joueurs des deux clans avec au moins 5 attaques cette saison. Le trait jaune marque la moyenne du clan.</p></div>';
 h+='</div></section>';
 /* 4. Capitale */
 h+='<section class="s pt"><div class="wrap">'+head('Capitale','Ses raids du week-end cette saison.')+'<div class="pt-card">'+facts([['Or de capitale pillé',nb(v.cap||0)],['Points en capitale',nb((p.p||{}).cap||0)+' / 30']])+'</div></div></section>';
 /* 5. Classé : ligue actuelle, record, puis semaine après semaine */
 var HI=f.hist||{s:{},w:{}},SS=Object.keys(HI.s||{}).sort(),WK=Object.keys(HI.w||{}).sort();
 h+='<section class="s pt"><div class="wrap">'+head('Classé','Sa ligue, semaine après semaine.')+'<div class="pt-card pt-rk">'+(lgi?'<img src="'+esc(lgi)+'" alt="Blason '+esc(lgn)+'">':'<span class="pt-wph" aria-hidden="true"></span>')+'<div>'+facts([['Ligue',esc(lgn)],['Trophées',nb(tr)],['Record de trophées',nb(f.best||0)],['Points en classé',nb((p.p||{}).rk||0)+' / 20']])+'</div></div>';
 if(WK.length)h+='<div class="pt-card" style="margin-top:12px"><p class="pt-h">Ses dernières semaines</p><div class="pt-wk">'+WK.map(function(k,ix){var x=HI.w[k];return (ix?'<i class="pt-sep" aria-hidden="true"></i>':'')+'<div class="pt-w">'+(x[1]?'<img src="'+esc(x[1])+'" alt="">':'<span class="pt-wph" aria-hidden="true"></span>')+'<b>'+esc(court(x[0]))+'</b><span class="pt-tro">'+TRO+nb(x[2])+'</span><span>'+(+k.slice(8,10))+' '+MC[+k.slice(5,7)-1]+'</span></div>'}).join('')+'</div><p class="pt-note">Une case par semaine&nbsp;: sa ligue et ses trophées en fin de semaine'+(HI.since?', suivi depuis le '+(+HI.since.slice(8,10))+' '+MOIS[+HI.since.slice(5,7)-1]:'')+'.</p></div>';
 if(SS.length>1)h+='<div class="pt-card" style="margin-top:12px"><p class="pt-h">Ses saisons</p><ol class="crk-l">'+SS.slice().reverse().map(function(k){var x=HI.s[k];return '<li><span class="crk-n">'+MOIS[+k.slice(5,7)-1].replace(/^./,function(c){return c.toUpperCase()})+' '+k.slice(0,4)+'</span><span class="crk-lg">'+nb(x.score)+' PTS · '+esc(lig(x.lg)).toUpperCase()+'</span></li>'}).join('')+'</ol></div>';
 h+='</div></section>';
 /* 6. Activité et dons */
 h+='<section class="s pt"><div class="wrap">'+head('Activité','Sa présence au quotidien et ses dons.')+'<div class="pt-card">'+facts([['Jours actifs cette saison',nb(v.act||0)],['Troupes données',nb(v.don||0)],['Points en activité',nb((p.p||{}).act||0)+' / 15'],['Points en dons',nb((p.p||{}).don||0)+' / 10']])+'</div></div></section>';
 /* 7. Armée */
 var A=f.army||{},T=[['heroes','Héros'],['equip','Équipements'],['troops','Troupes'],['spells','Sorts'],['pets','Familiers'],['siege','Engins']].filter(function(x){return (A[x[0]]||[]).length});
 if(T.length)h+='<section class="s pt"><div class="wrap">'+head('Armée','Son village, niveau par niveau.')+'<details class="pt-card pt-det"><summary>Voir son armée</summary>'+tabs('sa',T.map(function(x){var l=A[x[0]];return [x[0],x[1]+' '+l.filter(function(u){return u[1]>=u[2]}).length+'/'+l.length]}),T[0][0])+'<ol class="crk-l pt-army" id="army"></ol></details></div></section>';
 root.innerHTML=h;
 document.querySelectorAll('.copytag').forEach(function(b){b.addEventListener('click',function(){var t=b.dataset.copy,s=b.querySelector('.tt');var ok=function(){s.textContent='Copié';setTimeout(function(){s.textContent=t},1400)};if(navigator.clipboard)navigator.clipboard.writeText(t).then(ok,function(){});})});
 var M='war',PD=30;
 function stats(){var lim=Date.now()/1000-PD*86400,A2=HT.atk.filter(function(a){return a[1]===M&&a[0]>=lim}),D2=HT.def.filter(function(a){return a[1]===M&&a[0]>=lim}),el=document.getElementById('stats');
  if(!A2.length){el.innerHTML='<p class="pt-empty">Pas d’attaque '+(M==='war'?'en guerre':'en Ligue de clans')+' sur les '+PD+' derniers jours.</p>';return}
  var c=[0,0,0,0];A2.forEach(function(a){c[a[2]]++});var n=A2.length,cl=['#D9D2BE','#A7A292','#212320','#F8C801'];
  var o='<p class="pt-mini">Répartition des étoiles en attaque</p><div class="pt-split">'+[3,2,1,0].map(function(k){return c[k]?'<i style="width:'+(c[k]/n*100)+'%;background:'+cl[k]+'"></i>':''}).join('')+'</div><div class="pt-leg">'+[3,2,1,0].map(function(k){return '<span><u style="background:'+cl[k]+'"></u><b>'+c[k]+'</b> × '+k+' étoile'+(k>1?'s':'')+'</span>'}).join('')+'<span>sur '+n+' attaque'+(n>1?'s':'')+'</span></div>';
  function av(L,att){if(!L.length)return '<div><p class="pt-h">'+(att?'En attaque':'En défense')+'</p><p class="pt-empty">Pas encore de donnée.</p></div>';var s=L.reduce(function(a,x){return a+x[2]},0)/L.length,pc=L.reduce(function(a,x){return a+x[3]},0)/L.length,tr=L.filter(function(x){return x[2]===3}).length/L.length*100;
   return '<div><p class="pt-h">'+(att?'En attaque':'En défense')+'</p>'+facts([[att?'Étoiles en moyenne':'Étoiles concédées',nb(Math.round(s*10)/10)],[att?'Destruction':'Destruction subie',Math.round(pc)+'&nbsp;%'],[att?'Triples':'Triples subis',Math.round(tr)+'&nbsp;%']])+'<p class="pt-note">sur '+L.length+' '+(att?'attaque':'défense')+(L.length>1?'s':'')+'</p></div>'}
  el.innerHTML=o+'<div class="pt-two">'+av(A2,1)+av(D2,0)+'</div>'}
 stats();tabsOn('sm',function(x){M=x;stats()});tabsOn('sp',function(x){PD=+x;stats()});
 function army(k){var l=A[k]||[];document.getElementById('army').innerHTML=l.map(function(u){var m=u[1]>=u[2];return '<li><span class="crk-n">'+esc(u[0])+(u[3]&&u[3].length?'<span class="eq">'+u[3].map(function(e){return esc(e[0])+' '+e[1]}).join(' · ')+'</span>':'')+'</span><span class="lvl'+(m?' max':'')+'">'+u[1]+'<span> / '+u[2]+'</span></span></li>'}).join('')}
 if(T.length){army(T[0][0]);var dt=document.querySelector('.pt-det');tabsOn('sa',army);if(dt)dt.addEventListener('toggle',function(){window.dispatchEvent(new Event('resize'))})}
}).catch(function(){fail('Le portrait n’a pas pu être chargé. Réessaie dans un instant.')});
})();
/* barre du haut : le blason du clan remplace « Gravaen » quand on a dépassé l'en-tête, comme sur l'accueil */
(function(){var r=document.documentElement,t=false;
 fetch('data/clan.json',{cache:'no-store'}).then(function(x){return x.json()}).then(function(d){var hb=document.querySelector('.brand-b'),src=((d.clans||{}).main||{}).badge||(d.icons||{}).badge||d.badgeUrl;if(hb&&src){hb.onload=function(){hb.hidden=false;hb.parentNode.classList.add('has-b')};hb.src=src}}).catch(function(){});
 function u(){var hs=document.querySelector('.pt-hero');r.classList.toggle('past-hero',!!hs&&hs.getBoundingClientRect().bottom<90)}
 addEventListener('scroll',function(){if(t)return;t=true;requestAnimationFrame(function(){t=false;u()})},{passive:true});addEventListener('resize',u);setTimeout(u,300)})();
