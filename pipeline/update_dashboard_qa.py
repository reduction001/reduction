import pathlib
root=pathlib.Path(__file__).resolve().parents[1]
path=root/'pipeline/dashboard_qa.py';text=path.read_text()
text=text.replace('import datetime as dt,http.server,json,pathlib,re,threading','import datetime as dt,http.server,json,pathlib,re,threading,shutil,subprocess,tempfile')
text=text.replace("page.get_by_text('Q2 2026 / GLOBAL',exact=True)","page.get_by_text('LATEST REVIEWED RELEASE / Q2 2026',exact=True)")
old="            check(name+' six-or-fewer video embeds',page.locator('#youtube-discovery iframe').count()<=6)"
new='''            check(name+' initial video count',page.locator('.video-card:visible').count()==min(3,len(y['videos'])))
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
            check(name+' no empty Trends frames',page.locator('iframe[src*="/dashboards/widgets/"]').count()==0)
            check(name+' regional source links',page.locator('a[href^="https://trends.google.com/trends/explore?"]').count()>=4)'''
if old in text:text=text.replace(old,new)
elif "initial video count" not in text:raise ValueError('Old video QA marker missing')
start=text.find("        for filename in ['trends-us-interest.html'")
if start>=0:
    end=text.index('        browser.close()',start)
    text=text[:start]+text[end:]
marker='handler=lambda *args,**kwargs:'
block='''with tempfile.TemporaryDirectory() as temp:
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
'''
if "Refinement rendering is idempotent" not in text:text=text.replace(marker,block+marker,1)
path.write_text(text)
compile(text,str(path),'exec')
print('Updated QA expectations and added media interaction and idempotence checks.')
