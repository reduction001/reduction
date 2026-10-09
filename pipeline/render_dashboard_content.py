import html,json,pathlib,re
base=pathlib.Path(__file__).resolve().parents[1]/'public/dashboards'
esc=lambda x:html.escape(str(x))
def links(urls):
    return '<p class="status">Sources: '+' · '.join('<a href="'+esc(u)+'" target="_blank" rel="noopener">'+esc(__import__('urllib.parse',fromlist=['urlparse']).urlparse(u).netloc)+'</a>' for u in urls if u.startswith('https://'))+'</p>'
def replace(text,pattern,body):
    text,n=re.subn(pattern,lambda m:body,text,flags=re.S)
    if n!=1:raise ValueError('Expected exactly one content marker: '+pattern)
    return text
d=json.loads((base/'data/powerade-editorial.json').read_text())
p=d['profile'];f=d['financials'];lead=d['leadership'];lens=d['lens']
page=base/'powerade/index.html';text=page.read_text()
body='<article class="card"><h2>Brand identity</h2><p>'+esc(p['name'])+' / '+esc(p['parent'])+'</p><p>'+esc(p['us_proposition'])+'</p><p>Global platform: '+esc(p['global_platform'])+'</p><p class="status">'+esc(p['platform_scope'])+'</p><p>Parent CEO: '+esc(lead['parent_ceo'])+'</p><p>North America leadership: '+esc(lead['north_america_interim'])+' (interim); '+esc(lead['north_america_incoming'])+' announced effective '+esc(lead['incoming_effective'])+'.</p><p class="status">Leadership snapshot reviewed '+esc(d['reviewed_at'])+'. '+esc(lead['scope'])+'</p><p>Separately stated brand mission and values: not verified.</p>'+links(p['sources'])+'</article>'
text=replace(text,r'<article class="card"><h2>Brand identity</h2>.*?</article>',body)
body='<article class="card"><h2>Financial snapshot</h2><p class="label">'+esc(f['period'])+' / GLOBAL</p><p>Coca-Cola net revenue: $'+esc(f['parent_global_net_revenue_usd_billions'])+'bn / +'+esc(f['parent_global_net_revenue_growth_percent'])+'% year over year.</p><p>Powerade unit-case volume: +'+esc(f['powerade_global_unit_case_volume_growth_percent'])+'%.</p><p>Coca-Cola sports-drinks portfolio volume: +'+esc(f['coca_cola_sports_drinks_global_unit_case_volume_growth_percent'])+'%.</p><p>Powerade revenue, North American sales and total-market sales: not established from this release.</p><p class="status">'+esc(f['limitations'])+'</p>'+links([f['source']])+'</article>'
text=replace(text,r'<article class="card"><h2>Financial snapshot</h2>.*?</article>',body)
body='<section class="lens" aria-labelledby="lens-title"><p class="label">THE REDUCTION LENS / THE CONSEQUENCE</p><h2 id="lens-title">'+esc(lens['headline'])+'</h2><p>'+esc(lens['interpretation'])+'</p><div class="grid">'
for label,key in [('WHAT CHANGED','what_changed'),('WHY IT MATTERS','why_it_matters'),('THE IMPLICATION','implication')]:body+='<div><p class="label">'+label+'</p><p>'+esc(lens[key])+'</p></div>'
body+='</div><p class="status">Reviewed '+esc(d['reviewed_at'])+' / '+esc(lens['limitations'])+'</p>'+links(lens['sources'])+'</section>'
text=replace(text,r'<section class="lens".*?</section>',body)
page.write_text(text)
registry=base/'brands.json'
if not registry.exists():registry.write_text(json.dumps([{'slug':'powerade','name':'Powerade','enabled':True}],indent=2))
brands=json.loads(registry.read_text());seen=set();cards=[]
for b in brands:
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',b['slug']) or b['slug'] in seen:raise ValueError('Invalid or duplicate slug')
    seen.add(b['slug'])
    if not b.get('enabled') or not (base/b['slug']/'index.html').exists():continue
    cards.append('<a class="card" href="/dashboards/'+esc(b['slug'])+'/"><p class="label">SIGNAL BOARD</p><h2>'+esc(b['name'])+'</h2><p>North America / English</p><span>Open signal board ↗</span></a>')
directory=base/'index.html';directory.write_text(replace(directory.read_text(),r'<div class="grid">.*?</div>','<div class="grid">'+''.join(cards)+'</div>'))
admin=base/'admin';admin.mkdir(exist_ok=True)
admin.joinpath('index.html').write_text('''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Brand management / reduction</title><link rel="stylesheet" href="/dashboards/dashboard.css"></head><body><main><p class="label">CONFIGURATION / NOT A PUBLIC WRITE API</p><h1>manage</h1><p>Edit directory visibility here and export the configuration for Perplexity to apply. Adding a brand also requires its detail page and collectors. Removing a directory entry does not delete its page.</p><p><a href="https://github.com/reduction001/reduction/edit/feature/brand-dashboards/public/dashboards/brands.json" target="_blank" rel="noopener">Authenticated browser fallback: edit in GitHub ↗</a></p><label for="config">Brand registry</label><textarea id="config" style="display:block;width:100%;min-height:300px;background:#10171c;color:white"></textarea><button id="export">Validate and export</button><p id="status" role="status"></p><p>No API keys or tokens belong in this editor. Export does not publish changes.</p><a href="/dashboards/">Back to dashboards</a></main><script>fetch('/dashboards/brands.json').then(r=>r.json()).then(d=>document.querySelector('#config').value=JSON.stringify(d,null,2)).catch(()=>document.querySelector('#status').textContent='Could not load registry.');document.querySelector('#export').onclick=()=>{try{const d=JSON.parse(document.querySelector('#config').value);if(!Array.isArray(d))throw Error('Expected an array');const seen=new Set();for(const b of d){if(!b.name||!/^([a-z0-9]+-)*[a-z0-9]+$/.test(b.slug)||typeof b.enabled!=='boolean'||seen.has(b.slug))throw Error('Check names, unique slugs and enabled flags');seen.add(b.slug)}const u=URL.createObjectURL(new Blob([JSON.stringify(d,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=u;a.download='brands.json';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);document.querySelector('#status').textContent='Validated and exported; not published.'}catch(e){document.querySelector('#status').textContent=e.message}};</script></body></html>''')
print('Rendered sourced profile, financial snapshot, Lens, directory and export admin. No deployment performed.')
