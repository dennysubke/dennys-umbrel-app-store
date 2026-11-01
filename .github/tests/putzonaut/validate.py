"""Static package checks; live installation is a separate required job."""
import re
from pathlib import Path
import yaml

root=Path('denny-putzonaut')
manifest=yaml.safe_load((root/'umbrel-app.yml').read_text())
compose=yaml.safe_load((root/'docker-compose.yml').read_text())
assert manifest['id']==root.name
assert str(manifest['manifestVersion'])=='2.0' and manifest['requiresHttps']
assert manifest['storage']=={'dataRoot':'data'}
assert manifest['version']=='0.21.0'
assert manifest['port']==8876
assert manifest['submission']=='https://github.com/dennysubke/dennys-umbrel-app-store/pull/100'
assert not manifest.get('permissions') and not manifest.get('dependencies')
names=[v['name'] for v in manifest['environment']]
assert len(names)==len(set(names)) and 'SMTP_PASSWORD' not in names and 'BETTER_AUTH_SECRET' not in names
assert all(v['services']==['web'] for v in manifest['environment'])
web=compose['services']['web']
assert re.fullmatch(r'ghcr.io/putzonaut/putzonaut:0\.21\.0-[a-f0-9]{12}@sha256:[a-f0-9]{64}',web['image'])
assert web['user']=='1000:1000' and web['read_only'] and web['cap_drop']==['ALL']
assert not any(k in web for k in ['privileged','network_mode','ports','build','devices'])
assert web['volumes']==['${APP_DATA_DIR}/data:/data','${APP_DATA_DIR}/hooks/entrypoint.mjs:/umbrel/entrypoint.mjs:ro']
assert (root/'data/.gitkeep').is_file() and (root/'hooks/entrypoint.mjs').is_file()
assert web['environment']['BETTER_AUTH_SECRET']=='${APP_SEED}'
assert web['environment']['SMTP_PASSWORD']==''
assert compose['services']['app_proxy']['environment']=={'APP_HOST':'denny-putzonaut_web_1','APP_PORT':3080}
assert 'networks' not in compose
for path in Path('.').glob('*/umbrel-app.yml'):
    if path.parent==root: continue
    other=yaml.safe_load(path.read_text())
    assert other.get('port')!=manifest['port'], f'Port conflict with {path}'
print('PASS: manifest, persistent app storage, secret-free defaults, update path, and port isolation.')
