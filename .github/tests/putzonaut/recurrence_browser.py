"""Exercise the installed recurrence editor; all tasks and accounts are synthetic."""
import calendar
from datetime import date, datetime
import re
from zoneinfo import ZoneInfo
from playwright.sync_api import expect


def assert_recurrences(context, origin, expected):
    tasks={t['id']:t for t in context.request.get(origin+'/api/state').json()['tasks']}
    for task_id, rule in expected.items():
        task=tasks[task_id]
        assert {key:task[key] for key in rule}==rule


def check_recurrences(page, context, origin, evidence):
    state=context.request.get(origin+'/api/state').json()
    before=(state['user']['xp'],state['user']['stars'])
    year=datetime.fromisoformat(state['syncedAt'].replace('Z','+00:00')).astimezone(ZoneInfo('Europe/Berlin')).year+1
    leap=year
    while not calendar.isleap(leap):
        leap+=1
    first=f'{year}-01-31'
    annual=f'{leap}-02-29'
    expected={}
    nav=page.get_by_role('navigation',name='Hauptnavigation')
    expect(nav.get_by_role('button')).to_have_count(4)
    nav.get_by_role('button',name='Missionen',exact=True).click()

    def open_new(title):
        page.get_by_role('button',name='Eigene Mission erstellen',exact=True).click()
        expect(page.get_by_role('heading',name='Neue Mission',exact=True)).to_be_visible()
        expect(page.get_by_label('Weitere Wiederholungen',exact=True)).to_have_count(0)
        page.get_by_label('Was gibt es zu tun?',exact=True).fill(title)
        page.get_by_label('Wie oft?',exact=True).select_option('more')

    def save(label='Mission hinzufügen', method='POST'):
        with page.expect_response(lambda r: '/api/tasks' in r.url and r.request.method==method) as response:
            page.get_by_role('button',name=label,exact=True).click()
        assert response.value.status==200
        expect(page.locator('dialog[open]')).to_have_count(0)
        return response.value.json()

    def capture(name):
        assert not page.evaluate('document.documentElement.scrollWidth > innerWidth+1'), 'Recurrence editor overflows the viewport'
        assert page.locator('dialog[open]').evaluate('(el) => el.scrollWidth <= el.clientWidth+1'), 'Recurrence editor scrolls horizontally'
        page.locator('.recurrence-preview').scroll_into_view_if_needed()
        page.screenshot(path=str(evidence/name),full_page=True)

    open_new('CI Monatsrhythmus')
    page.get_by_label('Erster Termin',exact=True).fill(first)
    page.get_by_label('Abstand in Monaten',exact=True).select_option('3')
    expect(page.locator('.recurrence-preview')).to_contain_text('Alle 3 Monate am 31.')
    expect(page.locator('.recurrence-preview')).to_contain_text(f'Nächster Termin: 31.01.{year}')
    page.set_viewport_size({'width':360,'height':800})
    capture('recurrence-mobile.png')
    page.set_viewport_size({'width':1280,'height':900})
    capture('recurrence-desktop.png')
    page.set_viewport_size({'width':390,'height':844})

    # Closing and resuming must retain the advanced rule and its date.
    page.get_by_role('button',name='Schließen',exact=True).click()
    page.get_by_role('button',name='Eigene Mission erstellen',exact=True).click()
    expect(page.get_by_role('heading',name='Entwurf fortsetzen?',exact=True)).to_be_visible()
    page.get_by_role('button',name='Entwurf fortsetzen',exact=True).click()
    expect(page.get_by_label('Weitere Wiederholungen',exact=True)).to_have_value('monthly-interval')
    expect(page.get_by_label('Erster Termin',exact=True)).to_have_value(first)
    expect(page.get_by_label('Abstand in Monaten',exact=True)).to_have_value('3')
    monthly_id=save()['id']

    page.get_by_role('button',name=re.compile(r'^Demnächst')).click()
    page.get_by_role('button',name='CI Monatsrhythmus · Details',exact=True).click()
    page.get_by_role('button',name='Mission bearbeiten',exact=True).click()
    expect(page.get_by_label('Weitere Wiederholungen',exact=True)).to_have_value('monthly-interval')
    expect(page.get_by_label('Erster Termin',exact=True)).to_have_value(first)
    page.get_by_label('Abstand in Monaten',exact=True).select_option('6')
    save('Änderungen speichern','PATCH')
    expected[monthly_id]={'cadence':'monthly-interval','schedule':{'startDate':first,'intervalMonths':6},'nextDueDate':first}

    open_new('CI Letzter Sonntag')
    page.get_by_label('Weitere Wiederholungen',exact=True).select_option('monthly-weekday')
    page.get_by_label('Im Monat',exact=True).select_option('-1')
    page.get_by_label('Wochentag',exact=True).select_option('7')
    page.get_by_label('Startdatum',exact=True).fill(f'{year}-01-01')
    last=31
    while date(year,1,last).weekday()!=6:
        last-=1
    expect(page.locator('.recurrence-preview')).to_contain_text('Jeden letzten Sonntag im Monat')
    expect(page.locator('.recurrence-preview')).to_contain_text(f'Nächster Termin: {last:02d}.01.{year}')
    capture('recurrence-ordinal.png')
    ordinal_id=save()['id']
    expected[ordinal_id]={'cadence':'monthly-weekday','schedule':{'startDate':f'{year}-01-01','monthWeek':-1,'monthWeekday':7},'nextDueDate':f'{year}-01-{last:02d}'}

    open_new('CI Jährlicher Termin')
    page.get_by_label('Weitere Wiederholungen',exact=True).select_option('yearly')
    page.get_by_label('Erster Termin',exact=True).fill(annual)
    expect(page.locator('.recurrence-preview')).to_contain_text('Jährlich am 29. Februar')
    expect(page.locator('.recurrence-preview')).to_contain_text(f'Nächster Termin: 29.02.{leap}')
    capture('recurrence-yearly.png')
    annual_id=save()['id']
    rule={'cadence':'yearly','schedule':{'startDate':annual},'nextDueDate':annual}
    expected[annual_id]=rule
    page.get_by_role('button',name='CI Jährlicher Termin · Details',exact=True).click()
    page.get_by_role('button',name='Mission duplizieren',exact=True).click()
    expect(page.get_by_label('Erster Termin',exact=True)).to_have_value(annual)
    expected[save()['id']]=rule

    assert_recurrences(context,origin,expected)
    after=context.request.get(origin+'/api/state').json()['user']
    assert (after['xp'],after['stars'])==before, 'Planning must not award points'
    expect(nav.get_by_role('button')).to_have_count(4)
    return expected
