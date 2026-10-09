import datetime as dt,hashlib,json,pathlib,re,urllib.parse
from playwright.sync_api import sync_playwright
BASE='https://d52b2473.reduction-6j2.pages.dev'
HOST=urllib.parse.urlparse(BASE).hostname
EXPECTED_HEALTH='0ea5115a0871359dde43508e07026fcd247417f8'
out=pathlib.Path('qa-artifacts');out.mkdir(exist_ok=True)
report={'tested_at':dt.datetime.now(dt.timezone.utc).isoformat(),'target':BASE,'expected_health_blob':EXPECTED_HEALTH,'publication_allowed':False,'checks':[],'warnings':[],'routes':[],'viewports':{}}
def check(name,value):report['checks'].append({'check':name,'passed':bool(value)})
def safe_url(value):
    p=urllib.parse.urlparse(value);return p.scheme+'://'+str(p.hostname or '')+p.path
def clean(value):return re.sub(r'https?://[^\s<>]+',lambda m:safe_url(m[0]),str(value))[:600]
def provider(value):
    host=urllib.parse.urlparse(value).hostname or ''
    return host=='tradingview.com' or host.endswith('.tradingview.com') or host=='tradingview-widget.com' or host.endswith('.tradingview-widget.com')
try:
    with sync_playwright() as p:
        browser=p.chromium.launch();context=browser.new_context();page=context.new_page()
        for path in ['/','/rtx','/dashboards/','/dashboards/powerade/','/dashboards/admin/','/dashboards/admin/editorial.html']:
            row={'path':path}
            try:
                response=page.goto(BASE+path,wait_until='domcontentloaded',timeout=45000);page.wait_for_timeout(4000)
                row.update({'status':response.status if response else None,'landed_url':safe_url(page.url),'title':page.title()})
                same=urllib.parse.urlparse(page.url).hostname==HOST
                check(path+' stays on supplied preview host',same);check(path+' HTTP success',bool(response and response.status==200))
                if same and response and response.status==200:
                    if path=='/':check('Hosted homepage has Dashboards link',page.locator('a[href="/dashboards"],a[href="/dashboards/"]').count()>=1)
                    if path=='/rtx':check('Hosted RTX retains story container',page.locator('#stories').count()==1)
                    if path=='/dashboards/':check('Hosted directory links Powerade',page.locator('a[href="/dashboards/powerade/"]').count()==1)
                    if path=='/dashboards/admin/':check('Hosted brand editor present',page.locator('#config').count()==1)
                    if path=='/dashboards/admin/editorial.html':check('Hosted editorial editor present',page.locator('#editorial').count()==1)
            except Exception as err:row['error']=clean(err);check(path+' reachable',False)
            report['routes'].append(row)
        try:
            response=context.request.get(BASE+'/dashboards/data/powerade-health.json',timeout=30000)
            body=response.body();digest=hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest()
            report['observed_health_blob']=digest;check('Hosted data matches inspected build-branch snapshot',response.status==200 and digest==EXPECTED_HEALTH)
        except Exception as err:report['warnings'].append('Health fingerprint unavailable: '+clean(err));check('Hosted data fingerprint available',False)
        page.close()
        for name,width,height in [('desktop',1440,1000),('mobile',390,844)]:
            page=context.new_page(viewport={'width':width,'height':height});responses=[];failed=[];errors=[]
            page.on('response',lambda r,rows=responses:rows.append({'url':safe_url(r.url),'status':r.status}) if provider(r.url) else None)
            page.on('requestfailed',lambda r,rows=failed:rows.append({'url':safe_url(r.url),'failure':clean(r.failure)}) if provider(r.url) else None)
            page.on('pageerror',lambda err,rows=errors:rows.append(clean(err)))
            result={'ticker_verified':False,'playback_observed':False}
            try:
                response=page.goto(BASE+'/dashboards/powerade/',wait_until='domcontentloaded',timeout=45000);page.wait_for_timeout(12000)
                if urllib.parse.urlparse(page.url).hostname!=HOST or not response or response.status!=200:raise ValueError('Not an accessible dashboard on the supplied preview host')
                check(name+' hosted Lens present',page.locator('section.lens').count()==1)
                check(name+' hosted page has no horizontal overflow',page.evaluate('document.documentElement.scrollWidth<=window.innerWidth+2'))
                check(name+' official thumbnails present',page.locator('.video-card:visible img').count()>=1)
                if page.locator('#brand-logo').count():
                    page.locator('#brand-logo').scroll_into_view_if_needed();page.wait_for_function("document.querySelector('#brand-logo').complete && document.querySelector('#brand-logo').naturalWidth>0",timeout=15000)
                    check(name+' hosted logo loads',True)
                else:check(name+' hosted logo present',False)
                frames=[]
                for frame in page.frames:
                    if provider(frame.url):
                        item={'url':safe_url(frame.url)}
                        try:
                            text=frame.locator('body').inner_text(timeout=3000);item['visible_text_excerpt']=clean(text)[:500]
                            symbol=bool(re.search(r'\bKO\b|Coca.Cola',text,re.I))
                            price=bool(re.search(r'\$\s*\d[\d,]*\.\d{2}|\d[\d,]*\.\d{2}\s*USD|USD\s*\d[\d,]*\.\d{2}',text,re.I))
                            if symbol and price:result['ticker_verified']=True
                        except Exception as err:item['read_error']=type(err).__name__
                        frames.append(item)
                result['provider_frames']=frames
                check(name+' hosted KO price visibly verified',result['ticker_verified'])
                page.evaluate('window.scrollTo(0,0)');page.screenshot(path=str(out/('hosted-'+name+'.png')),full_page=True)
                if page.locator('.video-play:visible').count():
                    page.locator('.video-play:visible').first.click();page.wait_for_timeout(12000)
                    for frame in page.frames:
                        host=urllib.parse.urlparse(frame.url).hostname or ''
                        if host.endswith('youtube-nocookie.com') or host.endswith('youtube.com'):
                            try:
                                if frame.locator('video').count() and frame.locator('video').first.evaluate('(v)=>!v.paused && v.readyState>=2 && v.currentTime>0'):result['playback_observed']=True
                            except Exception:pass
                    if not result['playback_observed']:report['warnings'].append(name+': actual hosted YouTube playback was not observed; manual playback/consent review remains required')
                else:report['warnings'].append(name+': expected click-to-play control missing')
            except Exception as err:result['error']=clean(err);check(name+' hosted dashboard inspection completed',False)
            result.update({'responses':responses[:50],'failed_provider_requests':failed[:30],'browser_errors':errors[:20]});report['viewports'][name]=result
            page.close()
        browser.close()
finally:
    (out/'hosted-preview-readiness.json').write_text(json.dumps(report,indent=2))
failed_checks=[c['check'] for c in report['checks'] if not c['passed']]
print(json.dumps({'passed_checks':len(report['checks'])-len(failed_checks),'failed_checks':failed_checks,'warnings':report['warnings'],'publication_allowed':False},indent=2))
if failed_checks:raise SystemExit('Hosted preview has unresolved checks; no production changes performed')
