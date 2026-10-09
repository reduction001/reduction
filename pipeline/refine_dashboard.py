import datetime as dt,difflib,email.utils,html,json,pathlib,re,urllib.parse
root=pathlib.Path(__file__).resolve().parents[1];base=root/'public/dashboards'
esc=lambda x:html.escape(str(x))
load=lambda n:json.loads((base/'data'/n).read_text())
page=base/'powerade/index.html';text=page.read_text()
def replace(pattern,body):
    global text
    text,n=re.subn(pattern,lambda m:body,text,flags=re.S)
    if n!=1:raise ValueError('Unexpected page marker: '+pattern)
def date(x):
    try:return dt.datetime.fromisoformat(x.replace('Z','+00:00')).strftime('%b %d, %Y')
    except:return str(x)
def source(url,label):return '<a href="'+esc(url)+'" target="_blank" rel="noopener">'+esc(label)+' ↗</a>'
y=load('powerade-youtube.json')
body='<section id="youtube-discovery"><p class="label">LATEST OFFICIAL VIDEOS / POWERADE US</p><p class="status">Collected '+date(y.get('updated','Not available'))+' / weekly</p><div class="grid">'
for i,v in enumerate(y.get('videos',[])):
    if not re.fullmatch(r'[A-Za-z0-9_-]{11}',v['id']):continue
    body+='<article class="card video-card"'+(' hidden data-extra-video' if i>=3 else '')+'><button class="video-play" data-video="'+v['id']+'" aria-label="Play '+esc(v['title'])+'"><img src="https://i.ytimg.com/vi/'+v['id']+'/hqdefault.jpg" alt="" loading="lazy"><span>▶ Play video</span></button><h2>'+esc(v['title'])+'</h2><p>'+esc(v['channel'])+' / '+date(v['published'])+'</p>'+source(v['url'],'Watch on YouTube')+'</article>'
body+='</div>'
if len(y.get('videos',[]))>3:body+='<button id="show-videos" aria-expanded="false">View all '+str(len(y['videos']))+' videos</button>'
body+='<details><summary>Source &amp; methodology</summary><p>Official US channel uploads; English audio is uploader-declared metadata, not transcript verification. These videos do not establish active paid advertising. Playback may be unavailable; the YouTube link remains accessible.</p></details></section>'
replace(r'<section id="youtube-discovery">.*?</section>',body)
body='<section><p class="label">05 / SEARCH &amp; CONSUMER INTENT</p><p>Source-linked fallback. Embedded charts did not visibly render in QA, so empty chart frames have been removed. No search metrics are inferred.</p><div class="grid">'
for geo,name in [('US','United States'),('CA','Canada')]:
    query=urllib.parse.urlencode({'geo':geo,'q':'Powerade,Gatorade,BODYARMOR','date':'today 12-m'})
    related=urllib.parse.urlencode({'geo':geo,'q':'Powerade','date':'today 12-m'})
    body+='<article class="card"><p class="label">'+name+'</p><h2>Search signals</h2><p>'+source('https://trends.google.com/trends/explore?'+query,'Compare brand interest')+'</p><p>'+source('https://trends.google.com/trends/explore?'+related,'Explore related and rising queries')+'</p><p class="status">Live source access / not a collected feed. Related queries are not verified consumer questions or purchase intent.</p></article>'
body+='</div></section>'
replace(r'<section><p class="label">05 / SEARCH &amp; CONSUMER INTENT</p>.*?</section>',body)
n=load('powerade-signals.json')
body='<section><p class="label">04 / PR &amp; CULTURAL FOOTPRINT</p><p>Selected reporting / headline-based topic grouping, not verified story synthesis.</p><div class="grid">'
def normalized(title):return re.sub(r'[^a-z0-9 ]','',title.rsplit(' - ',1)[0].lower())
def news_time(item):
    try:return email.utils.parsedate_to_datetime(item['date']).timestamp()
    except:return 0
for brand in ['Powerade','Gatorade','BODYARMOR']:
    rows=sorted(n.get(brand,{}).get('items',[]),key=news_time,reverse=True);groups=[];related=[]
    for row in rows:
        title=normalized(row['title'])
        if brand.casefold() not in title or re.search(r'prime day|prime big deal|on sale|percent off|% off|complete list',row['title'],re.I):related.append(row);continue
        group=next((g for g in groups if difflib.SequenceMatcher(None,title,g['key']).ratio()>.72 or (brand=='Gatorade' and 'recall' in title and 'recall' in g['key'])),None)
        if group:group['items'].append(row)
        else:groups.append({'key':title,'items':[row]})
    body+='<article class="card"><h2>'+brand+'</h2><p class="status">Collected '+date(n.get(brand,{}).get('updated','Not available'))+'</p>'
    if n.get(brand,{}).get('error'):body+='<p>Latest refresh failed; earlier collection retained.</p>'
    def group_html(g):
        first=g['items'][0];out='<div class="news-item">'+source(first['url'],first['title'].rsplit(' - ',1)[0])+'<p class="status">'+esc(first['publisher'])+'</p>'
        if len(g['items'])>1:out+='<details><summary>'+str(len(g['items']))+' reports in this topic group</summary>'+''.join('<p>'+source(r['url'],r['publisher'])+'</p>' for r in g['items'])+'<p class="status">Topic grouping does not establish that every report describes the same incident.</p></details>'
        return out+'</div>'
    body+=''.join(group_html(g) for g in groups[:3])
    if not groups:body+='<p>No brand-specific headline groups in this collection.</p>'
    if groups[3:] or related:body+='<details><summary>More reporting and related coverage</summary>'+''.join(group_html(g) for g in groups[3:])+''.join('<p>'+source(r['url'],r['title'])+'</p>' for r in related)+'</details>'
    body+='</article>'
body+='</div><details><summary>Source &amp; methodology</summary><p>Weekly English news discovery using US settings. Brand-name headline filtering can miss relevant stories. Similar headlines are grouped heuristically, and Gatorade recall coverage is grouped as a topic. Parent/category and shopping results remain under related coverage. Not comprehensive North American reporting.</p></details></section>'
replace(r'<section><p class="label">04 / PR &amp; CULTURAL FOOTPRINT</p>.*?</section>',body)
e=load('powerade-editorial.json');f=e['financials'];sec=load('powerade-parent-financials.json')
body='<article class="card"><h2>Financial snapshot</h2><p class="label">LATEST REVIEWED RELEASE / '+esc(f['period'])+'</p><p class="metric">$'+esc(f['parent_global_net_revenue_usd_billions'])+'bn</p><p>Coca-Cola global net revenue / +'+esc(f['parent_global_net_revenue_growth_percent'])+'% year over year.</p><p>Powerade global volume +'+esc(f['powerade_global_unit_case_volume_growth_percent'])+'%; Coca-Cola sports-drinks portfolio volume +'+esc(f['coca_cola_sports_drinks_global_unit_case_volume_growth_percent'])+'%.</p>'+source(f['source'],'Reviewed earnings release')+'<details><summary>Filed parent revenue &amp; scope</summary><p class="status">SEC collection '+date(sec.get('updated','Not available'))+'</p>'
for kind,row in sec.get('periods',{}).items():body+='<p>'+esc(kind.title())+': '+esc(row['start'])+'–'+esc(row['end'])+' / $'+esc(f"{row['val']/1e9:,.2f}")+'bn.</p>'
q=sec.get('periods',{}).get('quarter',{})
if q.get('filed','')<f['published_at']:body+='<p>Freshness notice: the SEC collector returned an older quarterly period than the reviewed release. This is the latest available fact in this dataset, not the latest reported quarter.</p>'
if sec.get('error'):body+='<p>Latest SEC attempt failed; prior facts retained.</p>'
body+='<p>'+esc(f['limitations'])+'</p>'+source(sec.get('source','https://www.sec.gov/edgar/browse/?CIK=0000021344'),'SEC dataset')+'</details></article>'
replace(r'<article class="card"><h2>Financial snapshot</h2>.*?</article>',body)
body='<section class="lens" id="reduction-lens" aria-labelledby="lens-title"><p class="label">THE REDUCTION LENS / THE CONSEQUENCE</p><h2 id="lens-title">One brand. More than one performance story.</h2><p>The sourced global platform centers on permission to pause. The monitored US uploads use Power Your Legacy and It Takes More. The question is how these expressions connect—not whether different lines alone prove a fragmented strategy.</p><div class="grid"><div><p class="label">WHAT WE SEE</p><p>A global recovery platform alongside US creative framed around legacy and competitive stakes.</p></div><div><p class="label">THE STRATEGIC QUESTION</p><p>Does the work make hydration, recovery and ambition feel like one coherent view of performance?</p></div><div><p class="label">WHAT TO WATCH</p><p>Track whether new US executions connect the product benefit to that worldview, rather than adding another disconnected line.</p></div></div><details><summary>Evidence &amp; limitations</summary><p>Reduction editorial hypothesis based on the reviewed platform source and official upload titles, not a full creative-content analysis or a finding of campaign effectiveness.</p>'+source(e['profile']['sources'][1],'Global platform announcement')+'<p>'+source(y.get('channel_source','https://www.youtube.com/user/PoweradeUS'),'Official US creative source')+'</p></details></section>'
replace(r'<section class="lens".*?</section>',body)
if 'id="section-jumps"' not in text:text=text.replace('<section><p class="label">01 / EXECUTIVE SNAPSHOT</p>','<nav id="section-jumps" aria-label="Dashboard sections"><a href="#youtube-discovery">The work</a><a href="#reduction-lens">Jump to the Lens ↓</a></nav><section><p class="label">01 / EXECUTIVE SNAPSHOT</p>')
if '/dashboards/refinements.css' not in text:text=text.replace('</head>','<link rel="stylesheet" href="/dashboards/refinements.css"></head>')
if '/dashboards/refinements.js' not in text:text=text.replace('</body>','<script src="/dashboards/refinements.js" defer></script></body>')
reviewed=dt.date.fromisoformat(e['reviewed_at']);age=(dt.datetime.now(dt.timezone.utc).date()-reviewed).days
text=re.sub(r'BUILD PREVIEW / DATA CONNECTIONS PENDING(?: / EDITORIAL[^<]*)?','BUILD PREVIEW / NOT PUBLISHED / EDITORIAL REVIEW '+esc(e['reviewed_at'])+(' — REVIEW OVERDUE' if age>35 else ''),text)
text=re.sub(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?\+00:00',lambda m:date(m[0]),text)
page.write_text(text)
(base/'refinements.css').write_text('''body{font-size:16px}.grid{align-items:start}.card{min-height:0}.card p{font-size:14px}.status{font-size:12px;line-height:1.5;overflow-wrap:anywhere}.metric{font-size:38px!important;letter-spacing:-.05em}.video-play{width:100%;aspect-ratio:16/9;position:relative;display:block;overflow:hidden;border:1px solid #ffffff30;background:#17232c;color:white;padding:0;cursor:pointer;border-radius:7px}.video-play img{width:100%;height:100%;object-fit:cover}.video-play span{position:absolute;left:12px;bottom:12px;background:#080b0ee6;padding:8px 12px;border-radius:4px}.video-card[hidden]{display:none}.news-item{padding:15px 0;border-top:1px solid #ffffff18}details{margin-top:18px;font-size:13px}summary{cursor:pointer;color:#a9bdc8;padding:8px 0}button{font:inherit}#show-videos{margin-top:18px;background:#10171c;border:1px solid #ceff7250;color:#ceff72;padding:12px 18px;border-radius:6px}#section-jumps{justify-content:flex-start;margin:25px 0;gap:22px;flex-wrap:wrap}a:focus-visible,button:focus-visible,summary:focus-visible{outline:2px solid #ceff72;outline-offset:4px}.lens{scroll-margin-top:25px}.lens>p:not(.label){font-size:18px;max-width:900px}.lens details{max-width:900px}@media(max-width:750px){.card{padding:22px}.lens h2{font-size:40px}.lens>p:not(.label){font-size:16px}}''')
(base/'refinements.js').write_text('''document.querySelectorAll('.video-play').forEach(b=>{const img=b.querySelector('img');img.addEventListener('error',()=>{img.hidden=true;b.querySelector('span').textContent='▶ Play official video'});b.addEventListener('click',()=>{const id=b.dataset.video;if(!/^[A-Za-z0-9_-]{11}$/.test(id))return;const f=document.createElement('iframe');f.src='https://www.youtube-nocookie.com/embed/'+id+'?autoplay=1';f.title=b.getAttribute('aria-label');f.allow='autoplay; encrypted-media; picture-in-picture';f.allowFullscreen=true;f.style='width:100%;aspect-ratio:16/9;border:0';b.replaceWith(f)})});const all=document.querySelector('#show-videos');if(all)all.addEventListener('click',()=>{const open=all.getAttribute('aria-expanded')!=='true';document.querySelectorAll('[data-extra-video]').forEach(v=>v.hidden=!open);all.setAttribute('aria-expanded',String(open));all.textContent=open?'Show fewer videos':'View all videos'});''')
print('Applied dashboard presentation. No workflow edits or deployment performed.')
