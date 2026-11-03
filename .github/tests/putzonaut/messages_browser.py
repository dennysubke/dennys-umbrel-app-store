"""Two verified accounts exchanging messages in the installed production app."""
import re
import uuid
from playwright.sync_api import expect


def check_messages(page, context, browser, origin, evidence, mail_link_for):
    headers={'Origin':origin,'Content-Type':'application/json'}
    initial=context.request.get(origin+'/api/state').json()
    owner_id=initial['viewer']['id']
    invitation=context.request.post(origin+'/api/invitations',data={},headers=headers).json()['token']
    other=browser.new_context(viewport={'width':360,'height':800})
    assert other.request.post('https://localhost/trpc/user.login',data={'password':'synthetic-umbrel-ci-password'},headers={'Origin':'https://localhost'}).ok
    email='ci-messages@example.test'
    password='Synthetic message account passphrase 2026!'
    assert other.request.post(origin+'/api/account/sign-up/email',data={'name':'Robin','email':email,'password':password,'callbackURL':origin+'/konto/bestaetigt'},headers=headers).status==200
    verification=mail_link_for(email,'Bestätige deine E-Mail für Putzonaut')
    try:
        assert other.request.get(verification,max_redirects=0).status in [200,302]
    except Exception:
        raise AssertionError('Synthetic message account verification failed') from None
    finally:
        del verification
    assert other.request.post(origin+'/api/account/sign-in/email',data={'email':email,'password':password},headers=headers).status==200
    assert other.request.post(origin+'/api/auth/join',data={'name':'Robin','invite':invitation},headers=headers).status==201
    recipient_id=other.request.get(origin+'/api/state').json()['viewer']['id']

    def nav(p, name):
        p.get_by_role('navigation',name='Hauptnavigation').get_by_role('button',name=re.compile('^'+name)).click()

    def open_inbox(p):
        nav(p,'Crew')
        p.locator('.messages-link').click()
        expect(p.get_by_role('heading',name='Nachrichten',exact=True)).to_be_visible()

    def send(p, text):
        p.get_by_label('Deine Nachricht',exact=True).fill(text)
        with p.expect_response(lambda r:'/api/messages/' in r.url and r.request.method=='POST' and not r.url.endswith('/read')) as sent:
            p.get_by_role('button',name='Senden',exact=True).click()
        assert sent.value.status in [200,201]
        expect(p.get_by_label('Deine Nachricht',exact=True)).to_have_value('')
        expect(p.locator('.message-log').get_by_text(text,exact=True)).to_be_visible()

    page.goto(origin+'/')
    expect(page.get_by_role('navigation',name='Hauptnavigation')).to_be_visible(timeout=20000)
    open_inbox(page)
    page.get_by_role('button',name=re.compile('^Nachricht an Robin')).click()
    expect(page.get_by_role('heading',name='Robin',exact=True)).to_be_visible()
    first='Die Küche ist fertig. Kannst du später den Müll rausbringen? 🚀'
    send(page,first)
    assert other.request.get(origin+'/api/messages/unread').json()['unread']==1
    receiver=other.new_page();receiver.goto(origin+'/')
    expect(receiver.get_by_role('navigation',name='Hauptnavigation')).to_be_visible(timeout=20000)
    expect(receiver.locator('.nav-message-badge')).to_have_text('1',timeout=20000)
    open_inbox(receiver)
    receiver.get_by_role('button',name=re.compile('^Nachricht an Alex')).click()
    expect(receiver.locator('.message-log').get_by_text(first,exact=True)).to_be_visible()
    expect(receiver.locator('.nav-message-badge')).to_have_count(0,timeout=15000)
    reply='Klar, mache ich nach dem Essen. Danke dir!'
    send(receiver,reply)
    page.bring_to_front()
    expect(page.locator('.message-log').get_by_text(reply,exact=True)).to_be_visible(timeout=15000)

    # A message arriving before the sender's next poll must not be skipped by
    # advancing the poll cursor to the sender's own newer message.
    incoming='Zwischendurch angekommen'
    assert other.request.post(origin+'/api/messages/'+owner_id,data={'text':incoming,'requestKey':str(uuid.uuid4())},headers=headers).status==201
    send(page,'Alles klar!')
    expect(page.locator('.message-log').get_by_text(incoming,exact=True)).to_be_visible(timeout=15000)

    # A lost response after server commit must retain the draft and reuse its key.
    dropped={'done':False}
    pattern='**/api/messages/'+recipient_id
    def drop_response(route):
        if route.request.method=='POST' and not dropped['done']:
            response=route.fetch()
            assert response.status==201
            dropped['done']=True
            route.abort('connectionfailed')
        else:
            route.continue_()
    page.route(pattern,drop_response)
    retry_text='Nur einmal trotz unterbrochener Antwort'
    page.get_by_label('Deine Nachricht',exact=True).fill(retry_text)
    page.get_by_role('button',name='Senden',exact=True).click()
    expect(page.get_by_text(re.compile('^Nicht bestätigt:'))).to_be_visible()
    expect(page.get_by_label('Deine Nachricht',exact=True)).to_have_value(retry_text)
    page.unroute(pattern,drop_response)
    send(page,retry_text)
    conversation=context.request.get(origin+'/api/messages/'+recipient_id).json()['items']
    assert len([m for m in conversation if m['text']==retry_text])==1

    draft='Bleibt beim kurzen Offline-Wechsel erhalten'
    page.get_by_label('Deine Nachricht',exact=True).fill(draft)
    context.set_offline(True)
    expect(page.get_by_role('button',name='Senden',exact=True)).to_be_disabled()
    expect(page.get_by_label('Deine Nachricht',exact=True)).to_have_value(draft)
    context.set_offline(False)
    expect(page.get_by_role('button',name='Senden',exact=True)).to_be_enabled(timeout=15000)
    expect(page.get_by_label('Deine Nachricht',exact=True)).to_have_value(draft)
    page.get_by_label('Deine Nachricht',exact=True).fill('')

    # User text remains inert text and cannot load remote images or scripts.
    literal='<img src=x onerror=alert(1)> Grüße & gute Nacht'
    send(page,literal)
    expect(page.locator('.message-log img')).to_have_count(0)
    long_text='LangeNachrichtOhneLeerzeichen'*35
    send(page,long_text)
    for width,height,name in [(360,800,'messages-mobile.png'),(1280,900,'messages-desktop.png'),(320,640,'messages-narrow.png')]:
        page.set_viewport_size({'width':width,'height':height})
        assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1'), 'Messages overflow the viewport'
        assert page.locator('dialog[open]').evaluate('(el)=>el.scrollWidth<=el.clientWidth+1'), 'Messages overflow the dialog'
        page.get_by_label('Deine Nachricht',exact=True).scroll_into_view_if_needed()
        page.screenshot(path=str(evidence/name),full_page=False)
    page.set_viewport_size({'width':390,'height':844})
    page.get_by_role('button',name='Alle Nachrichten',exact=True).click()
    page.get_by_role('button',name='Schließen',exact=True).click()
    expect(page.locator('dialog[open]')).to_have_count(0)
    nav(page,'Missionen')
    assert page.get_by_role('navigation',name='Hauptnavigation').get_by_role('button').count()==4
    expected=[m['text'] for m in context.request.get(origin+'/api/messages/'+recipient_id).json()['items']]
    other.close()
    return {'recipientId':recipient_id,'texts':expected}


def assert_messages(context, origin, expected):
    response=context.request.get(origin+'/api/messages/'+expected['recipientId'])
    assert response.status==200
    assert [m['text'] for m in response.json()['items']]==expected['texts']
