"""Collect original notices from locked Windows Rust dependencies and production npm packages."""
from pathlib import Path
import json, subprocess, sys
root=Path(__file__).resolve().parent.parent
output=root/'LICENSES'
output.mkdir(exist_ok=True)
if len(sys.argv)>1:
    metadata=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8-sig'))
else:
    metadata=json.loads(subprocess.check_output(['cargo','metadata','--manifest-path','src-tauri/Cargo.toml','--locked','--filter-platform','x86_64-pc-windows-msvc','--format-version','1'],cwd=root,text=True,encoding='utf-8'))
inventory=[]
missing=[]
def notices(folder,extra):
    paths=set()
    for p in folder.iterdir():
        if p.is_file() and p.name.upper().startswith(('LICENSE','LICENCE','COPYING','NOTICE','COPYRIGHT','UNLICENSE')): paths.add(p)
        if p.is_dir() and p.name.lower() in ('licenses','licences'): paths.update(x for x in p.rglob('*') if x.is_file())
    if extra and (folder/extra).is_file(): paths.add(folder/extra)
    return sorted(paths)
def collect(kind,packages):
    parts=['Original dependency copyright and license texts. Headings identify source and version.\n']
    for name,version,license_name,repository,folder,extra in packages:
        files=notices(folder,extra)
        fallback=output/'upstream'/(name+'-'+version+'.json')
        upstream=json.loads(fallback.read_text(encoding='utf-8')) if not files and fallback.is_file() else None
        inventory.append({'ecosystem':kind,'name':name,'version':version,'license':license_name,'repository':repository,'notice_files':[p.relative_to(folder).as_posix() for p in files], 'upstream_notice_sources':[p['url'] for p in upstream['files']] if upstream else []})
        if not files and not upstream: missing.append(kind+':'+name+'@'+version)
        parts.append('\n'+'='*72+f'\n{name} {version}\nLicense: {license_name}\nSource: {repository}\n')
        for p in files: parts.append(f'\n--- {p.relative_to(folder).as_posix()} ---\n'+p.read_text(encoding='utf-8',errors='replace')+'\n')
        if upstream:
            parts.append('Upstream source revision: '+upstream['repository_commit']+'\n')
            for p in upstream['files']: parts.append('\n--- '+p['name']+' ---\nSource: '+p['url']+'\n'+p['text']+'\n')
    (output/f'{kind.upper()}-DEPENDENCIES.txt').write_text(''.join(parts),encoding='utf-8')
rust=[(p['name'],p['version'],p.get('license'),p.get('repository'),Path(p['manifest_path']).parent,p.get('license_file')) for p in metadata['packages'] if p.get('source')]
collect('rust',sorted(rust,key=lambda p:(p[0],p[1])))
lock=json.loads((root/'package-lock.json').read_text(encoding='utf-8'))
npm=[]
for location,p in lock['packages'].items():
    if not location or p.get('dev'): continue
    folder=root/location
    if not folder.is_dir(): continue
    info=json.loads((folder/'package.json').read_text(encoding='utf-8'))
    repository=info.get('repository','')
    if isinstance(repository,dict): repository=repository.get('url','')
    npm.append((info['name'],info['version'],info.get('license'),repository,folder,None))
collect('npm',sorted(npm,key=lambda p:(p[0],p[1])))
(output/'DEPENDENCIES.json').write_text(json.dumps({'target':'x86_64-pc-windows-msvc','scope':'Resolved Rust packages including build/test dependencies; installed production npm packages','packages':inventory,'missing_notice_texts':missing},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'packages':len(inventory),'without_notice_texts':missing},ensure_ascii=False))
if missing: raise SystemExit('Some package notice texts need review before redistribution')
