import copy,datetime as dt,hashlib,json,pathlib,shutil,subprocess,sys,tempfile
root=pathlib.Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as temp:
    clone=pathlib.Path(temp)
    for folder in ['pipeline','public','.github']:shutil.copytree(root/folder,clone/folder)
    base=clone/'public/dashboards';data=base/'data';epath=data/'powerade-editorial.json'
    def read(p):return json.loads(p.read_text())
    def write(p,d):p.write_text(json.dumps(d,indent=2))
    e=read(epath);e['reviewed_at']=str(dt.datetime.now(dt.timezone.utc).date()-dt.timedelta(days=60));e['lens']['reviewed_at']=e['reviewed_at'];write(epath,e);approved=copy.deepcopy(e)
    s=read(data/'powerade-signals.json');s['Powerade']['items'].append({'title':'Powerade synthetic fixture development','url':'https://example.com/fixture-news','date':dt.datetime.now(dt.timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT'),'publisher':'Fixture only'});write(data/'powerade-signals.json',s)
    urls=set(e['profile']['sources']+[e['financials']['source'],e['leadership']['source']])
    statepath=clone/'pipeline/editorial-source-state.json';write(statepath,{u:{'digest':'fixture-baseline','checked_at':'2000-01-01T00:00:00+00:00'} for u in urls})
    def monitor(fail=False):
        response="urllib.request.urlopen=lambda *a,**k: (_ for _ in ()).throw(OSError('Fixture failure'))" if fail else "urllib.request.urlopen=lambda *a,**k: io.BytesIO(b'<html><body>'+b'Fixture changed reference text '*20+b'</body></html>')"
        code='import runpy,sys,urllib.request,io; '+response+"; runpy.run_path(sys.argv[1],run_name='__main__')"
        subprocess.run([sys.executable,'-c',code,str(clone/'pipeline/editorial_monitor.py')],cwd=clone,check=True)
    monitor();queue=read(data/'powerade-review-queue.json')
    assert any(i['type']=='reference_change' for i in queue['items']),'Reference change not queued'
    assert any(i['url']=='https://example.com/fixture-news' for i in queue['items']),'New reporting not queued'
    first={i['id'] for i in queue['items']};monitor();second=read(data/'powerade-review-queue.json')
    assert first=={i['id'] for i in second['items']},'Duplicate discovery items created'
    assert read(epath)==approved,'Discovery changed approved claims or review dates'
    h=read(data/'powerade-health.json');assert h['editorial_review']['overdue'],'Overdue review not flagged'
    state=read(statepath);baseline=copy.deepcopy(state)
    for v in state.values():v['checked_at']='2000-01-01T00:00:00+00:00'
    write(statepath,state);monitor(True);failed=read(statepath)
    for u in baseline:assert failed[u]['digest']==baseline[u]['digest'],'Failure discarded baseline'
    assert read(epath)==approved,'Failure changed approved content'
    e=read(epath);e['lens']['headline']='Synthetic reviewed Lens fixture';write(epath,e)
    subprocess.run([sys.executable,str(clone/'pipeline/refine_dashboard.py')],cwd=clone,check=True)
    assert 'Synthetic reviewed Lens fixture' in (base/'powerade/index.html').read_text(),'Lens is not editable from JSON'
    assert 'review overdue' in (base/'powerade/index.html').read_text(),'Overdue review not visible'
    registry=base/'brands.json';original=read(registry)
    hidden=copy.deepcopy(original)
    for b in hidden:
        if b['slug']=='powerade':b['enabled']=False
    write(registry,hidden);subprocess.run([sys.executable,str(clone/'pipeline/render_dashboard_content.py')],cwd=clone,check=True)
    assert 'href="/dashboards/powerade/"' not in (base/'index.html').read_text(),'Hide failed'
    fixture=base/'fixture-brand';fixture.mkdir(exist_ok=True);(fixture/'index.html').write_text('<!doctype html><title>Fixture</title>')
    added=copy.deepcopy(original)+[{'slug':'fixture-brand','name':'Fixture Brand','enabled':True}];write(registry,added)
    subprocess.run([sys.executable,str(clone/'pipeline/render_dashboard_content.py')],cwd=clone,check=True)
    assert 'href="/dashboards/fixture-brand/"' in (base/'index.html').read_text(),'Directory add failed'
    write(registry,original);subprocess.run([sys.executable,str(clone/'pipeline/render_dashboard_content.py')],cwd=clone,check=True)
    assert 'href="/dashboards/fixture-brand/"' not in (base/'index.html').read_text(),'Directory removal failed'
    assert (fixture/'index.html').exists(),'Directory removal unexpectedly purged content'
    write(registry,original+[copy.deepcopy(original[0])])
    duplicate=subprocess.run([sys.executable,str(clone/'pipeline/render_dashboard_content.py')],cwd=clone)
    assert duplicate.returncode!=0,'Duplicate slug accepted'
print('Editorial governance, failure retention, editable Lens and directory tests passed using synthetic temporary fixtures. No production content changed.')
