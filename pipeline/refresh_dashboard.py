import datetime as dt,json,os,pathlib,subprocess,sys
root=pathlib.Path(__file__).resolve().parents[1];base=root/'public/dashboards'
if not os.environ.get('YOUTUBE_API_KEY'):raise SystemExit('YOUTUBE_API_KEY is required')
refiner=root/'pipeline/refine_dashboard.py';text=refiner.read_text()
marker="for name in ['youtube-monitoring.yml'"
if marker in text:
    text=text[:text.index(marker)]+"print('Applied dashboard presentation. No workflow edits or deployment performed.')\n"
    refiner.write_text(text)
steps=['render_dashboard_content.py','signals_monitor.py','youtube_monitor.py','financial_monitor.py','render_social_search.py','refine_dashboard.py']
results=[]
for name in steps:
    result=subprocess.run([sys.executable,str(root/'pipeline'/name)],cwd=root)
    results.append({'step':name,'exit_code':result.returncode})
    if result.returncode and name not in ['signals_monitor.py','youtube_monitor.py','financial_monitor.py']:raise SystemExit('Renderer failed: '+name)
now=dt.datetime.now(dt.timezone.utc);health={}
def status(label,data,days):
    updated=data.get('updated')
    if not updated:raise ValueError(label+' has no last-good collection')
    age=(now-dt.datetime.fromisoformat(updated)).total_seconds()/86400
    health[label]={'last_success':updated,'age_days':round(age,2),'state':'stale' if age>days else ('degraded' if data.get('error') else 'current'),'latest_error':data.get('error')}
signals=json.loads((base/'data/powerade-signals.json').read_text())
for brand in ['Powerade','Gatorade','BODYARMOR']:status(brand+' news',signals[brand],16)
status('Wikipedia',signals['wiki'],45)
y=json.loads((base/'data/powerade-youtube.json').read_text());status('YouTube',y,16)
if y.get('policy')!='official-us-english-audio-v2':raise ValueError('Unqualified YouTube policy')
f=json.loads((base/'data/powerade-parent-financials.json').read_text());status('Parent financial collection',f,45)
if not f.get('periods'):raise ValueError('No last-good parent financial facts')
e=json.loads((base/'data/powerade-editorial.json').read_text())
health['Editorial']={'reviewed_at':e['reviewed_at'],'state':'review_overdue' if (now.date()-dt.date.fromisoformat(e['reviewed_at'])).days>35 else 'reviewed_snapshot','automatic_editorial_updates':False}
report={'attempted_at':now.isoformat(),'steps':results,'sources':health,'publication_allowed':False,'scope':'Collector and rendering rehearsal; editorial review, ticker and hosting verification remain unfinished'}
(base/'data/powerade-health.json').write_text(json.dumps(report,indent=2))
print('Full refresh completed; QA must pass before commit. No deployment performed.')
