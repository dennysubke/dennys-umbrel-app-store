#!/usr/bin/env bash
set -euo pipefail
test_container=moinpdf-umbrel-test

ready=false
for attempt in $(seq 1 120); do
    if docker exec "$test_container" umbreld client user.exists.query >/dev/null 2>&1; then
        ready=true
        break
    fi
    sleep 5
done
if [ "$ready" != true ]; then
    echo 'Umbrel did not become ready within 10 minutes.' >&2
    exit 1
fi
docker exec "$test_container" docker info --format 'driver={{.Driver}} root={{.DockerRootDir}}'
storage_driver="$(docker exec "$test_container" docker info --format '{{.Driver}}')"
if [ "$storage_driver" = vfs ]; then
    echo 'The disposable Docker host selected space-amplifying VFS storage; use a host supporting overlay storage.' >&2
    exit 1
fi
df -h /
docker exec "$test_container" df -h /var/lib/docker /var/lib/containerd /home/umbrel/umbrel
docker exec "$test_container" umbreld client user.register.mutate \
    --name MoinPDF-CI --password synthetic-umbrel-ci-password >/dev/null

# Follow Umbrel's own integration-test approach: register a small HTTP Git
# community repository via the public app-store API. Only the rendered app
# package is served, on runner loopback; the private source repo is excluded.
ci_store="${RUNNER_TEMP:-/tmp}/moinpdf-umbrel-ci-store"
repository="$ci_store/repositories/umbrel-apps.git"
mkdir -p "$repository"
cp -R "${MOINPDF_UPGRADE_FROM:-denny-moinpdf}" "$repository/denny-moinpdf"
printf 'id: denny\nname: MoinPDF CI\n' > "$repository/umbrel-app-store.yml"
git -C "$repository" init --initial-branch=main --quiet
git -C "$repository" add .
git -C "$repository" -c user.name=MoinPDF-CI -c user.email=ci@example.invalid \
    commit --quiet -m 'Exact published MoinPDF package'
npm install --prefix "$ci_store" --ignore-scripts --no-audit --no-fund \
    --save-exact node-git-server@1.0.0
node .github/tests/moinpdf/umbrel-git-server.cjs "$ci_store" > "$ci_store/server.log" 2>&1 &
printf '%s\n' "$!" > "$ci_store/server.pid"
for attempt in $(seq 1 30); do
    if [ -s "$ci_store/url" ]; then break; fi
    sleep 1
done
store_url="$(cat "$ci_store/url")"
git ls-remote "$store_url" HEAD >/dev/null
echo 'Registering the local CI community store through Umbrel.'
timeout 180 docker exec "$test_container" umbreld client appStore.addRepository.mutate \
    --url "$store_url"
# Umbrel's CLI calls process.exit immediately after console.log. Redirect its
# large JSON to a regular file inside the container so Node flushes it before
# exit; direct Docker pipes otherwise truncate the registry at about 64 KiB.
docker exec "$test_container" sh -ec \
    'umbreld client appStore.registry.query > /tmp/moinpdf-ci-registry.json; cat /tmp/moinpdf-ci-registry.json' \
    > /tmp/umbrel-ci-registry.json
python - <<'PYREGISTRY'
import json
registry = json.load(open('/tmp/umbrel-ci-registry.json'))
assert any(app['id'] == 'denny-moinpdf' for store in registry for app in store['apps']), [
    {'store': store['meta'], 'apps': len(store['apps'])} for store in registry]
PYREGISTRY
echo 'MoinPDF is visible in the native Umbrel registry.'
# This API waits for the full image download and installation. Allow the same
# 20-minute budget as the install-state check, and report progress meanwhile.
timeout 1200 docker exec "$test_container" umbreld client apps.install.mutate \
    --appId denny-moinpdf > /tmp/umbrel-ci-install.log 2>&1 &
install_pid=$!
while kill -0 "$install_pid" 2>/dev/null; do
    if timeout 30 docker exec "$test_container" umbreld client apps.state.query \
        --appId denny-moinpdf > /tmp/umbrel-ci-state.json; then
        python - <<'PYSTATE'
import json
state = json.load(open('/tmp/umbrel-ci-state.json'))
print('Installation:', state.get('state'), 'progress:', state.get('progress', state.get('stateProgress')))
PYSTATE
    fi
    sleep 15
done
if ! wait "$install_pid"; then
    cat /tmp/umbrel-ci-install.log >&2
    echo 'The native Umbrel installation failed or exceeded 20 minutes.' >&2
    exit 1
fi

for attempt in $(seq 1 240); do
    docker exec "$test_container" umbreld client apps.state.query --appId denny-moinpdf > /tmp/umbrel-ci-state.json
    if python -c 'import json; assert json.load(open("/tmp/umbrel-ci-state.json"))["state"] == "ready"' 2>/dev/null; then
        echo 'Umbrel reports MoinPDF ready; browser and document workflows are checked next.'
        if [ -n "${MOINPDF_UPGRADE_FROM:-}" ]; then
            bash .github/tests/moinpdf/umbrel-upgrade.sh "$repository"
        fi
        exit 0
    fi
    if [ "$((attempt % 6))" -eq 0 ]; then
        python -c 'import json; print("Installation state:", json.load(open("/tmp/umbrel-ci-state.json"))["state"])'
    fi
    sleep 5
done
echo 'Umbrel did not finish installing MoinPDF within 20 minutes.' >&2
exit 1
