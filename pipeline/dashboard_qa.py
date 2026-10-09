import datetime as dt,http.server,json,pathlib,re,threading
from playwright.sync_api import sync_playwright
root=pathlib.Path(__file__).resolve().parents[1];public=root/'public';out=root/'qa-artifacts';out.mkdir(exist_ok=True)
base=public/'dashboards';checks=[];warnings=[]
def check(name,ok):
    checks.append({'check':name,'passed':bool(ok)})
    if not ok:raise AssertionError(name)
for file in public.rglob('*'):
    if file.is_file() and file.suffix in ['.html','.json','.js','.css']:
        check('No Google API key in '+str(file.relative_to(public)),not re.search(r'AIza[0-9A-Za-z_-]{30,}',file.read_text()))
y=json.loads((base/'data/powerade-youtube.json').read_text())
check('Official English YouTube policy',y.get('policy')=='official-us-english-audio-v2')
check('Qualified video provenance',all(v['channel_id']==y['channel_id'] and v['audio_language'].lower().startswith('en') for v in y['videos']))
if not y['videos']:warnings.append('No qualified official video uploads currently displayed')
news=json.loads((base/'data/powerade-signals.json').read_text())
for brand in ['Powerade','Gatorade','BODYARMOR']:check(brand+' news has a successful collection',bool(news.get(brand,{}).get('updated')))
check('Wikipedia successful collection',bool(news.get('wiki',{}).get('updated')))
f=json.loads((base/'data/powerade-parent-financials.json').read_text())
if not f.get('periods'):warnings.append('SEC collector has no successful financial facts')
e=json.loads((base/'data/powerade-editorial.json').read_text())
quarter=f.get('periods',{}).get('quarter',{})
if quarter.get('filed','')<e['financials']['published_at']:warnings.append('SEC quarterly facts predate the editorial earnings release; label as latest available in this dataset, not latest reported quarter')
handler=lambda *args,**kwargs:http.server.SimpleHTTPRequestHandler(*args,directory=str(public),**kwargs)
server=http.server.ThreadingHTTPServer(('127.0.0.1',8765),handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
try:
    with sync_playwright() as p:
        browser=p.chromium.launch()
        for name,width,height in [('desktop',1440,1000),('mobile',390,844)]:
            page=browser.new_page(viewport={'width':width,'height':height})
            errors=[];page.on('pageerror',lambda err:errors.append(str(err)))
            page.goto('http://127.0.0.1:8765/dashboards/powerade/',wait_until='domcontentloaded')
            page.wait_for_timeout(8000)
            check(name+' has exactly one Lens',page.locator('section.lens').count()==1)
            check(name+' Lens is outside cards',page.locator('article.card section.lens').count()==0)
            check(name+' no nested cards',page.locator('article.card article.card').count()==0)
            check(name+' no horizontal document overflow',page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 2'))
            check(name+' profile rendered',page.get_by_text('Global platform: Pause is Power',exact=True).count()==1)
            check(name+' financial snapshot rendered',page.get_by_text('Q2 2026 / GLOBAL',exact=True).count()==1)
            check(name+' six-or-fewer video embeds',page.locator('#youtube-discovery iframe').count()<=6)
            for frame in page.locator('iframe').all():check(name+' iframe has accessible title',bool(frame.get_attribute('title')))
            if errors:warnings.append(name+' browser errors: '+'; '.join(errors))
            page.screenshot(path=str(out/(name+'.png')),full_page=True)
            page.close()
        page=browser.new_page()
        page.goto('http://127.0.0.1:8765/')
        check('Homepage has Dashboard navigation',page.locator('a[href="/dashboards"]').count()==1)
        check('Homepage retains RTX',page.locator('a[href="/rtx"]').count()>=1)
        page.goto('http://127.0.0.1:8765/dashboards/')
        check('Directory points to Powerade',page.locator('a[href="/dashboards/powerade/"]').count()==1)
        page.goto('http://127.0.0.1:8765/dashboards/admin/')
        page.wait_for_function("document.querySelector('#config').value.length > 0")
        page.locator('#config').fill('invalid json')
        page.locator('#export').click()
        check('Admin rejects invalid JSON',bool(page.locator('#status').inner_text()))
        page.locator('#config').fill(json.dumps([{'slug':'powerade','name':'Powerade','enabled':True}]))
        with page.expect_download():page.locator('#export').click()
        check('Admin exports without publishing','not published' in page.locator('#status').inner_text())
        for filename in ['trends-us-interest.html','trends-us-queries.html','trends-ca-interest.html','trends-ca-queries.html']:
            page.goto('http://127.0.0.1:8765/dashboards/widgets/'+filename,wait_until='domcontentloaded')
            page.wait_for_timeout(8000)
            if page.locator('iframe').count()==0:warnings.append(filename+': no child chart iframe; embed may be unavailable')
            check(filename+' has source fallback',page.locator('a[href^="https://trends.google.com/"]').count()>=1)
        browser.close()
except Exception as err:
    warnings.append('QA stopped: '+str(err))
    raise
finally:
    server.shutdown()
    report={'tested_at':dt.datetime.now(dt.timezone.utc).isoformat(),'checks':checks,'warnings':warnings,'publication_allowed':False,'unresolved':['Visual review of screenshots','External embed content and consent behavior','Financial dataset freshness','Automated editorial/brand sales updates','Hosting deploy behavior for bot refresh commits','Full product scope acceptance']}
    (out/'readiness.json').write_text(json.dumps(report,indent=2))
