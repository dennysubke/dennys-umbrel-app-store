// Packaged under hooks so Umbrel also copies this runtime file on updates.
// It is loaded by Node, not executed as a lifecycle hook.
import {createServer} from 'node:http';
import {readFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';

const escape = value => String(value).replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));

export function configurationProblems(env) {
  const problems = [];
  try {
    const url = new URL(env.APP_ORIGIN);
    if (url.origin !== env.APP_ORIGIN || url.protocol !== 'https:' || url.username || url.password) throw new Error();
  } catch { problems.push('APP_ORIGIN: vollständige HTTPS-Adresse ohne abschließenden Schrägstrich eintragen.'); }
  for (const key of ['MAIL_FROM', 'SMTP_HOST', 'SMTP_USER', 'SMTP_PASSWORD']) {
    if (!env[key]?.trim()) problems.push(`${key}: Wert aus deinem Mailkonto ergänzen.`);
  }
  if (env.MAIL_FROM && (!env.MAIL_FROM.includes('@') || /[\r\n]/.test(env.MAIL_FROM))) problems.push('MAIL_FROM: gültigen, bestätigten Absender eintragen.');
  if (env.SMTP_HOST && /[\s/]/.test(env.SMTP_HOST)) problems.push('SMTP_HOST: nur den Servernamen eintragen.');
  const port = Number(env.SMTP_PORT ?? 587);
  if (!Number.isInteger(port) || port < 1 || port > 65535) problems.push('SMTP_PORT: gültige Portnummer eintragen.');
  if (!env.BETTER_AUTH_SECRET || env.BETTER_AUTH_SECRET.length < 32) problems.push('Der von Umbrel bereitgestellte App-Schlüssel fehlt. Bitte die App neu starten.');
  return problems;
}

export function setupPage(problems) {
  return `<!doctype html><html lang="de"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Putzonaut einrichten</title><style>
    :root{color-scheme:light dark;font:16px/1.6 system-ui,sans-serif;background:#f6f2e9;color:#173f43}body{margin:0;padding:32px 20px}main{max-width:650px;margin:0 auto}img{width:88px;height:88px;border-radius:22px}h1{line-height:1.2;font-size:2rem}h2{font-size:1.1rem}section{padding:20px 24px;border:1px solid #cbd5cd;border-radius:20px;background:#fffdf7;margin:24px 0}li{margin:12px 0}code{overflow-wrap:anywhere;font-size:.93em}small{display:block;color:#4c6464}a{color:inherit}@media(prefers-color-scheme:dark){:root{background:#11282e;color:#f4efdc}section{background:#19363b;border-color:#355458}small{color:#b6c9c7}}
    </style><main><img src="/setup-icon.png" alt="Putzonaut"><h1>Bereit für den ersten Start?</h1><p>Putzonaut ist installiert. Ergänze noch die E-Mail-Einstellungen für Bestätigung und Passwort-Wiederherstellung.</p><section><h2>So richtest du die App ein</h2><ol><li>Öffne in Umbrel <strong>Einstellungen → App-Einstellungen → Putzonaut → Erweitert</strong>.</li><li>Trage bei den vorgeschlagenen Variablen deinen bestätigten Absender, den SMTP-Server, Port und Benutzernamen ein. Bei Brevo: <code>smtp-relay.brevo.com</code>, Port <code>587</code>.</li><li>Ergänze unter <strong>Eigene Variablen</strong> für den Dienst <code>web</code> die Variable <code>SMTP_PASSWORD</code> mit deinem SMTP-Schlüssel.</li><li>Wenn du eine eigene Domain nutzt, setze <code>APP_ORIGIN</code> auf ihre vollständige HTTPS-Adresse. Leite den Tunnel an <code>http://denny-putzonaut_web_1:3080</code>.</li><li>Wähle <strong>Übernehmen und neu starten</strong>. Danach kannst du dein erstes Putzonaut-Konto anlegen.</li></ol></section><section><h2>Noch zu prüfen</h2><ul>${problems.map(p=>`<li>${escape(p)}</li>`).join('')}</ul></section><small>Zugangsdaten werden hier nicht angezeigt. Änderungen erfolgen ausschließlich in deinen Umbrel-App-Einstellungen.</small></main></html>`;
}

function securityHeaders(res) {
  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('Referrer-Policy', 'no-referrer');
  res.setHeader('Content-Security-Policy', "default-src 'none'; img-src 'self'; style-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'");
}

export function routeRequest({origin, problems, applicationServer, appRoot}, req, res) {
  securityHeaders(res);
  const target = req.url ?? '/';
  if (!target.startsWith('/') || target.startsWith('//') || target.includes('\\')) { res.writeHead(400); res.end(); return; }
  const pathname = new URL(target, origin || 'http://localhost').pathname;
  if (!applicationServer) {
    if (!['GET', 'HEAD'].includes(req.method)) { res.writeHead(503); res.end('Einrichtung erforderlich.'); return; }
    if (pathname === '/api/health') { res.setHeader('Content-Type', 'application/json'); res.end(req.method === 'HEAD' ? undefined : '{"status":"setup"}'); return; }
    if (pathname === '/setup-icon.png') {
      void readFile(resolve(appRoot, 'dist/standalone/icons/icon-192.png')).then(bytes => {
        res.setHeader('Content-Type', 'image/png'); res.end(req.method === 'HEAD' ? undefined : bytes);
      }).catch(() => { res.writeHead(404); res.end(); });
      return;
    }
    if (pathname.startsWith('/api/')) { res.writeHead(503); res.end('Einrichtung erforderlich.'); return; }
    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    res.end(req.method === 'HEAD' ? undefined : setupPage(problems));
    return;
  }
  // Account cookies and verification emails must use one canonical HTTPS
  // origin. Launching the Umbrel tile after configuring a tunnel opens that URL.
  if (pathname !== '/api/health' && req.headers.host?.toLowerCase() !== new URL(origin).host.toLowerCase()) {
    if (!['GET', 'HEAD'].includes(req.method) || pathname.startsWith('/api/')) { res.writeHead(403); res.end(); return; }
    res.writeHead(302, {Location: new URL(target, origin).href}); res.end(); return;
  }
  applicationServer.emit('request', req, res);
}

export async function start({env = process.env, appRoot = '/app', port = Number(env.PORT ?? 3080), host = env.HOST ?? '0.0.0.0'} = {}) {
  process.umask(0o077);
  const problems = configurationProblems(env);
  let app, applicationServer, mailTimer;
  if (!problems.length) {
    const load = name => import(pathToFileURL(resolve(appRoot, 'standalone', name)).href);
    const [{createStandaloneApp}, {createHttpServer}, {smtpTransport}] = await Promise.all([load('app.ts'), load('http.ts'), load('mail.ts')]);
    app = await createStandaloneApp({directory:resolve(env.DATA_DIR ?? '/data'), origin:env.APP_ORIGIN, secret:env.BETTER_AUTH_SECRET, sendMail:smtpTransport(env)});
    applicationServer = createHttpServer(app, {origin:env.APP_ORIGIN, publicDirectory:resolve(appRoot,'dist/standalone'), trustedProxies:(env.TRUSTED_PROXY_IPS ?? '').split(',').map(v=>v.trim()).filter(Boolean)});
    mailTimer = setInterval(() => { void app.flushMail(); }, 5000); mailTimer.unref();
    void app.flushMail();
  }
  const state = {origin:problems.length ? null : env.APP_ORIGIN, problems, applicationServer, appRoot};
  const server = createServer({requestTimeout:30000,headersTimeout:15000,maxHeaderSize:16384}, (req,res) => routeRequest(state,req,res));
  await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(port,host,resolve);});
  const close = async () => {
    clearInterval(mailTimer);
    await new Promise((resolve,reject)=>server.close(error=>error?reject(error):resolve()));
    if (app) await app.close();
  };
  return {server, close, configured:!problems.length};
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  try {
    const runtime = await start();
    console.log(runtime.configured ? 'Putzonaut ist bereit.' : 'Putzonaut wartet auf die Konfiguration in den App-Einstellungen.');
    let stopping = false;
    for (const signal of ['SIGINT','SIGTERM']) process.on(signal, () => {
      if (stopping) return; stopping = true;
      void runtime.close().then(()=>process.exit(0),()=>process.exit(1));
    });
  } catch { console.error('Putzonaut konnte nicht starten. Bitte App-Einstellungen und Datenspeicher prüfen.'); process.exitCode = 1; }
}
