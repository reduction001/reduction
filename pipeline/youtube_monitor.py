import datetime as dt, html, json, os, pathlib, re, urllib.parse, urllib.request
root=pathlib.Path(__file__).resolve().parents[1]
base=root/'public/dashboards'
folder=base/'data';folder.mkdir(exist_ok=True)
path=folder/'powerade-youtube.json'
key=os.environ.get('YOUTUBE_API_KEY')
if not key: raise SystemExit('YOUTUBE_API_KEY secret is missing')
def api(method,params):
    params['key']=key
    req=urllib.request.Request('https://www.googleapis.com/youtube/v3/'+method+'?'+urllib.parse.urlencode(params))
    with urllib.request.urlopen(req,timeout=30) as r: return json.load(r)
now=dt.datetime.now(dt.timezone.utc).isoformat()
data=json.loads(path.read_text()) if path.exists() else {}
try:
    result=api('search',{'part':'snippet','q':'Powerade commercial campaign','type':'video','order':'date','maxResults':20,'regionCode':'US','relevanceLanguage':'en','videoEmbeddable':'true'})
    ids=[i['id']['videoId'] for i in result.get('items',[]) if re.fullmatch(r'[A-Za-z0-9_-]{11}',i.get('id',{}).get('videoId',''))]
    if not ids: raise ValueError('No videos returned')
    details=api('videos',{'part':'snippet,contentDetails,status','id':','.join(ids)})
    videos=[]
    for item in details.get('items',[]):
        s=item['snippet']
        if 'powerade' not in (s.get('title','')+' '+s.get('description','')).casefold(): continue
        if not item.get('status',{}).get('embeddable'): continue
        videos.append({'id':item['id'],'title':s['title'],'channel':s['channelTitle'],'channel_id':s['channelId'],'published':s['publishedAt'],'url':'https://www.youtube.com/watch?v='+item['id'],'provenance':'Campaign discovery / unverified uploader'})
    if not videos: raise ValueError('No relevant embeddable videos returned')
    data={'updated':now,'videos':sorted(videos,key=lambda v:v['published'],reverse=True)[:6],'scope':'US search settings / English relevance preference, not verified North American campaign delivery'}
except Exception as e:
    data['error']='Refresh failed: '+type(e).__name__;data['attempted']=now
    if not data.get('videos'):
        path.write_text(json.dumps(data,indent=2));raise SystemExit(data['error'])
path.write_text(json.dumps(data,indent=2))
esc=lambda s:html.escape(str(s))
body='<section id="youtube-discovery"><p class="label">LATEST VIDEO / CAMPAIGN DISCOVERY</p><p class="status">Last successful collection: '+esc(data['updated'])+'</p>'
if data.get('error'): body+='<p>Latest attempt failed; previous collection retained.</p>'
body+='<div class="grid">'
for v in data['videos']:
    body+='<article class="card"><iframe title="'+esc(v['title'])+'" src="https://www.youtube-nocookie.com/embed/'+v['id']+'" loading="lazy" style="width:100%;aspect-ratio:16/9;border:0" allowfullscreen></iframe><h2>'+esc(v['title'])+'</h2><p>'+esc(v['channel'])+' / '+esc(v['published'][:10])+'</p><p class="status">'+esc(v['provenance'])+'</p><a href="'+esc(v['url'])+'" target="_blank" rel="noopener">Watch on YouTube ↗</a></article>'
body+='</div><p>Public video discovery, not proof of an active paid ad. English relevance and US search settings do not establish campaign geography. Weekly refresh.</p></section>'
page=base/'powerade/index.html'
text=page.read_text()
if 'id="youtube-discovery"' in text:
    text=re.sub(r'<section id="youtube-discovery">.*?</section>',lambda m:body,text,flags=re.S)
else:
    marker='<p>Verified commercials and campaign cards: collection pending.</p>'
    if marker not in text: raise SystemExit('Video insertion marker missing')
    text=text.replace(marker,body)
page.write_text(text)
print('Rendered '+str(len(data['videos']))+' discovered videos; secret never printed.')
