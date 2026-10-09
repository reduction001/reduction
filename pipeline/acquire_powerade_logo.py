import json,pathlib,re,urllib.parse,urllib.request
from defusedxml.ElementTree import fromstring
import cairosvg
root=pathlib.Path(__file__).resolve().parents[1];base=root/'public/dashboards'
allowed={'commons.wikimedia.org','upload.wikimedia.org'}
def validated(value):
    url=urllib.parse.urljoin('https://commons.wikimedia.org/',value)
    parsed=urllib.parse.urlparse(url)
    if parsed.scheme!='https' or parsed.hostname not in allowed or parsed.username or parsed.password or parsed.port not in [None,443]:raise ValueError('Untrusted Wikimedia URL host: '+str(parsed.hostname))
    return url
for sample in ['https://example.com/a','http://upload.wikimedia.org/a','https://upload.wikimedia.org.example.com/a','https://user@upload.wikimedia.org/a']:
    try:validated(sample)
    except ValueError:pass
    else:raise AssertionError('Unsafe asset URL accepted')
class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        validated(newurl)
        return super().redirect_request(req,fp,code,msg,headers,newurl)
opener=urllib.request.build_opener(SafeRedirect())
def read(url):
    req=urllib.request.Request(validated(url),headers={'User-Agent':'ReductionMonitor/1.0 (https://reduction.nyc)'})
    with opener.open(req,timeout=30) as response:
        validated(response.geturl())
        payload=response.read(2000001)
    if len(payload)>2000000:raise ValueError('Asset response too large')
    return payload
params={'action':'query','titles':'File:Powerade-logo-2019.svg','prop':'imageinfo','iiprop':'url|extmetadata','format':'json'}
result=json.loads(read('https://commons.wikimedia.org/w/api.php?'+urllib.parse.urlencode(params)))
info=next(iter(result['query']['pages'].values()))['imageinfo'][0]
url=validated(info['url']);payload=read(url)
png_header=bytes([137,80,78,71,13,10,26,10])
if payload.startswith(png_header):png=payload
else:
    svg=fromstring(payload)
    if svg.tag.rsplit('}',1)[-1].lower()!='svg':raise ValueError('Original asset is not SVG or PNG')
    for node in svg.iter():
        if node.tag.rsplit('}',1)[-1].lower() in ['script','foreignobject']:raise ValueError('Active SVG content rejected')
        for name,value in node.attrib.items():
            local=name.rsplit('}',1)[-1].lower()
            if local.startswith('on'):raise ValueError('SVG event handler rejected')
            if local=='href' and not value.startswith('#'):raise ValueError('External SVG reference rejected')
    for target in re.findall(r'url\(([^)]+)\)',payload.decode('utf-8',errors='replace'),flags=re.I):
        if not target.strip().strip('\"\'').startswith('#'):raise ValueError('External SVG CSS reference rejected')
    png=cairosvg.svg2png(bytestring=payload,output_width=240,unsafe=False)
if not png.startswith(png_header):raise ValueError('Converted asset is not PNG')
assets=base/'assets';assets.mkdir(exist_ok=True)
(assets/'powerade-logo.png').write_bytes(png)
(base/'data/powerade-logo.json').write_text(json.dumps({'source':'https://commons.wikimedia.org/wiki/File:Powerade-logo-2019.svg','asset_label':'Powerade-logo-2019.svg','original_url':url,'license_metadata':info.get('extmetadata',{}),'scope':'Sourced 2019 logo file; not verification of current brand guidelines or endorsement','processing':'Validated original asset converted to local PNG; no arbitrary external asset hosts'},indent=2))
print('Saved validated local logo from original asset host:',urllib.parse.urlparse(url).hostname)
