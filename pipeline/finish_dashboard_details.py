import html,json,pathlib,re,urllib.parse,urllib.request
root=pathlib.Path(__file__).resolve().parents[1];base=root/'public/dashboards';esc=lambda x:html.escape(str(x))
assets=base/'assets';assets.mkdir(exist_ok=True);logo=assets/'powerade-logo.png'
provenance=base/'data/powerade-logo.json'
if not logo.exists():
    params={'action':'query','titles':'File:Powerade-logo-2019.svg','prop':'imageinfo','iiprop':'url|extmetadata','iiurlwidth':240,'format':'json'}
    req=urllib.request.Request('https://commons.wikimedia.org/w/api.php?'+urllib.parse.urlencode(params),headers={'User-Agent':'ReductionMonitor/1.0 (https://reduction.nyc)'})
    with urllib.request.urlopen(req,timeout=30) as r:result=json.load(r)
    info=next(iter(result['query']['pages'].values()))['imageinfo'][0];url=info['thumburl']
    if urllib.parse.urlparse(url).netloc!='upload.wikimedia.org':raise ValueError('Unexpected asset host')
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'ReductionMonitor/1.0 (https://reduction.nyc)'}),timeout=30) as r:payload=r.read(1500000)
    if not payload.startswith(bytes([137,80,78,71,13,10,26,10])):raise ValueError('Logo thumbnail is not PNG')
    logo.write_bytes(payload)
    provenance.write_text(json.dumps({'source':'https://commons.wikimedia.org/wiki/File:Powerade-logo-2019.svg','asset_label':'Powerade-logo-2019.svg','thumbnail_url':url,'license_metadata':info.get('extmetadata',{}),'scope':'Sourced 2019 logo file; not a verification of current brand guidelines or endorsement'},indent=2))
e=json.loads((base/'data/powerade-editorial.json').read_text());p=e['profile'];lead=e['leadership']
page=base/'powerade/index.html';text=page.read_text()
def link(u,label):return '<a href="'+esc(u)+'" target="_blank" rel="noopener">'+esc(label)+' ↗</a>'
body='<article class="card"><h2>Brand identity</h2><img id="brand-logo" src="/dashboards/assets/powerade-logo.png" alt="Powerade logo, sourced 2019 asset" style="display:block;max-width:180px;max-height:65px;background:white;padding:10px;border-radius:5px;margin:18px 0"><p>'+esc(p['name'])+' / '+esc(p['parent'])+'</p><p>'+esc(p['us_proposition'])+'</p><p>Global platform: '+esc(p['global_platform'])+'</p><details><summary>Leadership, scope &amp; sources</summary><p>'+esc(p['platform_scope'])+'</p><p>Parent CEO: '+esc(lead['parent_ceo'])+'</p><p>North America: '+esc(lead['north_america_interim'])+' interim; '+esc(lead['north_america_incoming'])+' announced effective '+esc(lead['incoming_effective'])+'. Reviewed '+esc(e['reviewed_at'])+'.</p><p>'+esc(lead['scope'])+'</p><p>Separate brand mission and values were not verified.</p>'
for label,url in zip(['US brand site','Global platform announcement','Regional leadership announcement'],p['sources']):body+='<p>'+link(url,label)+'</p>'
body+='<p>'+link('https://commons.wikimedia.org/wiki/File:Powerade-logo-2019.svg','Logo source and licensing notes')+'</p><p class="status">Sourced 2019 logo asset, not proof of current brand guidelines. Reduction is an independent monitoring site.</p></details></article>'
text,n=re.subn(r'<article class="card"><h2>Brand identity</h2>.*?</article>',lambda m:body,text,flags=re.S)
if n!=1:raise ValueError('Identity marker missing')
widgets=base/'widgets';widgets.mkdir(exist_ok=True)
widget='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Coca-Cola stock quote</title><style>body{margin:0;background:#10171c;color:#eee;font:12px Arial}a{color:#ceff72}.tradingview-widget-container{width:100%;min-height:125px}</style></head><body><div class="tradingview-widget-container"><div class="tradingview-widget-container__widget"></div><div class="tradingview-widget-copyright"><a href="https://www.tradingview.com/symbols/NYSE-KO/" rel="noopener" target="_blank">KO stock price</a> by TradingView</div><script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-single-quote.js" async>{"symbol":"NYSE:KO","width":"100%","locale":"en","colorTheme":"dark","isTransparent":true}</script></div><p>If the quote is unavailable, open the source above. No replacement price is inferred.</p></body></html>'''
(widgets/'ko-quote.html').write_text(widget)
market='<section id="parent-market"><p class="label">PARENT STOCK / NYSE:KO / USD</p><iframe id="parent-quote" title="Coca-Cola parent-company stock quote by TradingView" src="/dashboards/widgets/ko-quote.html" style="width:100%;max-width:430px;height:180px;border:0;background:#10171c"></iframe><p class="status">Provider-delivered quote when loaded; exchange data may be delayed. This is Coca-Cola stock, not Powerade sales or campaign performance.</p><p>'+link('https://www.tradingview.com/symbols/NYSE-KO/','Quote source / TradingView')+'</p></section>'
if 'id="parent-market"' in text:text=re.sub(r'<section id="parent-market">.*?</section>',lambda m:market,text,flags=re.S)
else:text=text.replace('<section><p class="label">01 / EXECUTIVE SNAPSHOT</p>',market+'<section><p class="label">01 / EXECUTIVE SNAPSHOT</p>',1)
text=text.replace('Free-provider candidate · integration pending.','Source-link fallback · Google Ads Transparency Center.')
text=text.replace('Source-link fallback · North American API feed unverified.','Source-link fallback · TikTok Commercial Content Library; geographic coverage differs from this dashboard.')
text=text.replace('Source-linked fallback. Embedded charts did not visibly render in QA, so empty chart frames have been removed. No search metrics are inferred.','Explore US and Canadian search signals on Google Trends. Source-linked access, not a collected in-dashboard search dataset.')
page.write_text(text)
qa=root/'pipeline/dashboard_qa.py';code=qa.read_text()
code=code.replace('iframe[src*="/dashboards/widgets/"]','iframe[src*="/dashboards/widgets/trends-"]')
if 'market_quote_checks={}' not in code:code=code.replace('checks=[];warnings=[]','checks=[];warnings=[];market_quote_checks={}')
if "brand logo loaded" not in code:
    marker="            page.screenshot(path=str(out/(name+'.png')),full_page=True)"
    block='''            page.locator('#brand-logo').scroll_into_view_if_needed()
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
'''
    if marker not in code:raise ValueError('Screenshot marker missing')
    code=code.replace(marker,block+marker)
if "Editorial editor rejects invalid JSON" not in code:
    marker='        browser.close()'
    block='''        page.goto('http://127.0.0.1:8765/dashboards/admin/editorial.html')
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
'''
    code=code.replace(marker,block+marker)
code=code.replace("report={'tested_at':","report={'market_quote_checks':market_quote_checks,'tested_at':")
qa.write_text(code);compile(code,str(qa),'exec')
tests=root/'pipeline/test_dashboard_refresh.py';code=tests.read_text()
code=code.replace("['render_dashboard_content.py','render_social_search.py','financial_monitor.py','refine_dashboard.py']","['render_dashboard_content.py','render_social_search.py','financial_monitor.py','refine_dashboard.py','finish_dashboard_details.py']")
tests.write_text(code);compile(code,str(tests),'exec')
print('Rendered sourced logo, provider ticker and capability labels; updated QA. Quote availability still requires browser verification. No deployment.')
