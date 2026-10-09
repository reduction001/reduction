import datetime as dt,html,json,pathlib,re,urllib.request
base=pathlib.Path(__file__).resolve().parents[1]/'public/dashboards'
path=base/'data/powerade-parent-financials.json'
now=dt.datetime.now(dt.timezone.utc);stamp=now.isoformat()
source='https://data.sec.gov/api/xbrl/companyfacts/CIK0000021344.json'
old=json.loads(path.read_text()) if path.exists() else {}
data=old
if not old.get('updated') or (now-dt.datetime.fromisoformat(old['updated'])).days>=28:
    try:
        req=urllib.request.Request(source,headers={'User-Agent':'ReductionMonitor/1.0 (https://reduction.nyc)','Accept':'application/json'})
        with urllib.request.urlopen(req,timeout=30) as r:facts=json.load(r)
        tags=['RevenueFromContractWithCustomerExcludingAssessedTax','SalesRevenueNet','Revenues']
        selections={}
        for label,lo,hi in [('quarter',75,105),('annual',350,380)]:
            candidates=[]
            for priority,tag in enumerate(tags):
                for row in facts.get('facts',{}).get('us-gaap',{}).get(tag,{}).get('units',{}).get('USD',[]):
                    if row.get('form') not in ['10-Q','10-K'] or not row.get('start') or not row.get('end'):continue
                    duration=(dt.date.fromisoformat(row['end'])-dt.date.fromisoformat(row['start'])).days+1
                    if lo<=duration<=hi and row['end']<=str(now.date()):candidates.append((row['end'],row.get('filed',''),-priority,tag,row))
            if candidates:
                chosen=max(candidates,key=lambda x:x[:3]);row=dict(chosen[4]);row['tag']=chosen[3];selections[label]=row
        if not selections:raise ValueError('No valid quarterly or annual revenue facts')
        data={'updated':stamp,'source':source,'scope':'The Coca-Cola Company / global consolidated revenue / USD; not Powerade sales','periods':selections}
    except Exception as e:
        data=dict(old,error=type(e).__name__,attempted=stamp)
path.parent.mkdir(exist_ok=True);path.write_text(json.dumps(data,indent=2))
esc=lambda x:html.escape(str(x))
body='<div id="sec-parent-revenue"><p class="label">AUTOMATED PARENT REVENUE / SEC FILINGS</p><p class="status">Last success: '+esc(data.get('updated','Not available'))+'</p>'
if data.get('error'):body+='<p>Latest SEC collection failed; previous successful data, if any, retained. No invented replacement figure.</p>'
for period,row in data.get('periods',{}).items():
    body+='<p>'+esc(period.title())+' period '+esc(row['start'])+' to '+esc(row['end'])+': $'+esc(f"{row['val']/1e9:,.2f}")+'bn consolidated revenue.</p><p class="status">Filed '+esc(row.get('filed',''))+' / '+esc(row['form'])+' / '+esc(row['tag'])+'</p>'
    accession=row.get('accn','').replace('-','')
    if accession.isdigit():body+='<a href="https://www.sec.gov/Archives/edgar/data/21344/'+accession+'/" target="_blank" rel="noopener">Source filing ↗</a>'
body+='<p class="status">Monthly collection. Periods are selected from filed facts, not inferred from year-to-date totals. Annual and quarterly numbers must not be compared as like-for-like. Brand/category growth snapshot above is editorially sourced and separate.</p></div>'
page=base/'powerade/index.html';text=page.read_text()
if 'id="sec-parent-revenue"' in text:
    text,n=re.subn(r'<div id="sec-parent-revenue">.*?</div>',lambda m:body,text,flags=re.S)
else:
    text,n=re.subn(r'(<article class="card"><h2>Financial snapshot</h2>.*?)(</article>)',lambda m:m[1]+body+m[2],text,flags=re.S)
if n!=1:raise SystemExit('Financial insertion marker missing')
page.write_text(text)
print('SEC periods available:',','.join(data.get('periods',{})) or 'none','Latest attempt:',data.get('error','success'))
