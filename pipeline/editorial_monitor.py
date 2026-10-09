import datetime as dt,email.utils,hashlib,html,json,pathlib,re,urllib.parse,urllib.request
root=pathlib.Path(__file__).resolve().parents[1];base=root/'public/dashboards';now=dt.datetime.now(dt.timezone.utc)
esc=lambda x:html.escape(str(x))
def load(path,default):return json.loads(path.read_text()) if path.exists() else default
def save(path,data):path.write_text(json.dumps(data,indent=2))
epath=base/'data/powerade-editorial.json';e=load(epath,{})
if e['lens']['headline']=='Make the pause a platform. Not just a line.':
    e['lens'].update({'headline':'One brand. More than one performance story.','interpretation':'The sourced global platform centers on permission to pause. The monitored US uploads use Power Your Legacy and It Takes More. The question is how these expressions connect—not whether different lines alone prove a fragmented strategy.','what_changed':'A global recovery platform alongside US creative framed around legacy and competitive stakes.','why_it_matters':'Does the work make hydration, recovery and ambition feel like one coherent view of performance?','implication':'Track whether new US executions connect the product benefit to that worldview, rather than adding another disconnected line.','limitations':'Reduction editorial hypothesis based on the reviewed platform source and official upload titles, not a full creative-content analysis or a finding of campaign effectiveness.','sources':[e['profile']['sources'][1],'https://www.youtube.com/user/PoweradeUS']})
e['lens'].setdefault('reviewed_at',e['reviewed_at']);save(epath,e)
qpath=base/'data/powerade-review-queue.json';queue=load(qpath,{'items':[]});existing={i['id'] for i in queue['items']}
reviewed=dt.date.fromisoformat(e['reviewed_at'])
def add(kind,title,url,reason,published=None,fingerprint=''):
    if not url.startswith('https://'):return
    key=hashlib.sha256((kind+'|'+url+'|'+fingerprint).encode()).hexdigest()[:24]
    if key in existing:return
    existing.add(key);queue['items'].append({'id':key,'type':kind,'title':title,'url':url,'reason':reason,'published_at':published,'discovered_at':now.isoformat(),'status':'pending'})
def is_new(value):
    try:return dt.datetime.fromisoformat(value.replace('Z','+00:00')).date()>reviewed
    except:
        try:return email.utils.parsedate_to_datetime(value).date()>reviewed
        except:return True
signals=load(base/'data/powerade-signals.json',{})
for brand in ['Powerade','Gatorade','BODYARMOR']:
    for item in signals.get(brand,{}).get('items',[]):
        if is_new(item.get('date','')):add('news',item['title'],item['url'],'Published after the recorded editorial review date, or publication date could not be established. Requires source review.',item.get('date'))
y=load(base/'data/powerade-youtube.json',{})
for v in y.get('videos',[]):
    if is_new(v.get('published','')):add('official_video',v['title'],v['url'],'Official upload after the editorial review date. Metadata is evidence of publication, not campaign effectiveness.',v.get('published'))
statepath=root/'pipeline/editorial-source-state.json';state=load(statepath,{})
urls=set(e['profile']['sources']+[e['financials']['source'],e['leadership']['source']])
allowed={'www.powerade.com','www.coca-colacompany.com','investors.coca-colacompany.com'}
for url in sorted(urls):
    parsed=urllib.parse.urlparse(url)
    if parsed.scheme!='https' or parsed.netloc not in allowed:continue
    old=state.get(url,{})
    if old.get('checked_at') and (now-dt.datetime.fromisoformat(old['checked_at'])).days<28:continue
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'ReductionMonitor/1.0 (https://reduction.nyc)'})
        with urllib.request.urlopen(req,timeout=25) as response:raw=response.read(2000000).decode('utf-8',errors='replace')
        raw=re.sub(r'<script\b.*?</script>|<style\b.*?</style>',' ',raw,flags=re.S|re.I)
        plain=html.unescape(re.sub(r'<[^>]+>',' ',raw));plain=' '.join(plain.split())
        if len(plain)<100:raise ValueError('Insufficient reference text')
        digest=hashlib.sha256(plain.encode()).hexdigest()
        if old.get('digest') and old['digest']!=digest:add('reference_change','Official reference text changed',url,'Text fingerprint changed; this may include navigation or banners and is not a verified factual change.',fingerprint=digest)
        state[url]={'digest':digest,'checked_at':now.isoformat(),'initial_baseline':not bool(old.get('digest'))}
    except Exception as err:
        state[url]=dict(old,last_attempt=now.isoformat(),error=type(err).__name__)
        add('reference_check','Official reference check unavailable',url,'Collection could not establish a usable reference baseline. Retain reviewed content; investigate the source.')
save(statepath,state)
queue['checked_at']=now.isoformat();queue['policy']='Discovery only. Review dates and approved claims are not automatically changed. Date comparisons use the recorded review day.'
save(qpath,queue)
pending=sum(i.get('status')=='pending' for i in queue['items'])
hpath=base/'data/powerade-health.json';health=load(hpath,{})
health['editorial_review']={'reviewed_at':e['reviewed_at'],'lens_reviewed_at':e['lens']['reviewed_at'],'pending_items':pending,'overdue':(now.date()-reviewed).days>35,'automatic_approval':False}
save(hpath,health)
refiner=root/'pipeline/refine_dashboard.py';code=refiner.read_text()
if "lens=e['lens']" not in code:
    start=code.index('body=\'<section class="lens"')
    end=code.index("replace(r'<section class=\"lens\"",start) if "replace(r'<section class=\"lens\"" in code[start:] else code.index("replace(r'<section class="+'"lens"',start)
    end=code.index('\n',end)+1
    replacement='''lens=e['lens']
body='<section class="lens" id="reduction-lens" aria-labelledby="lens-title"><p class="label">THE REDUCTION LENS / THE CONSEQUENCE</p><h2 id="lens-title">'+esc(lens['headline'])+'</h2><p>'+esc(lens['interpretation'])+'</p><div class="grid">'
for label,key in [('WHAT WE SEE','what_changed'),('THE STRATEGIC QUESTION','why_it_matters'),('WHAT TO WATCH','implication')]:body+='<div><p class="label">'+label+'</p><p>'+esc(lens[key])+'</p></div>'
body+='</div><details><summary>Evidence &amp; limitations</summary><p>Reviewed '+esc(lens.get('reviewed_at',e['reviewed_at']))+' / '+esc(lens['limitations'])+'</p>'+''.join('<p>'+source(u,'Supporting source')+'</p>' for u in lens['sources'])+'</details></section>'
replace(r'<section class="lens".*?</section>',body)
'''
    code=code[:start]+replacement+code[end:]
if 'health_panel=' not in code:
    marker='page.write_text(text)'
    insertion='''health_report=load('powerade-health.json')
review=health_report.get('editorial_review',{})
health_panel='<aside id="source-health"><details><summary>Source health / '+str(review.get('pending_items',0))+' items awaiting editorial review</summary><p>Editorial reviewed '+esc(review.get('reviewed_at',e['reviewed_at']))+(' — review overdue' if review.get('overdue') else '')+'. Discovery does not approve new claims.</p><ul>'
for label,value in health_report.get('sources',{}).items():health_panel+='<li>'+esc(label)+' / '+esc(value.get('state','unknown'))+'</li>'
health_panel+='</ul><p><a href="/dashboards/admin/editorial.html">Review queue &amp; editorial editor ↗</a></p></details></aside>'
if 'id="source-health"' in text:text=re.sub(r'<aside id="source-health">.*?</aside>',lambda m:health_panel,text,flags=re.S)
else:text=text.replace('<section><p class="label">01 / EXECUTIVE SNAPSHOT</p>',health_panel+'<section><p class="label">01 / EXECUTIVE SNAPSHOT</p>',1)
'''
    if code.count(marker)!=1:raise ValueError('Unexpected page-write marker')
    code=code.replace(marker,insertion+marker)
refiner.write_text(code);compile(code,str(refiner),'exec')
admin=base/'admin';admin.mkdir(exist_ok=True)
items=''.join('<details><summary>'+esc(i['type'])+' / '+esc(i['title'])+'</summary><p>'+esc(i['reason'])+'</p><a href="'+esc(i['url'])+'" target="_blank" rel="noopener">Review source ↗</a></details>' for i in queue['items'] if i.get('status')=='pending')
content='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Editorial review / reduction</title><link rel="stylesheet" href="/dashboards/dashboard.css"></head><body><main><p class="label">REVIEW / NEVER AUTO-APPROVED</p><h1>editorial</h1><p>Discovery queue. Review sources before changing claims. Exporting does not publish, save to GitHub, approve queue items, or advance review dates.</p>QUEUE<p><a href="https://github.com/reduction001/reduction/edit/feature/brand-dashboards/public/dashboards/data/powerade-editorial.json">Authenticated GitHub content editor ↗</a></p><label for="editorial">Reviewed content JSON</label><textarea id="editorial" style="display:block;width:100%;min-height:450px;background:#10171c;color:white"></textarea><button id="export">Validate &amp; export</button><p id="status" role="status"></p><a href="/dashboards/admin/">Brand management</a></main><script>fetch('/dashboards/data/powerade-editorial.json').then(r=>r.json()).then(d=>document.querySelector('#editorial').value=JSON.stringify(d,null,2));document.querySelector('#export').onclick=()=>{try{const d=JSON.parse(document.querySelector('#editorial').value);if(!/^\d{4}-\d{2}-\d{2}$/.test(d.reviewed_at))throw Error('Review date required');for(const k of ['headline','interpretation','what_changed','why_it_matters','implication','limitations'])if(!d.lens[k])throw Error('Lens field missing: '+k);if(!d.lens.sources.length||d.lens.sources.some(u=>!u.startsWith('https://')))throw Error('HTTPS supporting sources required');if(/AIza[0-9A-Za-z_-]{30,}/.test(JSON.stringify(d)))throw Error('Never include API keys');const u=URL.createObjectURL(new Blob([JSON.stringify(d,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=u;a.download='powerade-editorial.json';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);document.querySelector('#status').textContent='Validated and exported. No publication or approval performed.'}catch(e){document.querySelector('#status').textContent=e.message}};</script></body></html>'''.replace('QUEUE',items or '<p>No pending items from the available discovery data.</p>',1)
(admin/'editorial.html').write_text(content)
index=admin/'index.html';text=index.read_text()
if '/dashboards/admin/editorial.html' not in text:text=text.replace('</main>','<p><a href="/dashboards/admin/editorial.html">Editorial review queue ↗</a></p></main>')
index.write_text(text)
print('Editorial monitoring completed:',pending,'pending items. Review dates preserved; no deployment.')
