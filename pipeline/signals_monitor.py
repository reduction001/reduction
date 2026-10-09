import datetime as dt, html, json, pathlib, re, urllib.parse, urllib.request, xml.etree.ElementTree as ET
base=pathlib.Path(__file__).resolve().parents[1]/'public/dashboards'
folder=base/'data';folder.mkdir(exist_ok=True)
path=folder/'powerade-signals.json'
data=json.loads(path.read_text()) if path.exists() else {}
now=dt.datetime.now(dt.timezone.utc);stamp=now.isoformat()
def get(url):
    req=urllib.request.Request(url,headers={'User-Agent':'ReductionMonitor/1.0 (https://reduction.nyc)'})
    with urllib.request.urlopen(req,timeout=30) as r:return r.read()
esc=lambda x:html.escape(str(x))
for brand in ['Powerade','Gatorade','BODYARMOR']:
    try:
        q=urllib.parse.urlencode({'q':brand+' sports drink when:7d','hl':'en-US','gl':'US','ceid':'US:en'})
        root=ET.fromstring(get('https://news.google.com/rss/search?'+q))
        items=[];seen=set()
        for row in root.findall('./channel/item'):
            title=row.findtext('title','');url=row.findtext('link','')
            if title.casefold() in seen or not url.startswith('https://'):continue
            seen.add(title.casefold());items.append({'title':title,'url':url,'date':row.findtext('pubDate',''),'publisher':row.findtext('source','')})
        data[brand]={'updated':stamp,'items':items[:12]}
    except Exception as e:
        data.setdefault(brand,{'items':[]})['error']=type(e).__name__
w=data.get('wiki',{})
if not w.get('updated') or (now-dt.datetime.fromisoformat(w['updated'])).days>=28:
    try:
        end=now.date()-dt.timedelta(days=2);start=end-dt.timedelta(days=59)
        url=f'https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia.org/all-access/user/Powerade/daily/{start:%Y%m%d}/{end:%Y%m%d}'
        rows=json.loads(get(url))['items']
        if len(rows)!=60:raise ValueError('Incomplete period')
        recent=sum(r['views'] for r in rows[30:]);previous=sum(r['views'] for r in rows[:30])
        data['wiki']={'updated':stamp,'end':str(end),'views':recent,'change':round(100*(recent/previous-1),1) if previous else None,'daily':rows}
    except Exception as e:data.setdefault('wiki',{})['error']=type(e).__name__
path.write_text(json.dumps(data,indent=2))
page=base/'powerade/index.html';text=page.read_text()
body='<section><p class="label">04 / PR &amp; CULTURAL FOOTPRINT</p><p>Weekly English news discovery. US search settings do not guarantee North American-only coverage. Headlines are source-linked, not editorially verified summaries.</p><div class="grid">'
for brand in ['Powerade','Gatorade','BODYARMOR']:
    n=data.get(brand,{})
    body+='<article class="card"><h2>'+brand+'</h2><p class="status">Last success: '+esc(n.get('updated','Not available'))+'</p>'
    if n.get('error'):body+='<p>Refresh failed; prior items retained.</p>'
    body+='<ul>'+''.join('<li><a href="'+esc(i['url'])+'" target="_blank" rel="noopener">'+esc(i['title'])+'</a><p class="status">'+esc(i['publisher'])+' / '+esc(i['date'])+'</p></li>' for i in n.get('items',[]))+'</ul></article>'
body+='</div></section>'
text,count=re.subn(r'<section><p class="label">04 / PR &amp; CULTURAL FOOTPRINT</p>.*?</section>',lambda m:body,text,flags=re.S)
if count!=1:raise SystemExit('PR insertion marker missing')
w=data.get('wiki',{})
if 'views' in w:
    body='<article class="card"><h2>Attention pulse</h2><p>'+esc(f"{w['views']:,}")+' views / 30 days ending '+esc(w['end'])+'</p>'
    if w['change'] is not None:body+='<p>'+esc(w['change'])+'% versus preceding 30 days.</p>'
    body+='<p class="status">Global English Wikipedia attention, not regional search demand. Monthly refresh. Last success: '+esc(w['updated'])+'</p>'
    if w.get('error'):body+='<p>Latest attempt failed; prior data retained.</p>'
    body+='</article>'
    text=re.sub(r'<article class="card"><h2>Attention pulse</h2>.*?</article>',lambda m:'<article class="card">'+body+'</article>',text,flags=re.S)
page.write_text(text)
failed=[b for b in ['Powerade','Gatorade','BODYARMOR','wiki'] if data.get(b,{}).get('error')]
print('Failed sources:',','.join(failed) or 'none')
if len(failed)==4:raise SystemExit('All collection sources failed')
