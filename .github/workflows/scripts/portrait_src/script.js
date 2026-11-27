(function(){
var root=document.getElementById('fiche');
var esc=function(t){return String(t==null?'':t).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})};
var nb=function(n){return Number(n||0).toLocaleString('fr-FR',{maximumFractionDigits:1})};
var FR={Legend:'Légende',Electro:'Électro',Dragon:'Dragon',Titan:'Titan',Golem:'Golem',Witch:'Sorcière',Valkyrie:'Valkyrie',Wizard:'Sorcier',Archer:'Archère',Barbarian:'Barbare',Skeleton:'Squelette'};
var lig=function(n){n=String(n||'');var m=n.match(/^(.+?)\s*League\s*(.*)$/);return m?((FR[m[1]]||m[1])+(m[2]?' '+m[2]:'')):(n&&!/Unranked/.test(n)?n:'Non classé')};
var G={cwl:['Ligue de clans',5,15],gdc:['Guerre',4,10],cap:['Capitale',3,10],rk:['Classé',2,10],act:['Activité',1.5,10],don:['Dons',1,10]};
var COL={cwl:'#212320',gdc:'#5C5D56',cap:'#8C8A80',rk:'#B3AFA3',act:'#D2CDBF',don:'#E8E2D2'};
var I={cwl:['Leader technique','tire le clan vers le haut en Ligue de clans'],gdc:['Attaquant sur qui on compte','assure les étoiles en guerre'],cap:['Moteur de la capitale','fait grandir la capitale à chaque raid'],rk:['Vitrine du clan','montre jusqu’où un joueur de Gravaen peut aller'],act:['Repère du clan','garde le rythme du clan au quotidien'],don:['Soutien de l’équipe','permet à chacun d’attaquer à pleine puissance']};
var B={champ:['Champion de la saison','M3.5 8.5l4.2 3.3L12 5.5l4.3 6.3 4.2-3.3-1.8 10H5.3z'],cwl:['Maître de la Ligue','M12 3l7 3v5.5c0 4.3-2.9 7.6-7 9.5-4.1-1.9-7-5.2-7-9.5V6z M9 12l2 2 4-4'],gdc:['Chef de guerre','M14.5 17.5L3 6V3h3l11.5 11.5M13 19l6-6M16 16l4 4M19 21l2-2M14.5 6.5L18 3h3v3l-3.5 3.5M5 14l4 4M7 17l-3 3M3 19l2 2'],cap:['Bâtisseur de capitale','M4 21V9h3V5h2v4h2V5h2v4h2V5h2v4h3v12z M10 21v-4a2 2 0 014 0v4'],rk:['Compétiteur','M8 4h8v4a4 4 0 01-8 0z M8 6H5c0 2 1.3 3.6 3.2 4 M16 6h3c0 2-1.3 3.6-3.2 4 M12 12v4 M8.5 20h7 M10 16h4l.5 4h-5z'],act:['Infatigable','M12 3c1.2 3 4.5 5 4.5 9.5a4.5 4.5 0 01-9 0c0-2.2 1.1-3.6 2.3-4.6 0 2 .9 3.3 2.2 3.6-.9-3-.2-6.1 0-8.5z'],don:['Cœur du clan','M12 20s-7-4.4-7-10a4 4 0 017-2.7A4 4 0 0119 10c0 5.6-7 10-7 10z']};
var force=function(p,k){var r=(p.r||{})[k];return r?(G[k][2]+1-r)/G[k][2]:0};
var MOIS=['janvier','février','mars','avril','mai','juin','juillet','août','septembre','octobre','novembre','décembre'],MC=['janv.','févr.','mars','avr.','mai','juin','juil.','août','sept.','oct.','nov.','déc.'];
var CRT={'Légende':'Lég.','Électro':'Élec.','Dragon':'Drag.','Sorcière':'Sorc.','Sorcier':'Sorc.','Valkyrie':'Valk.','Archère':'Arch.','Barbare':'Barb.','Squelette':'Squel.'};
function court(n){var l=lig(n);var w=l.split(' ');if(CRT[w[0]])w[0]=CRT[w[0]];return w.join(' ')}
var TRO='<svg class="pt-ti" viewBox="0 0 24 24" aria-hidden="true"><path d="M8 4h8v4a4 4 0 01-8 0z M8 6H5c0 2 1.3 3.6 3.2 4 M16 6h3c0 2-1.3 3.6-3.2 4 M12 12v4 M8.5 20h7 M10 16h4l.5 4h-5z"/></svg>';
function svg(d){return '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="'+d+'"/></svg>'}
var SV=function(e){return '<svg class="pw-star'+(e?' e':'')+'" viewBox="0 0 24 24" aria-hidden="true"><path d="M11.525 2.295a.53.53 0 0 1 .95 0l2.31 4.679a2.123 2.123 0 0 0 1.595 1.16l5.166.756a.53.53 0 0 1 .294.904l-3.736 3.638a2.123 2.123 0 0 0-.611 1.878l.882 5.14a.53.53 0 0 1-.771.56l-4.618-2.428a2.122 2.122 0 0 0-1.973 0L6.396 21.01a.53.53 0 0 1-.77-.56l.881-5.139a2.122 2.122 0 0 0-.611-1.879L2.16 9.795a.53.53 0 0 1 .294-.906l5.165-.755a2.122 2.122 0 0 0 1.597-1.16z"/></svg>'};
function stars(n){var s='';for(var i=0;i<3;i++)s+=SV(i>=n);return s}
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
 var prof0=cats.length?(function(){var a=I[cats[0]],b=cats[1]?I[cats[1]]:null;return a[0]+(b?' et '+b[0].charAt(0).toLowerCase()+b[0].slice(1):'')+'&nbsp;: '+a[1]+'.'})():'Garant de l’organisation&nbsp;: lance les guerres et valide les montées.';
 var SG={cwl:function(){return nb(v.cwl||0)+' étoiles en Ligue de clans ce mois-ci'},gdc:function(){return nb(v.gdc||0)+' étoiles en guerre ce mois-ci'},cap:function(){return nb(v.cap||0)+' d’or pillé en capitale'},rk:function(){return nb(f.tr!=null?f.tr:(v.rk||0))+' trophées en '+lig(f.lg||p.lg)},act:function(){return 'présent '+nb(v.act||0)+' jours cette saison'},don:function(){return nb(v.don||0)+' troupes données à l’équipe'}};
 var cs=Object.keys(G).filter(function(k){return (p.r||{})[k]}).sort(function(a,b){return p.r[a]-p.r[b]}).slice(0,2);
 var prof=cs.length?cs.map(function(k){return SG[k]()}).join(' · ').replace(/^./,function(c){return c.toUpperCase()}):prof0;
 var bd=[];if(p.b)bd=p.b.filter(function(k){return B[k]});else{if(p.rank===1)bd.push('champ');Object.keys(G).forEach(function(k){var r=(p.r||{})[k];if(r&&r<=3)bd.push(k)})}  /* badges de la dernière saison terminée, sinon de la saison en cours */
 var link='https://link.clashofclans.com/fr?action=OpenPlayerProfile&tag='+encodeURIComponent(q.replace('#',''));
 var lgi=f.lgi||p.lgi,lgn=lig(f.lg||p.lg),tr=f.tr!=null?f.tr:(v.rk||0);
 var mo=season?MOIS[+season.slice(5,7)-1]+' '+season.slice(0,4):'';
 var h='';
 /* En-tête : identité, badges, profil, bouton */
 var w=f.war||{},atk=w.atk||0,HT=f.hits||{atk:[],def:[]},FA=f.fam,PP=p.p||{};
 h+='<section class="pt-hero"><div class="wrap">'+(/^(leader|coLeader)$/.test(f.role||p.role)?'<a class="pt-back" href="./#staff">← Le staff</a>':'<a class="pt-back" href="./#meilleurs">← Le classement</a>')+'<div class="pw-hero"><div class="pt-who">';
 var hdvf='hdv-'+Math.max(1,Math.min(18,+th||1))+'.webp';h+='<img class="pt-hdv" src="'+((window.__IMG||{})[hdvf]||hdvf)+'" alt="Hôtel de ville niveau '+esc(th)+'" width="84" height="98"><div class="pt-nm"><p class="pt-role">'+({leader:'Chef',coLeader:'Chef adjoint',admin:'Aîné',member:'Membre'}[f.role||p.role]||'Membre')+' · HDV '+esc(th)+(f.xp?' · Niveau '+esc(f.xp):'')+'</p><h1>'+esc(name)+'</h1>';
 h+='<button class="pt-tag copytag" type="button" data-copy="'+esc(q)+'" aria-label="Copier le tag '+esc(q)+'"><span class="tt">'+esc(q)+'</span><svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="9" y="9" width="11" height="11" rx="1.5"/><path d="M5 15V5a1 1 0 0 1 1-1h10"/></svg></button>'+'</div></div>';
 h+='<a class="cta pw-open" href="'+link+'" target="_blank" rel="noopener">Ouvrir dans le jeu<svg class="pt-ext" viewBox="0 0 24 24" aria-hidden="true"><path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 01-1 1H5a1 1 0 01-1-1V7a1 1 0 011-1h5"/></svg></a></div>';
 var RK=function(r){return r===1?'1er':r+'e'};
 if(bd.length)h+='<ul class="pw-bdg">'+bd.map(function(k){var r=k==='champ'?0:(p.r||{})[k];return '<li class="b-'+k+'">'+svg(B[k][1])+'<span>'+B[k][0]+'</span></li>'}).join('')+'</ul>';

 var PG=[['apercu','Aperçu'],['guerre','Guerre'],['classe','Classé'],['armee','Armée']];
 h+='<nav class="pw-nav" role="tablist">'+PG.map(function(x,i){return '<button type="button" role="tab" data-p="'+x[0]+'" aria-selected="'+(i===0)+'">'+x[1]+'</button>'}).join('')+'</nav></div></section>';
 /* un widget : titre, info à droite, cases séparées par des traits */
 function wg(t,r,cells,foot,cls){return '<div class="pw'+(cls?' '+cls:'')+'"><div class="pw-h"><b>'+t+'</b>'+(r?'<span>'+r+'</span>':'')+'</div>'+(cells?'<div class="pw-g n'+cells.length+'">'+cells.map(function(c){return '<div><dt>'+c[0]+'</dt><dd>'+c[1]+'</dd>'+(c[2]?'<small>'+c[2]+'</small>':'')+'</div>'}).join('')+'</div>':'')+(foot?'<div class="pw-f">'+foot+'</div>':'')+'</div>'}
 h+='<section class="s pt pw-main"><div class="wrap">';
 /* Aperçu */
 var triR=FA?FA.tri:(atk?Math.round((w.tri||0)/atk*100):null),tot=Object.keys(G).reduce(function(a,k){return a+(PP[k]||0)},0);
 var split=tot?'<p class="pw-l">D’où viennent ses points</p><div class="pt-split">'+Object.keys(G).map(function(k){var x=PP[k]||0;return x?'<i style="width:'+(x/tot*100)+'%;background:'+COL[k]+'" title="'+G[k][0]+'"></i>':''}).join('')+'</div><div class="pt-leg">'+Object.keys(G).filter(function(k){return PP[k]}).map(function(k){return '<span><u style="background:'+COL[k]+'"></u>'+G[k][0]+' <b>'+nb(PP[k])+'</b></span>'}).join('')+'</div>':'';
 var NJ=Object.keys(P).length,ALL=(HT.atk||[]).slice().sort(function(a,b){return b[0]-a[0]});
 h+='<div class="pw-p" data-p="apercu">';
 function tierOf(lg){lg=String(lg||'');if(/legend/i.test(lg)){var r=(lg.match(/(III|II|I)\s*$/)||[])[1];return r==='III'?34:r==='II'?35:36}var n=lg.match(/(\d+)\s*$/);return n?+n[1]:0}
 function val(x,k){var vv=x.v||{};return k==='rk'?(tierOf(x.lg)*1e5+(vv.rk||0)):(vv[k]||0)}
 function place(k){var me=val(p,k);if(!(me>0))return '';var r=1;Object.keys(P).forEach(function(t){if(val(P[t],k)>me)r++});return (r===1?'1er':r+'e')+' sur '+NJ}
 h+=wg('Saison de '+esc(mo.split(' ')[0]),'',[['Points de la saison','<span data-n="'+(p.score||0)+'">'+nb(p.score||0)+'</span>',p.rank?(p.rank===1?'1er':p.rank+'e')+' sur '+NJ+' joueurs':''],['Taux de triples',triR!=null?'<span data-n="'+triR+'">'+triR+'</span>&nbsp;%':'—',FA?'Meilleur que '+FA.triBetter+'&nbsp;% du clan':'']],split,'pw-hi');
 if(ALL.length){var a10=ALL.slice(0,10),s3=a10.filter(function(x){return x[2]===3}).length;
  h+=wg('Ses 10 dernières attaques','',null,'<div class="pw-chips">'+a10.map(function(x){return '<span class="c'+x[2]+'" title="'+(x[1]==='cwl'?'Ligue de clans':'Guerre')+' · '+Math.round(x[3])+' %">'+x[2]+SV(!x[2])+'</span>'}).join('')+'</div><button type="button" class="pw-more" data-go="guerre">Toute sa guerre <span aria-hidden="true">→</span></button>')}
 h+='<div class="pw-three">';
 h+='<div class="pw pw-mini"><div class="pw-h"><b>Classé</b><button type="button" class="pw-more" data-go="classe">Voir <span aria-hidden="true">→</span></button></div><div class="pw-rkb">'+(lgi?'<img src="'+esc(lgi)+'" alt="Blason '+esc(lgn)+'">':'<span class="pt-wph" aria-hidden="true"></span>')+'<div><p class="pw-mid">'+esc(lgn)+'</p><p class="pw-sub">'+TRO+nb(tr)+' · record '+nb(f.best||0)+'</p>'+(place('rk')?'<p class="pw-pl">'+place('rk')+'</p>':'')+'</div></div></div>';
 h+=wg('Capitale','',[['Or de capitale pillé','<span data-n="'+(v.cap||0)+'">'+nb(v.cap||0)+'</span>',place('cap')]],null,'pw-mini');
 var hasS=v.actd!=null;
 h+=wg('Activité','',(hasS?[['Score d’activité','<span data-n="'+(v.act||0)+'">'+nb(v.act||0)+'</span>',place('act')],['Jours actifs','<span data-n="'+v.actd+'">'+nb(v.actd)+'</span>']]:[['Jours actifs','<span data-n="'+(v.act||0)+'">'+nb(v.act||0)+'</span>',place('act')]]).concat([['Troupes données','<span data-n="'+(v.don||0)+'">'+nb(v.don||0)+'</span>',place('don')]]),null,'pw-mini');
 h+='</div></div>';
 /* Guerre */
 var rd=f.cwl||[];
 h+='<div class="pw-p" data-p="guerre" hidden><div class="pw-ctl">'+tabs('sm',[['war','Guerre'],['cwl','Ligue de clans']],'war')+tabs('sp',[['7','7 jours'],['30','30 jours'],['90','90 jours']],'30')+'</div><div id="stats"></div>';
 if(rd.length){var tiles='';for(var i=0;i<7;i++){var r=rd[i];if(!r){tiles+='<div class="pt-rd off"><span class="n">M'+(i+1)+'</span><span class="p">Pas aligné</span></div>';continue}
   if(!r[3]){tiles+='<div class="pt-rd off"><span class="n">M'+(i+1)+'</span><span class="st">'+stars(0)+'</span><span class="p">Pas jouée</span></div>';continue}
   tiles+='<div class="pt-rd'+(r[0]===3?' tri':'')+'"><span class="n">M'+(i+1)+'</span><span class="st">'+stars(r[0])+'</span><span class="p">'+Math.round(r[1])+'&nbsp;%</span><span class="h">HDV '+esc(r[2])+'</span></div>'}
  h+=wg('Ligue de clans','',null,'<div class="pt-rounds">'+tiles+'</div>')}
 if(FA)h+=wg('Face à Gravaen','',null,[['Taux de triples',FA.tri,FA.triBetter,FA.triAvg],['Destruction moyenne',FA.pct,FA.pctBetter,FA.pctAvg]].map(function(x){return '<div class="pt-fm"><div class="t">'+x[0]+'<span>'+x[1]+'&nbsp;%</span></div><div class="tr"><i style="width:'+Math.min(100,x[1])+'%"></i><em style="left:'+Math.min(99,x[3])+'%"></em></div><div class="d">Meilleur que <b>'+x[2]+'&nbsp;%</b> du clan</div></div>'}).join(''));
 h+='</div>';
 /* Classé */
 var HI=f.hist||{w:{}},WK=Object.keys(HI.w||{}).sort();
 h+='<div class="pw-p" data-p="classe" hidden><div class="pw pw-rk"><div class="pw-h"><b>Classé</b></div><div class="pw-rkb">'+(lgi?'<img src="'+esc(lgi)+'" alt="Blason '+esc(lgn)+'">':'<span class="pt-wph" aria-hidden="true"></span>')+'<div><p class="pw-big">'+esc(lgn)+'</p><p class="pw-sub">'+TRO+nb(tr)+' trophée'+(tr>1?'s':'')+' · record '+nb(f.best||0)+'</p></div></div></div>';
 if(WK.length)h+=wg('Ses semaines','',null,'<div class="pt-wk">'+WK.slice().reverse().map(function(k,ix){var x=HI.w[k];return (ix?'<i class="pt-sep" aria-hidden="true"></i>':'')+'<div class="pt-w">'+(x[1]?'<img src="'+esc(x[1])+'" alt="">':'<span class="pt-wph" aria-hidden="true"></span>')+'<b>'+esc(court(x[0]))+'</b><span class="pt-tro">'+TRO+nb(x[2])+'</span><span>'+(+k.slice(8,10))+' '+MC[+k.slice(5,7)-1]+'</span></div>'}).join('')+'</div>');
 h+='</div>';
 /* Armée */
 var A=f.army||{},T=[['heroes','Héros'],['equip','Équipements'],['troops','Troupes'],['spells','Sorts'],['pets','Familiers'],['siege','Engins']].filter(function(x){return (A[x[0]]||[]).length});
 h+='<div class="pw-p" data-p="armee" hidden>'+(T.length?'<div class="pw-ctl">'+tabs('sa',T.map(function(x){var l=A[x[0]];return [x[0],x[1]+' '+l.filter(function(u){return u[1]>=u[2]}).length+'/'+l.length]}),T[0][0])+'</div><div class="pw"><div id="army"></div></div>':'<div class="pw"><p class="pt-empty">L’armée s’affichera au prochain relevé.</p></div>')+'</div>';
 h+='</div></section>';
 root.innerHTML=h;
 document.querySelectorAll('.copytag').forEach(function(b){b.addEventListener('click',function(){var t=b.dataset.copy,s=b.querySelector('.tt');var ok=function(){s.textContent='Copié';setTimeout(function(){s.textContent=t},1400)};if(navigator.clipboard)navigator.clipboard.writeText(t).then(ok,function(){});})});
 /* onglets de la page, retenus dans l'adresse (#guerre…) */
 function go(id,push){if(!PG.some(function(x){return x[0]===id}))id='apercu';document.querySelectorAll('.pw-nav button').forEach(function(b){b.setAttribute('aria-selected',b.dataset.p===id)});document.querySelectorAll('.pw-p').forEach(function(x){x.hidden=x.dataset.p!==id});if(push)try{history.replaceState(null,'',location.pathname+location.search+(id==='apercu'?'':'#'+id))}catch(e){}window.dispatchEvent(new Event('resize'))}
 document.querySelectorAll('.pw-nav button').forEach(function(b){b.addEventListener('click',function(){go(b.dataset.p,1)})});
 go(location.hash.slice(1),0);
 document.querySelectorAll('[data-go]').forEach(function(b){b.addEventListener('click',function(){go(b.dataset.go,1);var n=document.querySelector('.pw-nav');if(n)n.scrollIntoView({behavior:'smooth',block:'start'})})});
 /* les chiffres de l'aperçu montent jusqu'à leur valeur à l'arrivée */
 if(!matchMedia('(prefers-reduced-motion: reduce)').matches)document.querySelectorAll('[data-n]').forEach(function(el){var to=+el.dataset.n;if(!(to>0))return;var t0=null;function st(t){if(!t0)t0=t;var k=Math.min(1,(t-t0)/900),e=1-Math.pow(1-k,3);el.textContent=nb(Math.round(to*e));if(k<1)requestAnimationFrame(st)}el.textContent='0';requestAnimationFrame(st)});
 var M='war',PD=30;
 function stats(){var lim=Date.now()/1000-PD*86400,A2=HT.atk.filter(function(a){return a[1]===M&&a[0]>=lim}).sort(function(a,b){return b[0]-a[0]}),D2=HT.def.filter(function(a){return a[1]===M&&a[0]>=lim}),el=document.getElementById('stats'),lab=M==='war'?'Guerre':'Ligue de clans';
  if(!A2.length){el.innerHTML=wg('En attaque','',null,'<p class="pt-empty">Pas d’attaque sur les '+PD+' derniers jours.</p>');return}
  function mo_(L,k){return L.reduce(function(a,x){return a+x[k]},0)/L.length}
  var n=A2.length,t3=A2.filter(function(x){return x[2]===3}).length;
  var chips='<p class="pw-l">Dernières attaques, la plus récente en premier</p><div class="pw-chips">'+A2.slice(0,20).map(function(x){return '<span class="c'+x[2]+'">'+x[2]+SV(!x[2])+'</span>'}).join('')+'</div>';
  var o=wg('En attaque','',[['Taux de triples',Math.round(t3/n*100)+'&nbsp;%',t3+' triple'+(t3>1?'s':'')],['Attaques',nb(n)],['Étoiles en moyenne',nb(Math.round(mo_(A2,2)*100)/100)],['Destruction',Math.round(mo_(A2,3))+'&nbsp;%']],chips);
  if(D2.length){var d3=D2.filter(function(x){return x[2]===3}).length;o+=wg('En défense','',[['Défenses',nb(D2.length)],['Étoiles concédées',nb(Math.round(mo_(D2,2)*100)/100)],['Destruction subie',Math.round(mo_(D2,3))+'&nbsp;%'],['Triples subis',Math.round(d3/D2.length*100)+'&nbsp;%']])}
  el.innerHTML=o}
 stats();tabsOn('sm',function(x){M=x;stats()});tabsOn('sp',function(x){PD=+x;stats()});
 var HFR={'Barbarian King':'Roi des barbares','Archer Queen':'Reine des archers','Grand Warden':'Grand gardien','Royal Champion':'Championne royale','Minion Prince':'Prince des sbires','Dragon Duke':'Duc dragon'};
 var DIR={heroes:'heroes',equip:'equipment',troops:'troops',siege:'troops',pets:'pets',spells:'spells'};
 function ico(cat,n){var c=String(n).toLowerCase().replace(/ /g,'_').replace(/[.?’']/g,''),u='https://assets.clashk.ing/'+DIR[cat]+'/'+c+(/^(heroes|troops|pets)$/.test(DIR[cat])?'/icon.webp':'.webp');return (window.__IMG||{})[u]||u}
 function lvl(u){return '<b>'+u[1]+'<span>/'+u[2]+'</span></b>'}
 function army(k){var l=A[k]||[],el=document.getElementById('army');
  if(k==='heroes'){el.className='pw-hr';el.innerHTML=l.map(function(u){return '<div class="pw-hrr"><img src="'+ico('heroes',u[0])+'" alt="'+esc(u[0])+'" loading="lazy"><div class="nm">'+esc(HFR[u[0]]||u[0])+lvl(u)+'</div>'+(u[3]&&u[3].length?'<div class="pw-eq">'+u[3].map(function(e){return '<div><img src="'+ico('equip',e[0])+'" alt="'+esc(e[0])+'" title="'+esc(e[0])+'" loading="lazy">'+e[1]+'</div>'}).join('')+'</div>':'')+'</div>'}).join('');return}
  el.className='pw-ar';el.innerHTML=l.map(function(u){return '<div class="pw-u'+(u[1]>=u[2]?' mx':'')+'" title="'+esc(u[0])+'"><img src="'+ico(k,u[0])+'" alt="'+esc(u[0])+'" loading="lazy">'+lvl(u)+'</div>'}).join('')}
 if(T.length){army(T[0][0]);tabsOn('sa',army)}
}).catch(function(){fail('Le portrait n’a pas pu être chargé. Réessaie dans un instant.')});
})();
/* barre du haut : le blason du clan remplace « Gravaen » quand on a dépassé l'en-tête, comme sur l'accueil */
(function(){var r=document.documentElement,t=false;
 fetch('data/clan.json',{cache:'no-store'}).then(function(x){return x.json()}).then(function(d){var hb=document.querySelector('.brand-b'),src=((d.clans||{}).main||{}).badge||(d.icons||{}).badge||d.badgeUrl;if(hb&&src){hb.onload=function(){hb.hidden=false;hb.parentNode.classList.add('has-b')};hb.src=src}}).catch(function(){});
 function u(){var hs=document.querySelector('.pt-hero');r.classList.toggle('past-hero',!!hs&&hs.getBoundingClientRect().bottom<90)}
 addEventListener('scroll',function(){if(t)return;t=true;requestAnimationFrame(function(){t=false;u()})},{passive:true});addEventListener('resize',u);setTimeout(u,300)})();
