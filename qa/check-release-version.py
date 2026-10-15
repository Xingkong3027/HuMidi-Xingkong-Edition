"""Check locked application versions and an optional exact Xingkong tag, without network access."""
from pathlib import Path
import json, re, subprocess, sys, tomllib
root = Path(__file__).resolve().parent.parent
package = json.loads((root/'package.json').read_text(encoding='utf-8'))
lock = json.loads((root/'package-lock.json').read_text(encoding='utf-8'))
cargo = tomllib.loads((root/'src-tauri/Cargo.toml').read_text(encoding='utf-8'))
cargo_lock = tomllib.loads((root/'src-tauri/Cargo.lock').read_text(encoding='utf-8'))
versions = {
    'package.json':package['version'], 'package-lock.json':lock['version'],
    'package-lock root':lock['packages']['']['version'],
    'tauri.conf.json':json.loads((root/'src-tauri/tauri.conf.json').read_text(encoding='utf-8'))['version'],
    'Cargo.toml':cargo['package']['version'],
    'Cargo.lock':next(p['version'] for p in cargo_lock['package'] if p['name']==cargo['package']['name']),
}
version=package['version']
if not re.fullmatch(r'\d+\.\d+\.\d+-xk\.\d+', version) or set(versions.values())!={version}:
    raise SystemExit('Application version mismatch: '+json.dumps(versions))
if len(sys.argv)>1:
    tag=sys.argv[1]
    if tag!='v'+version: raise SystemExit('Tag does not match application version: '+tag)
    tagged=subprocess.check_output(['git','rev-parse','--verify',f'refs/tags/{tag}^{{commit}}'],cwd=root,text=True).strip()
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
    if tagged!=head: raise SystemExit('Checkout is not the requested tagged commit')
print('Application versions match: '+version)
