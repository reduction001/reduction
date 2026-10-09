import pathlib
root=pathlib.Path(__file__).resolve().parents[1]
collector=root/'pipeline/signals_monitor.py'
text=collector.read_text()
bad="lambda m:'<article class=\"card\">'+body+'</article>'"
text=text.replace(bad,'lambda m:body')
collector.write_text(text)
page=root/'public/dashboards/powerade/index.html'
text=page.read_text()
start='<article class="card"><article class="card"><h2>Attention pulse</h2>'
while start in text:
    begin=text.index(start)
    end=text.index('</article></article>',begin)
    text=text[:begin]+text[begin:end].replace('<article class="card"><article class="card">','<article class="card">',1)+'</article>'+text[end+len('</article></article>'):]
page.write_text(text)
assert start not in text
assert bad not in collector.read_text()
print('Attention card repaired in collector and generated page.')
