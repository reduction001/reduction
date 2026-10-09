import pathlib,warnings
root=pathlib.Path(__file__).resolve().parents[1];path=root/'pipeline/finish_dashboard_details.py';code=path.read_text()
if 'acquire_powerade_logo.py' not in code:
    start=code.index('if not logo.exists():')
    end=code.index("e=json.loads((base/'data/powerade-editorial.json').read_text())",start)
    block="if not logo.exists() or not logo.read_bytes().startswith(bytes([137,80,78,71,13,10,26,10])):\n    import subprocess,sys\n    subprocess.run([sys.executable,str(root/'pipeline/acquire_powerade_logo.py')],check=True)\n"
    code=code[:start]+block+code[end:]
code=code.replace("block='''","block=r'''")
with warnings.catch_warnings():
    warnings.simplefilter('error',SyntaxWarning)
    compile(code,str(path),'exec')
path.write_text(code)
print('Logo collector patched; generated QA code uses raw strings. No deployment.')
