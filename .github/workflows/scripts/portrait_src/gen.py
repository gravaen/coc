"""Construit joueur.html à partir de index.html (mêmes styles, barre du haut et pied de page). Usage : python3 gen.py index.html joueur.html"""
import re,sys
import os
D=os.path.dirname(os.path.abspath(__file__))+'/'
src=open(sys.argv[1],encoding='utf-8').read()
head=src[:src.index('</head>')]
head=re.sub(r'<title>.*?</title>','<title>Profil · Gravaen</title>',head)
head=re.sub(r'<meta name="description"[^>]*>','<meta name="description" content="Profil d’un membre du staff de Gravaen : sa saison, sa ligue de clans, ses guerres et son armée."><meta name="robots" content="noindex">',head)
head=re.sub(r'<link rel="canonical"[^>]*>','',head)
head=head.replace('<link rel="preload" href="data/clan.json" as="fetch" crossorigin>','')
head=head.replace('</style>',open(D+'extra.css',encoding='utf-8').read()+'\n</style>',1) if head.count('</style>')==1 else head[:head.rindex('</style>')]+open(D+'extra.css',encoding='utf-8').read()+'\n'+head[head.rindex('</style>'):]
i=src.index('<header class="nav">');j=src.index('</header>',i)+9
nav=src[i:j].replace('href="#top"','href="./"').replace('aria-label="Gravaen, retour en haut de page"','aria-label="Gravaen, page d’accueil"')
nav=re.sub(r'href="#(vision|clans|staff|meilleurs)"',r'href="./#\1"',nav)
nav=nav.replace('<a href="./#staff">Organisation</a>','<a href="./#staff" aria-current="true">Organisation</a>')
fi=src.index('<footer>');fj=src.index('</footer>',fi)+9
menu='''<script>
const m=document.getElementById('menu'),l=document.getElementById('links'),mi=document.getElementById('mi');
function setMenu(o){l.classList.toggle('is-open',o);m.setAttribute('aria-expanded',o);m.setAttribute('aria-label',o?'Fermer le menu':'Ouvrir le menu');mi.setAttribute('d',o?'M6 6l12 12M18 6L6 18':'M4 7h16M4 12h16M4 17h16')}
m.onclick=()=>setMenu(!l.classList.contains('is-open'));l.onclick=e=>{if(e.target.closest('a'))setMenu(false)};
document.addEventListener('keydown',e=>{if(e.key==='Escape')setMenu(false)});
</script>'''
out=head+'</head>\n<body class="portrait">\n'+nav+'\n'+open(D+'body.html',encoding='utf-8').read()+src[fi:fj]+'\n'+menu+'\n<script>\n'+open(D+'script.js',encoding='utf-8').read()+'</script>\n</body>\n</html>\n'
open(sys.argv[2],'w',encoding='utf-8').write(out)
print(len(out))
