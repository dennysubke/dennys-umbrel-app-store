"""Real installed UI: optional seasons, omission, room order and decorative reactions."""
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from playwright.sync_api import expect


def check_everyday(page, context, origin, evidence):
    def state():
        return context.request.get(origin+'/api/state').json()

    def post(path, data):
        response=context.request.post(origin+'/api'+path,data=data,headers={'Origin':origin})
        assert response.status==200, response.text()
        return response.json()

    def motion(enabled):
        response=context.request.patch(origin+'/api/profile/motion',data={'enabled':enabled},headers={'Origin':origin})
        assert response.status==200

    def reload_missions():
        page.goto(origin+'/')
        expect(page.get_by_role('navigation',name='Hauptnavigation')).to_be_visible(timeout=20000)
        page.get_by_role('navigation',name='Hauptnavigation').get_by_role('button',name='Missionen',exact=True).click()
        page.get_by_role('button',name=re.compile(r'^Jetzt offen')).click()

    def save(label='Mission hinzufügen'):
        with page.expect_response(lambda r:'/api/tasks' in r.url and r.request.method=='POST') as response:
            page.get_by_role('button',name=label,exact=True).click()
        assert response.value.status==200
        expect(page.locator('dialog[open]')).to_have_count(0)
        return response.value.json()['id']

    def capture(name):
        assert not page.evaluate('document.documentElement.scrollWidth > innerWidth+1'), 'Everyday UI overflows viewport'
        if page.locator('dialog[open]').count():
            assert page.locator('dialog[open]').evaluate('(el)=>el.scrollWidth<=el.clientWidth+1')
        page.screenshot(path=str(evidence/name),full_page=True)

    initial=state()
    today=datetime.fromisoformat(initial['syncedAt'].replace('Z','+00:00')).astimezone(ZoneInfo('Europe/Berlin')).date()
    year=today.year+1
    before=(initial['user']['xp'],initial['user']['stars'],initial['completedCount'])
    expected={}
    page.get_by_role('button',name='Eigene Mission erstellen',exact=True).click()
    page.get_by_label('Was gibt es zu tun?',exact=True).fill('CI Saisonpflanzen')
    page.get_by_label(re.compile(r'^Wie oft\?')).select_option('daily')
    page.get_by_label('Startdatum',exact=True).fill(f'{year}-01-01')
    expect(page.locator('.season-options')).not_to_have_attribute('open','')
    page.locator('.season-options summary').click()
    page.get_by_role('checkbox',name='Nur in ausgewählten Monaten',exact=True).check()
    months=page.get_by_role('group',name='Aktive Monate',exact=True)
    for button in months.get_by_role('button').all():
        button.click()
    expect(page.get_by_role('button',name='Mission hinzufügen',exact=True)).to_be_disabled()
    expect(page.get_by_role('alert')).to_contain_text('mindestens einen')
    for month in ['Apr','Mai','Jun','Jul','Aug','Sep']:
        months.get_by_role('button',name=month,exact=True).click()
    expect(page.locator('.recurrence-preview')).to_contain_text(f'01.04.{year}')
    page.set_viewport_size({'width':360,'height':800})
    months.scroll_into_view_if_needed()
    capture('season-mobile.png')
    page.set_viewport_size({'width':1280,'height':900})
    capture('season-desktop.png')
    page.set_viewport_size({'width':390,'height':844})
    page.get_by_role('button',name='Schließen',exact=True).click()
    page.get_by_role('button',name='Eigene Mission erstellen',exact=True).click()
    page.get_by_role('button',name='Entwurf fortsetzen',exact=True).click()
    expect(page.get_by_role('checkbox',name='Nur in ausgewählten Monaten')).to_be_checked()
    expect(months.get_by_role('button',name='Apr',exact=True)).to_have_attribute('aria-pressed','true')
    expect(months.get_by_role('button',name='Okt',exact=True)).to_have_attribute('aria-pressed','false')
    seasonal_id=save()
    expected[seasonal_id]={'cadence':'daily','schedule':{'startDate':f'{year}-01-01','activeMonths':[4,5,6,7,8,9]},'nextDueDate':f'{year}-04-01'}
    page.get_by_role('button',name=re.compile(r'^Demnächst')).click()
    page.get_by_role('button',name='CI Saisonpflanzen · Details',exact=True).click()
    page.get_by_role('button',name='Mission duplizieren',exact=True).click()
    expect(page.get_by_role('checkbox',name='Nur in ausgewählten Monaten')).to_be_checked()
    expect(months.get_by_role('button',name='Mai',exact=True)).to_have_attribute('aria-pressed','true')
    copied_id=save()
    expected[copied_id]={'cadence':'daily','schedule':{'startDate':today.isoformat(),'activeMonths':[4,5,6,7,8,9]}}

    def create(title, icon='sparkles', category='tidy', room='household', minutes=2):
        return post('/tasks',{'title':title,'icon':icon,'category':category,'areaId':room,'room':'Haushalt','cadence':'daily','minutes':minutes,'xp':20,'stars':5,'assignedTo':initial['user']['id'],'schedule':{'startDate':today.isoformat()}})['id']

    omit_id=create('CI Heute nicht nötig')
    reload_missions()
    page.get_by_role('button',name='CI Heute nicht nötig · Details',exact=True).click()
    page.get_by_role('button',name='Heute passt nicht',exact=True).click()
    expect(page.locator('.omit-round')).to_contain_text('keine Punkte')
    page.set_viewport_size({'width':360,'height':800})
    page.locator('.omit-round').scroll_into_view_if_needed()
    capture('omit-mobile.png')
    with page.expect_response(lambda r:r.url.endswith('/omit')) as response:
        page.get_by_role('button',name='Heute nicht nötig',exact=True).click()
    assert response.value.status==200
    expect(page.locator('dialog[open]')).to_have_count(0)
    after=state()
    assert (after['user']['xp'],after['user']['stars'],after['completedCount'])==before
    omitted=next(t for t in after['tasks'] if t['id']==omit_id)
    assert omitted['status']=='upcoming' and omitted['nextDueDate']>today.isoformat()
    expected[omit_id]={'status':'upcoming','nextDueDate':omitted['nextDueDate'],'omission':omitted['omission']}
    assert page.locator('.mission-reaction').count()==0

    a=create('CI Pflanzen Küche','plant','plants','kitchen',1)
    b=create('CI Wäsche Bad','laundry','laundry','bath',2)
    c=create('CI Küche glänzt','spray','kitchen','kitchen',3)
    post('/rounds',{'taskIds':[a,b,c],'minutes':10})
    assert [e['taskId'] for e in state()['round']['entries']]==[a,c,b]
    page.goto(origin+'/')
    page.get_by_role('navigation',name='Hauptnavigation').get_by_role('button',name='Basis',exact=True).click()
    page.get_by_role('button',name='Runde fortsetzen',exact=True).click()
    page.locator('.round-overview summary').click()
    expect(page.locator('.round-overview li')).to_have_text(['CI Pflanzen KücheNoch offen','CI Küche glänztNoch offen','CI Wäsche BadNoch offen'])
    capture('room-order-mobile.png')
    round_state=state()['round']
    response=context.request.patch(origin+'/api/rounds/'+round_state['id'],data={'version':round_state['version'],'action':'finish'},headers={'Origin':origin})
    assert response.status==200

    def finish(title, reaction=None, screenshot=None):
        page.get_by_role('button',name=title+' · Details',exact=True).click()
        with page.expect_response(lambda r:r.url.endswith('/complete')) as completed:
            page.get_by_role('button',name='Mission erledigt',exact=True).click()
        assert completed.value.status==200 and not completed.value.json().get('pending')
        if reaction:
            detail=page.locator(f'[data-reaction="{reaction}"]')
            expect(detail).to_be_visible(timeout=5000)
            assert detail.get_attribute('aria-hidden')=='true'
            if screenshot:
                # Capture an actual visible frame after the intentional fade-in.
                page.wait_for_timeout(180)
                capture(screenshot)
            expect(page.locator('.mission-reaction')).to_have_count(0,timeout=4000)
        else:
            expect(page.locator('dialog[open]')).to_have_count(0)
            expect(page.locator('.mission-reaction')).to_have_count(0)

    motion(True)
    reload_missions()
    finish('CI Pflanzen Küche','watering','reaction-watering.png')
    # Leaving a special success screen must not replay its already-finished reaction.
    page.get_by_role('navigation',name='Hauptnavigation').get_by_role('button',name='Missionen',exact=True).click()
    expect(page.locator('.mission-reaction')).to_have_count(0)
    finish('CI Wäsche Bad','sock','reaction-sock.png')
    page.get_by_role('navigation',name='Hauptnavigation').get_by_role('button',name='Missionen',exact=True).click()
    finish('CI Küche glänzt','shine')
    create('CI Bewegung aus','plant','plants')
    motion(False)
    reload_missions()
    finish('CI Bewegung aus')
    create('CI Reduzierte Bewegung','laundry','laundry')
    motion(True)
    page.emulate_media(reduced_motion='reduce')
    reload_missions()
    finish('CI Reduzierte Bewegung')
    page.emulate_media(reduced_motion='no-preference')
    expect(page.get_by_role('navigation',name='Hauptnavigation').get_by_role('button')).to_have_count(4)
    assert state()['completedCount']==before[2]+5
    backup=context.request.get(origin+'/api/backups').json()
    saved=next(t for t in backup['payload']['crew']['tasks'] if t['id']==omit_id)
    assert saved['omission']==omitted['omission']
    assert next(t for t in backup['payload']['crew']['tasks'] if t['id']==seasonal_id)['schedule']['activeMonths']==[4,5,6,7,8,9]
    return expected
