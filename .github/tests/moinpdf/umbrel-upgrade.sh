#!/usr/bin/env bash
set -euo pipefail
repository="$1"
test_container=moinpdf-umbrel-test
mkdir -p umbrel-evidence

# Verify that this really is an installed old version before replacing the store.
docker exec "$test_container" sh -ec \
    'umbreld client apps.list.query > /tmp/moinpdf-installed.json; cat /tmp/moinpdf-installed.json' \
    > /tmp/moinpdf-installed.json
python - <<'PY'
import json
apps = json.load(open('/tmp/moinpdf-installed.json'))
assert next(app for app in apps if app['id'] == 'denny-moinpdf')['version'] == '0.15.4', apps
PY

# Synthetic existing data must survive the native update. Keep credentials out
# of logs: compare only a hash of the internal key inside the disposable host.
docker exec "$test_container" sh -ec \
    'printf "synthetic pre-upgrade data\n" > /home/umbrel/umbrel/app-data/denny-moinpdf/data/trust/upgrade-marker.txt'
docker exec "$test_container" docker exec denny-moinpdf_documents_1 \
    python -c 'import hashlib,os; print(hashlib.sha256(os.environ["MOINPDF_API_KEY"].encode()).hexdigest())' \
    > /tmp/moinpdf-key-before.sha256

cp -R denny-moinpdf/. "$repository/denny-moinpdf/"
git -C "$repository" add denny-moinpdf
git -C "$repository" -c user.name=MoinPDF-CI -c user.email=ci@example.invalid \
    commit --quiet -m 'Update to the exact candidate MoinPDF package'

# Let Umbrel refresh its community store normally (its polling interval is 5m).
ready=false
for attempt in $(seq 1 90); do
    docker exec "$test_container" sh -ec \
        'umbreld client appStore.registry.query > /tmp/moinpdf-upgrade-registry.json; cat /tmp/moinpdf-upgrade-registry.json' \
        > /tmp/moinpdf-upgrade-registry.json
    if python - <<'PY' 2>/dev/null
import json, re
from pathlib import Path
version = re.search(r'^version: "([^"]+)"$', Path('denny-moinpdf/umbrel-app.yml').read_text(), re.M).group(1)
registry = json.load(open('/tmp/moinpdf-upgrade-registry.json'))
assert any(app['id'] == 'denny-moinpdf' and app['version'] == version for store in registry for app in store['apps'])
PY
    then
        ready=true
        break
    fi
    sleep 5
done
if [ "$ready" != true ]; then
    echo 'Umbrel did not discover the candidate community-store update.' >&2
    exit 1
fi

timeout 1200 docker exec "$test_container" umbreld client apps.update.mutate --appId denny-moinpdf
docker exec "$test_container" sh -ec \
    'umbreld client apps.list.query > /tmp/moinpdf-installed.json; cat /tmp/moinpdf-installed.json' \
    > /tmp/moinpdf-installed.json
python - <<'PY'
import json, re
from pathlib import Path
version = re.search(r'^version: "([^"]+)"$', Path('denny-moinpdf/umbrel-app.yml').read_text(), re.M).group(1)
apps = json.load(open('/tmp/moinpdf-installed.json'))
assert next(app for app in apps if app['id'] == 'denny-moinpdf')['version'] == version, apps
Path('umbrel-evidence/upgrade.json').write_text(json.dumps({'from': '0.15.4', 'to': version, 'nativeUpdate': True}, indent=2) + '\n')
PY
docker exec "$test_container" sh -ec \
    'test "$(cat /home/umbrel/umbrel/app-data/denny-moinpdf/data/trust/upgrade-marker.txt)" = "synthetic pre-upgrade data"'
docker exec "$test_container" docker exec denny-moinpdf_documents_1 \
    python -c 'import hashlib,os; print(hashlib.sha256(os.environ["MOINPDF_API_KEY"].encode()).hexdigest())' \
    > /tmp/moinpdf-key-after.sha256
cmp /tmp/moinpdf-key-before.sha256 /tmp/moinpdf-key-after.sha256
echo 'PASS: native Umbrel update from 0.15.4; existing data and internal credential preserved.'
