#!/usr/bin/env python3
"""Generate shared navigation from public HTML, with explicit overrides/exclusions."""
import argparse, json, re, shutil
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

class Metadata(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_title=False
        self.title=[]
        self.meta={}
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='title':self.in_title=True
        if tag=='meta':self.meta[a.get('name','').lower()]=a.get('content','')
    def handle_endtag(self,tag):
        if tag=='title':self.in_title=False
    def handle_data(self,data):
        if self.in_title:self.title.append(data)

def public_route(relative):
    parts=list(relative.parts)
    if parts[-1]=='index.html':parts=parts[:-1]
    else:parts[-1]=Path(parts[-1]).stem
    return '/'+('/'.join(parts)) if parts else '/'

def build(root):
    config=json.loads((root/'navigation.config.json').read_text(encoding='utf-8'))
    origin=config['site_origin'].rstrip('/')
    exclusions=config.get('exclude_paths',[])
    overrides=config.get('overrides',{})
    items=[]
    seen=set()
    public=root/'public'
    for file in sorted(public.rglob('*.html')):
        rel=file.relative_to(public)
        if any(part.startswith(('.', '_')) for part in rel.parts):continue
        if any(part.lower() in {'admin','private','preview','drafts'} for part in rel.parts):continue
        route=public_route(rel)
        if any(route==path or route.startswith(path.rstrip('/')+'/') for path in exclusions):continue
        m=Metadata();m.feed(file.read_text(encoding='utf-8'))
        if m.meta.get('reduction:nav','').lower() in {'hidden','false','exclude'}:continue
        override=overrides.get(route,{})
        if override.get('hidden'):continue
        label=override.get('label') or m.meta.get('reduction:nav-label') or ''.join(m.title).strip() or file.stem.replace('-',' ').title()
        description=override.get('description',m.meta.get('description',''))
        order=override.get('order',m.meta.get('reduction:nav-order',100))
        try:order=float(order)
        except (ValueError,TypeError):order=100
        url=origin+route
        if url in seen:continue
        seen.add(url)
        items.append({'id':re.sub(r'[^a-z0-9]+','-',route.lower()).strip('-') or 'reduction','label':label,'url':url,'description':description,'order':order})
    for item in config.get('external_pages',[]):
        if item.get('hidden'):continue
        if urlsplit(item.get('url','')).scheme not in {'http','https'}:raise ValueError('External page must have an absolute HTTP(S) URL')
        if item['url'] in seen:continue
        seen.add(item['url']);items.append(item)
    items.sort(key=lambda x:(float(x.get('order',100)),x['label'].casefold()))
    data={'version':1,'items':items}
    for directory in [root/'public',root/'facts']:
        directory.mkdir(parents=True,exist_ok=True)
        (directory/'site-navigation.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        shutil.copyfile(root/'shared'/'site-nav.js',directory/'site-nav.js')
    return data

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);args=p.parse_args()
    data=build(args.root.resolve());print(f"Built navigation: {len(data['items'])} pages")
