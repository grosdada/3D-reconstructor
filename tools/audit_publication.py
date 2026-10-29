"""Inspect candidate or staged Git blobs without printing possible secrets.

Heuristic defense, not a guarantee that every possible secret format is detected.
Run before commit. --staged audits the actual index, not just working-tree files.
"""
import ast
import base64
import io
import json
from pathlib import Path
import re
import subprocess
import sys
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[1]
STAGED = '--staged' in sys.argv
cmd = ['git', 'ls-files', '-z', '--cached']
if not STAGED:
    cmd += ['--others', '--exclude-standard']
paths = sorted(set(x for x in subprocess.check_output(cmd, cwd=ROOT).decode('utf8').split('\0') if x))
forbidden = {'.blend','.blend1','.blend2','.glb','.gltf','.fbx','.obj','.vdb','.exr','.hdr','.mp4','.mov','.zip','.pth','.pt','.safetensors','.pem','.key','.p12','.png','.jpg','.jpeg','.webp'}
ignored_roots = {'output','dist','vendor','.venv','.cache','test-output','__pycache__','.git'}
patterns = {
    'openai-shaped-key': r'\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{24,}',
    'github-shaped-token': r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})',
    'aws-access-key': r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b',
    'private-key': r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----',
    'literal-credential': r'''(?i)(?:api[_-]?key|access[_-]?token|password|client[_-]?secret)\s*[:=]\s*["'][A-Za-z0-9_+/=-]{20,}["']''',
}
findings=[];total=0;blobs={};pycount=0
for name in paths:
    p=Path(name)
    if p.parts[0] in ignored_roots or p.suffix.lower() in forbidden or p.name.startswith('.env'):
        findings.append({'file':name,'issue':'excluded artifact or sensitive filename'})
    blob = subprocess.check_output(['git','show',':'+name],cwd=ROOT) if STAGED else (ROOT/name).read_bytes()
    total+=len(blob);blobs[name]=blob
    if len(blob)>2_000_000:findings.append({'file':name,'issue':'over 2 MB'})
    try:text=blob.decode('utf-8-sig')
    except UnicodeDecodeError:
        findings.append({'file':name,'issue':'unexpected non-UTF8 binary'});continue
    # Images in the HTML are inspected below. Avoid random base64 false positives.
    scan=re.sub(r'data:image/jpeg;base64,[A-Za-z0-9+/=]+','<embedded-render>',text)
    for key,pattern in patterns.items():
        for m in re.finditer(pattern,scan):
            findings.append({'file':name,'line':scan.count('\n',0,m.start())+1,'issue':key})
    if p.suffix=='.py':
        try:ast.parse(text,filename=name);pycount+=1
        except SyntaxError as e:findings.append({'file':name,'line':e.lineno,'issue':'Python syntax'})

class Document(HTMLParser):
    def __init__(self):super().__init__();self.ids=[];self.links=[];self.images=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id' in a:self.ids.append(a['id'])
        if tag=='a' and 'href' in a:self.links.append(a['href'])
        if tag=='img':self.images.append(a)

html_name='docs/TRANSMISSION-CLAUDE.html'
if html_name in blobs:
    text=blobs[html_name].decode('utf8');doc=Document();doc.feed(text)
    if len(doc.ids)!=len(set(doc.ids)):findings.append({'file':html_name,'issue':'duplicate HTML ids'})
    for link in doc.links:
        if link.startswith('#') and link[1:] not in doc.ids:findings.append({'file':html_name,'issue':'broken anchor '+link})
        elif not link.startswith(('https://','http://','#')):
            target=(ROOT/'docs'/link.split('#')[0]).resolve()
            try:rel=target.relative_to(ROOT).as_posix()
            except ValueError:rel='outside-workspace'
            if rel not in blobs:findings.append({'file':html_name,'issue':'unpublished relative target '+link})
    if len(doc.images)!=6:findings.append({'file':html_name,'issue':'expected six illustrations'})
    for im in doc.images:
        if not im.get('alt') or not im.get('src','').startswith('data:image/jpeg;base64,'):findings.append({'file':html_name,'issue':'image missing alt or not embedded JPEG'});continue
        try:
            b=base64.b64decode(im['src'].split(',',1)[1],validate=True)
            assert b.startswith(b'\xff\xd8') and b.endswith(b'\xff\xd9')
        except Exception:findings.append({'file':html_name,'issue':'invalid JPEG payload'})
    if '@@' in text:findings.append({'file':html_name,'issue':'unresolved illustration placeholder'})
if total>10_000_000:findings.append({'issue':'publication exceeds 10 MB'})
print(json.dumps({'mode':'staged' if STAGED else 'candidate','files':len(paths),'bytes':total,'python_files_parsed':pycount,'findings':findings},indent=2))
sys.exit(bool(findings))
