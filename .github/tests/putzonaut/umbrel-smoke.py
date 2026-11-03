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
from recurrence_browser import check_recurrences, assert_recurrences
from everyday_browser import check_everyday

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

def mail_link_for(recipient, subject):
    # Only the disposable installation's synthetic outbox; never log the link.
    return app_node("""
      import {DatabaseSync} from 'node:sqlite';
      import {createHash,createDecipheriv} from 'node:crypto';
      const db=new DatabaseSync('/data/accounts.sqlite');
      const key=createHash('sha256').update('putzonaut-mail-v1\\0'+process.env.BETTER_AUTH_SECRET).digest();
      const target="""+json.dumps({'to':recipient,'subject':subject})+""";
      for(const row of db.prepare('SELECT payload FROM putzonaut_mail ORDER BY rowid DESC').all()){
        const payload=Buffer.from(row.payload,'base64');
        const cipher=createDecipheriv('aes-256-gcm',key,payload.subarray(0,12));cipher.setAuthTag(payload.subarray(12,28));
        const message=JSON.parse(Buffer.concat([cipher.update(payload.subarray(28)),cipher.final()]).toString('utf8'));
        if(message.to===target.to&&message.subject===target.subject){
          process.stdout.write(message.text.match(/https:\\/\\/\\S+/)[0]);db.close();process.exit(0);
        }
      }
      db.close();process.exit(2);
    """)

def check_website(expected_origin):
    result=app_node("""
      import assert from 'node:assert/strict';
      import {request} from 'node:http';
      const base='http://127.0.0.1:3081';
      const page=await fetch(base);assert.equal(page.status,200);
      const html=await page.text();assert.ok(html.includes('Hochglanzkurs.'));
      assert.ok(html.includes('sos@putzonaut.de'));
      assert.ok(html.includes(process.env.APP_ORIGIN));assert.ok(!html.includes('__APP_ORIGIN__'));
      assert.equal(page.headers.get('set-cookie'),null);
      assert.equal((await fetch(base+'/healthz')).status,200);
      for(const path of ['/app-qr.svg','/website-assets/screens/home.svg','/website-assets/putzonaut-rocket.webp','/website-assets/site.js','/website-assets/glass.css','/website-assets/features.css','/website-assets/mascot.css','/website-assets/fonts/nunito-900.woff2','/impressum','/datenschutz'])assert.equal((await fetch(base+path)).status,200,path);
      for(const path of ['/api/state','/api/account/get-session','/sw.js','/.env'])assert.equal((await fetch(base+path)).status,404,path);
      assert.equal((await fetch(base+'/api/auth/setup',{method:'POST'})).status,405);
      const redirect=await new Promise((resolve,reject)=>{const req=request(base+'/datenschutz',{headers:{host:'www.'+new URL(process.env.WEBSITE_ORIGIN).host}},res=>{res.resume();res.on('end',()=>resolve({status:res.statusCode,location:res.headers.location}));});req.on('error',reject);req.end();});
      assert.equal(redirect.status,308);assert.equal(redirect.location,process.env.WEBSITE_ORIGIN+'/datenschutz');
      console.log(JSON.stringify({appOrigin:process.env.APP_ORIGIN,website:true}));
    """)
    parsed=json.loads(result)
    assert parsed['website'] is True and parsed['appOrigin'].startswith('https://')
    if expected_origin is not None:
        assert parsed['appOrigin']==expected_origin

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
    check_website(None)
    page=context.new_page();page.goto(origin)
    expect(page.get_by_role('heading',name='Bereit für den ersten Start?')).to_be_visible()
    assert not page.evaluate('document.documentElement.scrollWidth > innerWidth+1'), 'Setup overflows a phone viewport'
    page.screenshot(path=str(evidence/'setup.png'),full_page=True)
    assert context.request.post(origin+'/api/account/sign-up/email',data={},headers={'Origin':origin}).status==503

    apps=json.loads(umbrel('apps.list.query'))
    installed=next(app for app in apps if app['id']==app_id)
    exposed={item['name'] for item in installed['environment']['exposed']}
    assert {'APP_ORIGIN','WEBSITE_ORIGIN','MAIL_FROM','SMTP_HOST','SMTP_PORT','SMTP_USER'}<=exposed
    assert 'SMTP_PASSWORD' not in exposed and 'BETTER_AUTH_SECRET' not in exposed
    values={'APP_ORIGIN':origin,'WEBSITE_ORIGIN':'https://site.example.test','MAIL_FROM':'Putzonaut CI <sender@example.test>','SMTP_HOST':'mail.example.invalid','SMTP_PORT':'587','SMTP_USER':'synthetic-smtp-user'}
    umbrel('apps.setSettings.mutate','--appId',app_id,
           '--environment',json.dumps([{'name':k,'value':v} for k,v in values.items()]),
           '--customEnvironment',json.dumps([{'serviceName':'web','name':'SMTP_PASSWORD','value':'synthetic-smtp-password'}]))
    settled(context)
    check_website(origin)
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

    verification=mail_link_for(email,'Bestätige deine E-Mail für Putzonaut')
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
    expect(page.get_by_role('heading',name='Hey, Alex!',exact=True)).to_be_visible(timeout=20000)
    expect(page.locator('.launch-screen')).to_have_count(0,timeout=20000)
    expect(page.get_by_role('navigation',name='Hauptnavigation')).to_be_visible()
    expect(page.locator('main')).to_contain_text('CI Sternencrew')
    assert not page.evaluate('document.documentElement.scrollWidth > innerWidth+1'), 'Signed-in app overflows a phone viewport'
    page.screenshot(path=str(evidence/'signed-in.png'),full_page=True)
    try:
        calendar_rules=check_recurrences(page,context,origin,evidence)
        calendar_rules.update(check_everyday(page,context,origin,evidence))
    except Exception:
        page.screenshot(path=str(evidence/'recurrence-failure.png'),full_page=True)
        raise

    push=context.request.get(origin+'/api/push').json()
    assert push['configured'] is True and push['publicKey'] and 'privateJwk' not in push
    push_key=push['publicKey']
    assert post('/api/push/dispatch',{}).status==404

    # Exercise the new account screen through the actual installed production app.
    page.goto(origin+'/konto/verwalten')
    expect(page.get_by_role('heading',name='Dein Konto',exact=True)).to_be_visible()
    expect(page.get_by_text(email,exact=True)).to_be_visible()
    page.locator('summary',has_text='Login-E-Mail ändern').click()
    page.locator('summary',has_text='Konto löschen').click()
    expect(page.get_by_role('link',name='Zur Crew-Verwaltung')).to_be_visible()
    expect(page.get_by_role('button',name='Konto endgültig löschen')).to_have_count(0)
    assert not page.evaluate('document.documentElement.scrollWidth > innerWidth+1'), 'Account settings overflow a phone viewport'
    page.screenshot(path=str(evidence/'account-mobile.png'),full_page=True)
    page.set_viewport_size({'width':1280,'height':900})
    assert not page.evaluate('document.documentElement.scrollWidth > innerWidth+1'), 'Account settings overflow a desktop viewport'
    page.screenshot(path=str(evidence/'account-desktop.png'),full_page=True)
    page.set_viewport_size({'width':390,'height':844})
    new_email='ci-new-login@example.test'
    page.get_by_label('Neue E-Mail-Adresse',exact=True).fill(new_email)
    page.get_by_label('Aktuelles Passwort',exact=True).fill('incorrect')
    page.get_by_role('button',name='Bestätigungslink senden').click()
    expect(page.get_by_role('alert')).to_have_text('Das aktuelle Passwort stimmt nicht.')
    page.get_by_label('Aktuelles Passwort',exact=True).fill(password)
    page.get_by_role('button',name='Bestätigungslink senden').click()
    expect(page.get_by_role('status')).to_contain_text('Bis zur Bestätigung bleibt die bisherige Adresse gültig.')
    assert context.request.get(origin+'/api/account/manage').json()['email']==email
    verification=mail_link_for(new_email,'Bestätige deine neue Putzonaut-Adresse')
    try:
        page.goto(verification)
        expect(page.get_by_role('heading',name='Neue Adresse bestätigt.',exact=True)).to_be_visible()
    except Exception:
        raise AssertionError('Synthetic new-email confirmation failed') from None
    finally:
        del verification
    assert context.request.get(origin+'/api/state').status==401
    page.get_by_role('link',name='Zur Anmeldung').click()
    page.get_by_label('E-Mail-Adresse',exact=True).fill(new_email)
    page.get_by_label('Passwort',exact=True).fill(password)
    page.get_by_role('button',name='Anmelden',exact=True).click()
    # Returning users keep their last app section (the recurrence test used Missions).
    expect(page.get_by_role('navigation',name='Hauptnavigation')).to_be_visible(timeout=20000)
    page.get_by_role('navigation',name='Hauptnavigation').get_by_role('button',name='Basis',exact=True).click()
    expect(page.get_by_role('heading',name='Hey, Alex!',exact=True)).to_be_visible(timeout=20000)
    assert context.request.get(origin+'/api/state').json()['household']['id']==crew_id

    # Exercise an image update through Umbrel as well as a normal restart.
    # This is an idempotent update of the first package, not an older-version migration.
    umbrel('apps.update.mutate','--appId',app_id)
    settled(context)
    assert context.request.get(origin+'/api/state').json()['household']['id']==crew_id
    umbrel('apps.restart.mutate','--appId',app_id)
    settled(context)
    state=context.request.get(origin+'/api/state').json()
    assert state['household']['id']==crew_id and state['user']['name']=='Alex'
    assert_recurrences(context,origin,calendar_rules)
    assert context.request.get(origin+'/api/push').json()['publicKey']==push_key
    assert json.loads(umbrel('apps.state.query','--appId',app_id))['state']=='ready'
    check_website(origin)
    mounts=json.loads(subprocess.check_output(['docker','exec',host,'docker','inspect',app_id+'_web_1','--format','{{json .Mounts}}'],text=True))
    assert {(m['Destination'],m['RW']) for m in mounts if m['Type']!='tmpfs'}=={('/data',True),('/umbrel/entrypoint.mjs',False)}
    tmpfs=json.loads(subprocess.check_output(['docker','exec',host,'docker','inspect',app_id+'_web_1','--format','{{json .HostConfig.Tmpfs}}'],text=True))
    assert '/tmp' in tmpfs
    assert next(m for m in mounts if m['Destination']=='/data')['Source'].endswith('/denny-putzonaut/data')
    fresh=browser.new_context()
    assert fresh.request.post('https://localhost/trpc/user.login',data={'password':'synthetic-umbrel-ci-password'},headers={'Origin':'https://localhost'}).ok
    forged=fresh.request.get(origin+'/api/state',headers={'oai-authenticated-user-id':'forged','oai-authenticated-user-email':'forged@example.test'})
    assert forged.status==401

    assert post('/api/household/close',{'confirmation':'CI Sternencrew'}).status==200
    page.goto(origin+'/konto/verwalten')
    page.locator('summary',has_text='Konto löschen').click()
    page.locator('input[name="delete-password"]').fill(password)
    page.get_by_label('Zur Bestätigung: KONTO LÖSCHEN',exact=True).fill('KONTO LÖSCHEN')
    page.get_by_role('checkbox').check()
    assert not page.evaluate('document.documentElement.scrollWidth > innerWidth+1'), 'Account deletion overflows a phone viewport'
    page.screenshot(path=str(evidence/'account-delete.png'),full_page=True)
    page.get_by_role('button',name='Konto endgültig löschen',exact=True).click()
    expect(page.get_by_role('heading',name='Dein Konto ist gelöscht.',exact=True)).to_be_visible()
    assert context.request.get(origin+'/api/account/manage').status==401
    assert post('/api/account/sign-in/email',{'email':new_email,'password':password}).status==401
    fresh.close();context.close();browser.close()

(evidence/'result.json').write_text(json.dumps({'app':app_id,'version':'0.25.1','umbrel':'2.0.0','architecture':architecture,'freshInstall':True,'browserSetup':True,'nativeSettings':True,'websiteDuringSetup':True,'websiteIsolation':True,'websiteAfterRestart':True,'emailVerification':'synthetic local outbox; no SMTP delivery','crewCreation':True,'sameVersionUpdate':True,'restartPersistence':True,'forgedIdentityRejected':True,'accountMobileAndDesktop':True,'emailChangePreservesCrew':True,'accountDeletion':True,'persistentPushConfiguration':True,'calendarRecurrenceEditor':True,'recurrenceDraftAndDuplicate':True,'recurrenceAfterRestart':True,'seasonDraftCopyAndBackup':True,'omitWithoutPoints':True,'roomOrder':True,'missionReactions':True,'reducedMotion':True},indent=2)+'\n')
print('PASS: native Umbrel install, browser setup, email change, account deletion, push configuration, update and restart persistence.')
