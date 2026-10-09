import datetime as dt,http.server,json,pathlib,re,threading,shutil,subprocess,tempfile
from playwright.sync_api import sync_playwright
root=pathlib.Path(__file__).resolve().parents[1];public=root/'public';out=root/'qa-artifacts';out.mkdir(exist_ok=True)
base=public/'dashboards';checks=[];warnings=[];market_quote_checks={}
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
with tempfile.TemporaryDirectory() as temp:
    clone=pathlib.Path(temp)
    shutil.copytree(root/'pipeline',clone/'pipeline')
    shutil.copytree(root/'public',clone/'public')
    shutil.copytree(root/'.github',clone/'.github')
    script=clone/'pipeline/refine_dashboard.py'
    subprocess.run(['python',str(script)],check=True)
    first=(clone/'public/dashboards/powerade/index.html').read_bytes()
    subprocess.run(['python',str(script)],check=True)
    second=(clone/'public/dashboards/powerade/index.html').read_bytes()
    check('Refinement rendering is idempotent',first==second)
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
            check(name+' financial snapshot rendered',page.get_by_text('LATEST REVIEWED RELEASE / Q2 2026',exact=True).count()==1)
            check(name+' initial video count',page.locator('.video-card:visible').count()==min(3,len(y['videos'])))
            check(name+' no player before interaction',page.locator('#youtube-discovery iframe').count()==0)
            for image in page.locator('.video-card:visible img').all():
                image.scroll_into_view_if_needed()
                image.evaluate('(img)=>{img.loading="eager"}')
            page.wait_for_function("Array.from(document.querySelectorAll('.video-card:not([hidden]) img')).every(i=>i.complete && i.naturalWidth>0)",timeout=20000)
            check(name+' thumbnail images loaded',page.locator('.video-card:visible img').count()==min(3,len(y['videos'])))
            if len(y['videos'])>3:
                page.locator('#show-videos').click()
                check(name+' expands all videos',page.locator('.video-card:visible').count()==len(y['videos']))
                page.locator('#show-videos').click()
                check(name+' collapses extra videos',page.locator('.video-card:visible').count()==3)
            if y['videos']:
                page.locator('.video-play:visible').first.click()
                check(name+' click creates player',page.locator('#youtube-discovery iframe').count()==1)
                check(name+' external watch links preserved',page.locator('#youtube-discovery a[href^="https://www.youtube.com/watch"]').count()==len(y['videos']))
                warnings.append(name+': click-to-player works; actual video playback and consent remain manual-review items')
                page.reload(wait_until='domcontentloaded')
                for image in page.locator('.video-card:visible img').all():image.scroll_into_view_if_needed()
                page.wait_for_function("Array.from(document.querySelectorAll('.video-card:not([hidden]) img')).every(i=>i.complete && i.naturalWidth>0)",timeout=20000)
            page.evaluate('window.scrollTo(0,0)')
            check(name+' no empty Trends frames',page.locator('iframe[src*="/dashboards/widgets/trends-"]').count()==0)
            check(name+' regional source links',page.locator('a[href^="https://trends.google.com/trends/explore?"]').count()>=4)
            for frame in page.locator('iframe').all():check(name+' iframe has accessible title',bool(frame.get_attribute('title')))
            if errors:warnings.append(name+' browser errors: '+'; '.join(errors))
            page.locator('#brand-logo').scroll_into_view_if_needed()
            page.wait_for_function("document.querySelector('#brand-logo').complete && document.querySelector('#brand-logo').naturalWidth>0")
            check(name+' brand logo loaded',page.locator('#brand-logo').count()==1)
            check(name+' parent ticker source present',page.locator('#parent-quote').count()==1)
            observed=False
            for frame in page.frames:
                if 'tradingview.com/embed-widget/' in frame.url or 'tradingview-widget.com/embed-widget/' in frame.url:
                    try:
                        quote=frame.locator('body').inner_text(timeout=3000)
                        if ('KO' in quote or 'Coca-Cola' in quote) and re.search(r'\d+[.,]\d{2}',quote):observed=True
                    except Exception:pass
            market_quote_checks[name]=observed
            if not observed:warnings.append(name+': provider stock quote was not visibly verified; source link is available. Do not label the ticker connection complete.')
            page.evaluate('window.scrollTo(0,0)')
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
        page.goto('http://127.0.0.1:8765/dashboards/admin/editorial.html')
        page.wait_for_function("document.querySelector('#editorial').value.length>0")
        original=page.locator('#editorial').input_value()
        page.locator('#editorial').fill('invalid json');page.locator('#export').click()
        check('Editorial editor rejects invalid JSON',bool(page.locator('#status').inner_text()))
        invalid=json.loads(original);invalid['lens']['sources']=['http://example.com']
        page.locator('#editorial').fill(json.dumps(invalid));page.locator('#export').click()
        check('Editorial editor rejects non-HTTPS sources','HTTPS' in page.locator('#status').inner_text())
        page.locator('#editorial').fill(original)
        with page.expect_download():page.locator('#export').click()
        check('Editorial export does not approve or publish','No publication or approval' in page.locator('#status').inner_text())
        check('Editorial export preserves review date',json.loads(page.locator('#editorial').input_value())['reviewed_at']==json.loads(original)['reviewed_at'])
        browser.close()
except Exception as err:
    warnings.append('QA stopped: '+str(err))
    raise
finally:
    server.shutdown()
    report={'market_quote_checks':market_quote_checks,'tested_at':dt.datetime.now(dt.timezone.utc).isoformat(),'checks':checks,'warnings':warnings,'publication_allowed':False,'unresolved':['Visual review of screenshots','External embed content and consent behavior','Financial dataset freshness','Automated editorial/brand sales updates','Hosting deploy behavior for bot refresh commits','Full product scope acceptance']}
    (out/'readiness.json').write_text(json.dumps(report,indent=2))
