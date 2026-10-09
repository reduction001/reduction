import pathlib
root=pathlib.Path(__file__).resolve().parents[1]
public=root/'public'
path=public/'index.html'
text=path.read_text()
marker='</ul></nav>'
link='<li><a href="/dashboards"><span class="nav-title"><span>Dashboards</span><span aria-hidden="true">↗</span></span><span class="nav-note">Brand activity, creative &amp; cultural signals</span></a></li>\n'
if 'href="/dashboards"' not in text:
    if text.count(marker)!=1:raise SystemExit('Unexpected homepage structure; refusing overwrite')
    text=text.replace(marker,link+marker)
path.write_text(text)
path=public/'_redirects'
text=path.read_text() if path.exists() else ''
rules=['/dashboards /dashboards/index.html 200','/dashboards/powerade /dashboards/powerade/index.html 200']
for rule in rules:
    if rule not in text:text=text.rstrip()+'\n'+rule+'\n'
path.write_text(text)
assert (public/'dashboards/index.html').exists()
assert (public/'dashboards/powerade/index.html').exists()
assert 'href="/rtx"' in (public/'index.html').read_text()
print('Homepage and dashboard routes prepared; RTX preserved. Deployment not performed.')
