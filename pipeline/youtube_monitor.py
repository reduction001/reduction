import datetime as dt, html, json, os, pathlib, re, urllib.parse, urllib.request
base=pathlib.Path(__file__).resolve().parents[1]/'public/dashboards'
folder=base/'data';folder.mkdir(exist_ok=True)
path=folder/'powerade-youtube.json'
key=os.environ.get('YOUTUBE_API_KEY')
if not key:raise SystemExit('YOUTUBE_API_KEY missing')
def api(method,params):
    params=dict(params,key=key)
    with urllib.request.urlopen('https://www.googleapis.com/youtube/v3/'+method+'?'+urllib.parse.urlencode(params),timeout=30) as r:return json.load(r)
now=dt.datetime.now(dt.timezone.utc).isoformat()
old=json.loads(path.read_text()) if path.exists() else {}
channel_id=None
try:
    channels=api('channels',{'part':'snippet,contentDetails','forHandle':'PoweradeUS'}).get('items',[])
    if not channels:channels=api('channels',{'part':'snippet,contentDetails','forUsername':'PoweradeUS'}).get('items',[])
    if len(channels)!=1:raise ValueError('Official channel resolution failed')
    channel=channels[0];channel_id=channel['id']
    uploads=channel['contentDetails']['relatedPlaylists']['uploads']
    entries=api('playlistItems',{'part':'contentDetails','playlistId':uploads,'maxResults':50}).get('items',[])
    ids=[e['contentDetails']['videoId'] for e in entries if re.fullmatch(r'[A-Za-z0-9_-]{11}',e['contentDetails'].get('videoId',''))]
    if not ids:raise ValueError('No uploads returned')
    items=api('videos',{'part':'snippet,status','id':','.join(ids)}).get('items',[])
    videos=[];review=[]
    for v in items:
        s=v['snippet'];status=v.get('status',{})
        if s['channelId']!=channel_id or status.get('privacyStatus')!='public':continue
        audio=s.get('defaultAudioLanguage','').lower()
        metadata=s.get('defaultLanguage','').lower()
        if not audio.startswith('en'):
            review.append({'id':v['id'],'title':s['title'],'audio_language':audio or 'unknown','metadata_language':metadata or 'unknown','reason':'English audio not established by metadata'})
            continue
        videos.append({'id':v['id'],'title':s['title'],'channel':s['channelTitle'],'channel_id':channel_id,'published':s['publishedAt'],'url':'https://www.youtube.com/watch?v='+v['id'],'embeddable':status.get('embeddable',False),'audio_language':audio,'provenance':'Official POWERADE US upload / English audio metadata'})
    data={'updated':now,'policy':'official-us-english-audio-v2','channel_id':channel_id,'channel_source':'https://www.youtube.com/user/PoweradeUS','videos':sorted(videos,key=lambda x:x['published'],reverse=True)[:6],'review_queue':review,'scope':'Official US channel uploads; not evidence of active paid advertising. Audio language is uploader-declared metadata, not transcript verification.'}
except Exception as e:
    data={'policy':'official-us-english-audio-v2','attempted':now,'error':type(e).__name__,'videos':[]}
    if old.get('policy')=='official-us-english-audio-v2':
        data=dict(old,error=type(e).__name__,attempted=now)
path.write_text(json.dumps(data,indent=2))
esc=lambda x:html.escape(str(x))
body='<section id="youtube-discovery"><p class="label">LATEST OFFICIAL VIDEOS / POWERADE US</p><p class="status">Last successful collection: '+esc(data.get('updated','Not yet available'))+'</p>'
if data.get('error'):body+='<p>Refresh failed. Only previously qualified official uploads can be retained.</p>'
body+='<div class="grid">'
for v in data['videos']:
    if not re.fullmatch(r'[A-Za-z0-9_-]{11}',v['id']):continue
    body+='<article class="card">'
    if v['embeddable']:body+='<iframe title="'+esc(v['title'])+'" src="https://www.youtube-nocookie.com/embed/'+v['id']+'" loading="lazy" style="width:100%;aspect-ratio:16/9;border:0" allowfullscreen></iframe>'
    body+='<h2>'+esc(v['title'])+'</h2><p>'+esc(v['channel'])+' / '+esc(v['published'][:10])+'</p><p class="status">'+esc(v['provenance'])+'</p><a href="'+esc(v['url'])+'" target="_blank" rel="noopener">Watch on YouTube ↗</a></article>'
body+='</div>'
if not data['videos']:body+='<p>No uploads passed the official-channel and English-audio metadata checks. Unknown-language uploads are held for review, not displayed.</p>'
body+='<p>Weekly collection. Published brand content, not proof of active paid ads. US channel provenance does not prove where a campaign ran.</p></section>'
page=base/'powerade/index.html';text=page.read_text()
text,count=re.subn(r'<section id="youtube-discovery">.*?</section>',lambda m:body,text,flags=re.S)
if count!=1:raise SystemExit('YouTube gallery marker missing')
page.write_text(text)
print('Qualified official videos:',len(data['videos']),'Review queue:',len(data.get('review_queue',[])))
if data.get('error'):raise SystemExit('Official video collection failed; sanitized output saved locally')
