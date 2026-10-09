import html,json,pathlib,re,urllib.parse
base=pathlib.Path(__file__).resolve().parents[1]/'public/dashboards'
esc=lambda x:html.escape(str(x))
page=base/'powerade/index.html';text=page.read_text()
channels={'Powerade':[('Facebook','https://www.facebook.com/PoweradeUS/videos/'),('TikTok','https://www.tiktok.com/@powerade_us'),('YouTube','https://www.youtube.com/user/PoweradeUS')],'Gatorade':[('Instagram','https://www.instagram.com/gatorade/'),('TikTok','https://www.tiktok.com/@gatorade?lang=en'),('YouTube','https://www.youtube.com/gatorade')],'BODYARMOR':[('Instagram','https://www.instagram.com/drinkbodyarmor/'),('TikTok','https://www.tiktok.com/@drinkbodyarmor'),('YouTube','https://www.youtube.com/user/DrinkBODYARMOR')]}
body='<section><p class="label">03 / BRAND &amp; COMPETITOR SOCIAL</p><p>Official-channel access / source-link fallback. These cards are not collected post streams. Platform pages can require sign-in.</p><div class="grid">'
for brand,rows in channels.items():
    body+='<article class="card"><h2>'+brand+'</h2>'
    if brand=='BODYARMOR':body+='<p class="status">Same Coca-Cola parent / portfolio competitor</p>'
    body+='<ul>'+''.join('<li><a href="'+esc(url)+'" target="_blank" rel="noopener">'+label+' ↗</a></li>' for label,url in rows)+'</ul></article>'
body+='</div><p>Public conversation: the linked reporting below is an earned-coverage fallback, not comprehensive social listening. No sentiment or social share-of-voice metrics are inferred.</p></section>'
text,n=re.subn(r'<section><p class="label">03 / BRAND &amp; COMPETITOR SOCIAL</p>.*?</section>',lambda m:body,text,flags=re.S)
if n!=1:raise ValueError('Social marker missing')
widgets=base/'widgets';widgets.mkdir(exist_ok=True)
body='<section><p class="label">05 / SEARCH &amp; CONSUMER INTENT</p><p>Google Trends source embeds / US and Canada kept separate. Relative search interest is not search volume, purchase intent or market share. Widgets refresh from Google when loaded, not from a stored Reduction dataset.</p><div class="grid">'
for geo,name in [('US','United States'),('CA','Canada')]:
    for kind,widget,label in [('interest','TIMESERIES','Search interest comparison'),('queries','RELATED_QUERIES','Powerade related queries')]:
        terms=['Powerade','Gatorade','BODYARMOR'] if kind=='interest' else ['Powerade']
        req={'comparisonItem':[{'keyword':term,'geo':geo,'time':'today 12-m'} for term in terms],'category':0,'property':''}
        query=urllib.parse.urlencode({'geo':geo,'q':','.join(terms),'date':'today 12-m'})
        options={'exploreQuery':query,'guestPath':'https://trends.google.com:443/trends/embed/'}
        filename='trends-'+geo.lower()+'-'+kind+'.html'
        widget_html='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+name+' '+label+'</title><style>body{margin:0;background:white;font:14px Arial}</style></head><body><script src="https://ssl.gstatic.com/trends_nrtr/3728_RC01/embed_loader.js"></script><script>if(window.trends){trends.embed.renderExploreWidget('+json.dumps(widget)+','+json.dumps(req)+','+json.dumps(options)+');}</script><p><a href="https://trends.google.com/trends/explore?'+esc(query)+'" target="_blank" rel="noopener">Open Google Trends if chart does not load</a></p></body></html>'
        (widgets/filename).write_text(widget_html)
        body+='<article class="card"><p class="label">'+name+'</p><h2>'+label+'</h2><iframe title="'+name+' '+label+'" src="/dashboards/widgets/'+filename+'" loading="lazy" style="width:100%;height:380px;border:0;background:white"></iframe><p><a href="https://trends.google.com/trends/explore?'+esc(query)+'" target="_blank" rel="noopener">Open source ↗</a></p></article>'
body+='</div><p class="status">Embed integration awaiting browser verification. Google can suppress charts for insufficient data or deny a widget request. Related queries are search signals, not verified consumer questions. Geography sets search origin, not campaign location.</p></section>'
text,n=re.subn(r'<section><p class="label">05 / SEARCH &amp; CONSUMER INTENT</p>.*?</section>',lambda m:body,text,flags=re.S)
if n!=1:raise ValueError('Search marker missing')
page.write_text(text)
print('Rendered source-linked social channels and four regional Trends widget pages. Not published.')
