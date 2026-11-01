"""Actual Umbrel installation: setup, settings, verified accounts and restart.

SMTP delivery is intentionally not tested here. The synthetic verification link
is read from the encrypted local outbox and is never written to logs or artifacts.
"""
import json
import os
import platform
from pathlib import Path
import subprocess
import time
from playwright.sync_api import expect, sync_playwright

host='putzonaut-umbrel-test'
app_id='denny-putzonaut'
origin='https://localhost:8876'
architecture={'x86_64':'amd64','aarch64':'arm64'}[platform.machine()]
assert architecture==os.environ['PUTZONAUT_TEST_ARCHITECTURE']
assert subprocess.check_output(['docker','exec',host,'uname','-m'],text=True).strip()==platform.machine()
evidence=Path('umbrel-evidence');evidence.mkdir(exist_ok=True)

def umbrel(*args):
    return subprocess.check_output(['docker','exec',host,'umbreld','client',*args],text=True)

def app_node(script):
    return subprocess.check_output(['docker','exec',host,'docker','exec',app_id+'_web_1','node','--input-type=module','-e',script],text=True).strip()

def settled(context, setup=False):
    for _ in range(60):
        try:
            response=context.request.get(origin+'/api/health',timeout=5000)
            if response.ok and (response.json().get('status')=='setup')==setup:
                return
        except Exception:
            pass
        time.sleep(2)
    raise AssertionError('Putzonaut did not reach the expected setup/running state.')

with sync_playwright() as p:
    browser=p.chromium.launch()
    context=browser.new_context(viewport={'width':390,'height':844})
    anonymous=context.request.get(origin,max_redirects=0)
    assert anonymous.status in [301,302,303,307,308,401,403], 'Umbrel authentication was bypassed'
    assert context.request.post('https://localhost/trpc/user.login',data={'password':'synthetic-umbrel-ci-password'},headers={'Origin':'https://localhost'}).ok
    settled(context,setup=True)
    page=context.new_page();page.goto(origin)
    expect(page.get_by_role('heading',name='Bereit für den ersten Start?')).to_be_visible()
    assert not page.evaluate('document.documentElement.scrollWidth > innerWidth+1'), 'Setup overflows a phone viewport'
    page.screenshot(path=str(evidence/'setup.png'),full_page=True)
    assert context.request.post(origin+'/api/account/sign-up/email',data={},headers={'Origin':origin}).status==503

    apps=json.loads(umbrel('apps.list.query'))
    installed=next(app for app in apps if app['id']==app_id)
    exposed={item['name'] for item in installed['environment']['exposed']}
    assert {'APP_ORIGIN','MAIL_FROM','SMTP_HOST','SMTP_PORT','SMTP_USER'}<=exposed
    assert 'SMTP_PASSWORD' not in exposed and 'BETTER_AUTH_SECRET' not in exposed
    values={'APP_ORIGIN':origin,'MAIL_FROM':'Putzonaut CI <sender@example.test>','SMTP_HOST':'mail.example.invalid','SMTP_PORT':'587','SMTP_USER':'synthetic-smtp-user'}
    umbrel('apps.setSettings.mutate','--appId',app_id,
           '--environment',json.dumps([{'name':k,'value':v} for k,v in values.items()]),
           '--customEnvironment',json.dumps([{'serviceName':'web','name':'SMTP_PASSWORD','value':'synthetic-smtp-password'}]))
    settled(context)
    page.goto(origin+'/konto/anmelden')
    expect(page.get_by_role('heading',name='Willkommen zurück')).to_be_visible()
    page.screenshot(path=str(evidence/'login.png'),full_page=True)

    headers={'Origin':origin,'Content-Type':'application/json'}
    def post(path,data):
        return context.request.post(origin+path,data=data,headers=headers)
    email='ci-crew@example.test'
    password='Synthetic long CI passphrase 2026!'
    assert post('/api/account/sign-up/email',{'name':'Alex','email':email,'password':password,'callbackURL':origin+'/konto/bestaetigt'}).status==200
    assert post('/api/account/sign-in/email',{'email':email,'password':password}).status==403
    assert post('/api/auth/setup',{'name':'Alex','householdName':'CI Sternencrew'}).status==401

    # Inspect only this disposable app's synthetic outbox; no real email is sent.
    verification=app_node("""
      import {DatabaseSync} from 'node:sqlite';
      import {createHash,createDecipheriv} from 'node:crypto';
      const db=new DatabaseSync('/data/accounts.sqlite');
      const row=db.prepare('SELECT payload FROM putzonaut_mail LIMIT 1').get();
      if(!row)process.exit(2);
      const payload=Buffer.from(row.payload,'base64');
      const key=createHash('sha256').update('putzonaut-mail-v1\\0'+process.env.BETTER_AUTH_SECRET).digest();
      const cipher=createDecipheriv('aes-256-gcm',key,payload.subarray(0,12));cipher.setAuthTag(payload.subarray(12,28));
      const message=JSON.parse(Buffer.concat([cipher.update(payload.subarray(28)),cipher.final()]).toString('utf8'));
      process.stdout.write(message.text.match(/https:\\/\\/\\S+/)[0]);db.close();
    """)
    try:
        verified=context.request.get(verification,max_redirects=0)
        assert verified.status in [200,302]
    except Exception:
        raise AssertionError('Synthetic email verification failed') from None
    finally:
        del verification
    assert post('/api/account/sign-in/email',{'email':email,'password':password,'rememberMe':True}).status==200
    assert post('/api/auth/setup',{'name':'Alex','householdName':'CI Sternencrew'}).status==201
    state=context.request.get(origin+'/api/state').json()
    assert state['user']['name']=='Alex'
    crew_id=state['household']['id']
    page.goto(origin+'/')
    expect(page.locator('body')).to_contain_text('Putzonaut')
    page.screenshot(path=str(evidence/'signed-in.png'),full_page=True)

    # Exercise an image update through Umbrel as well as a normal restart.
    # This is an idempotent update of the first package, not an older-version migration.
    umbrel('apps.update.mutate','--appId',app_id)
    settled(context)
    assert context.request.get(origin+'/api/state').json()['household']['id']==crew_id
    umbrel('apps.restart.mutate','--appId',app_id)
    settled(context)
    state=context.request.get(origin+'/api/state').json()
    assert state['household']['id']==crew_id and state['user']['name']=='Alex'
    assert json.loads(umbrel('apps.state.query','--appId',app_id))['state']=='ready'
    mounts=json.loads(subprocess.check_output(['docker','exec',host,'docker','inspect',app_id+'_web_1','--format','{{json .Mounts}}'],text=True))
    assert {(m['Destination'],m['RW']) for m in mounts if m['Type']!='tmpfs'}=={('/data',True),('/umbrel/entrypoint.mjs',False)}
    tmpfs=json.loads(subprocess.check_output(['docker','exec',host,'docker','inspect',app_id+'_web_1','--format','{{json .HostConfig.Tmpfs}}'],text=True))
    assert '/tmp' in tmpfs
    assert next(m for m in mounts if m['Destination']=='/data')['Source'].endswith('/denny-putzonaut/data')
    fresh=browser.new_context()
    assert fresh.request.post('https://localhost/trpc/user.login',data={'password':'synthetic-umbrel-ci-password'},headers={'Origin':'https://localhost'}).ok
    forged=fresh.request.get(origin+'/api/state',headers={'oai-authenticated-user-id':'forged','oai-authenticated-user-email':'forged@example.test'})
    assert forged.status==401
    fresh.close();context.close();browser.close()

(evidence/'result.json').write_text(json.dumps({'app':app_id,'version':'0.21.0','umbrel':'2.0.0','architecture':architecture,'freshInstall':True,'browserSetup':True,'nativeSettings':True,'emailVerification':'synthetic local outbox; no SMTP delivery','crewCreation':True,'sameVersionUpdate':True,'restartPersistence':True,'forgedIdentityRejected':True},indent=2)+'\n')
print('PASS: native Umbrel install, browser setup, account verification, crew creation, update and restart persistence.')
