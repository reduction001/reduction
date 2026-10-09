import json,os,pathlib,shutil,subprocess,sys,tempfile
root=pathlib.Path(__file__).resolve().parents[1]
if not os.environ.get('YOUTUBE_API_KEY'):raise SystemExit('Secret required to exercise collector failure paths')
def run(clone,name,fault=False):
    script=str(clone/'pipeline'/name)
    if fault:
        code="import runpy,sys,urllib.request; urllib.request.urlopen=lambda *a,**k: (_ for _ in ()).throw(OSError('Injected network failure')); runpy.run_path(sys.argv[1],run_name='__main__')"
        return subprocess.run([sys.executable,'-c',code,script],cwd=clone).returncode
    return subprocess.run([sys.executable,script],cwd=clone,check=True).returncode
with tempfile.TemporaryDirectory() as temp:
    clone=pathlib.Path(temp)
    for folder in ['pipeline','public','.github']:shutil.copytree(root/folder,clone/folder)
    base=clone/'public/dashboards/data'
    def load(name):return json.loads((base/name).read_text())
    before=load('powerade-signals.json');forced=dict(before);forced['wiki']=dict(before['wiki'],updated='2000-01-01T00:00:00+00:00')
    (base/'powerade-signals.json').write_text(json.dumps(forced))
    run(clone,'signals_monitor.py',True);after=load('powerade-signals.json')
    for brand in ['Powerade','Gatorade','BODYARMOR']:
        assert after[brand]['items']==before[brand]['items'],brand+' last-good news lost'
        assert after[brand].get('error'),brand+' missing failure notice'
    assert after['wiki']['views']==before['wiki']['views'],'Wikipedia last-good metric lost'
    assert after['wiki'].get('error'),'Wikipedia missing failure notice'
    before_y=load('powerade-youtube.json');run(clone,'youtube_monitor.py',True);after_y=load('powerade-youtube.json')
    assert before_y['videos']==after_y['videos'],'YouTube last-good videos lost'
    assert after_y.get('error'),'YouTube missing failure notice'
    before_f=load('powerade-parent-financials.json');forced=dict(before_f,updated='2000-01-01T00:00:00+00:00')
    (base/'powerade-parent-financials.json').write_text(json.dumps(forced))
    run(clone,'financial_monitor.py',True);after_f=load('powerade-parent-financials.json')
    assert before_f['periods']==after_f['periods'],'SEC last-good facts lost'
    assert after_f.get('error'),'SEC missing failure notice'
    for name in ['render_dashboard_content.py','render_social_search.py','financial_monitor.py','refine_dashboard.py']:run(clone,name)
    first=(clone/'public/dashboards/powerade/index.html').read_bytes()
    for name in ['render_dashboard_content.py','render_social_search.py','financial_monitor.py','refine_dashboard.py']:run(clone,name)
    second=(clone/'public/dashboards/powerade/index.html').read_bytes()
    assert first==second,'Combined rendering sequence is not idempotent'
    assert b'video-play' in second and b'reduction-lens' in second,'Final presentation lost'
    assert b'iframe src="/dashboards/widgets/' not in second,'Blank Trends frames returned'
print('Fault-injection retention and combined rendering tests passed in a temporary clone. No source files published.')
