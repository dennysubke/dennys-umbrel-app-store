import test from 'node:test';
import assert from 'node:assert/strict';
import {createServer, request} from 'node:http';
import {EventEmitter} from 'node:events';
import {configurationProblems, routeRequest, setupPage, start} from '../../../denny-putzonaut/hooks/entrypoint.mjs';

const complete = {APP_ORIGIN:'https://app.example.test', BETTER_AUTH_SECRET:'synthetic-umbrel-seed-'.repeat(4), MAIL_FROM:'Putzonaut <sender@example.test>', SMTP_HOST:'smtp.example.test', SMTP_PORT:'587', SMTP_USER:'synthetic-user', SMTP_PASSWORD:'synthetic-password'};
const fetchRaw = (port,path,headers={},method='GET') => new Promise((resolve,reject) => {
  const req=request({hostname:'127.0.0.1',port,path,method,headers},res=>{let body='';res.on('data',c=>body+=c);res.on('end',()=>resolve({status:res.statusCode,headers:res.headers,body}));});req.on('error',reject);req.end();
});

test('configuration rejects insecure and ambiguous origins and incomplete SMTP credentials',()=>{
  assert.deepEqual(configurationProblems(complete),[]);
  for(const APP_ORIGIN of ['http://example.test','https://user:password@example.test','https://example.test/','https://example.test/path','javascript:alert(1)','']) {
    assert.ok(configurationProblems({...complete,APP_ORIGIN}).some(p=>p.startsWith('APP_ORIGIN:')));
  }
  for(const key of ['MAIL_FROM','SMTP_HOST','SMTP_USER','SMTP_PASSWORD']) assert.ok(configurationProblems({...complete,[key]:''}).some(p=>p.startsWith(key+':')));
  for(const SMTP_PORT of ['0','65536','oops']) assert.ok(configurationProblems({...complete,SMTP_PORT}).some(p=>p.startsWith('SMTP_PORT:')));
});

test('setup is available without starting accounts and never echoes configured credentials',async t=>{
  const env={...complete,SMTP_HOST:''};
  const runtime=await start({env,host:'127.0.0.1',port:0,websitePort:0,websiteFactory:async options=>{
    assert.equal(options.appOrigin,complete.APP_ORIGIN);
    return createServer((_req,res)=>res.end('public website'));
  }}); t.after(()=>runtime.close());
  const port=runtime.server.address().port;
  const page=await fetchRaw(port,'/'); assert.equal(page.status,200); assert.match(page.body,/App-Einstellungen/);
  for(const value of [complete.BETTER_AUTH_SECRET,complete.SMTP_PASSWORD,complete.SMTP_USER]) assert.ok(!page.body.includes(value));
  assert.match(page.headers['content-security-policy'],/form-action 'none'/);
  assert.equal((await fetchRaw(port,'/api/account/sign-up/email',{},'POST')).status,503);
  assert.equal((await fetchRaw(port,'/api/state')).status,503);
  assert.deepEqual(JSON.parse((await fetchRaw(port,'/api/health')).body),{status:'setup'});
  assert.equal((await fetchRaw(port,'/',{},'HEAD')).body,'');
  assert.equal((await fetchRaw(runtime.website.address().port,'/')).body,'public website');
});

test('invalid website settings preserve the setup screen and return an unavailable public surface',async t=>{
  const runtime=await start({env:{...complete,SMTP_HOST:'',WEBSITE_ORIGIN:'broken'},host:'127.0.0.1',port:0,websitePort:0,websiteFactory:async()=>{throw new Error('bad origin');}});
  t.after(()=>runtime.close());
  assert.equal(runtime.configured,false);
  assert.equal((await fetchRaw(runtime.website.address().port,'/')).status,503);
  assert.match((await fetchRaw(runtime.server.address().port,'/')).body,/Website-Konfiguration/);
});

test('canonical routing preserves the original socket, rejects unsafe targets, and does not trust forwarded hosts',async t=>{
  const applicationServer=new EventEmitter();let forwarded=0;
  applicationServer.on('request',(req,res)=>{forwarded++;assert.equal(req.socket.remoteAddress,'127.0.0.1');res.end('application');});
  const state={origin:complete.APP_ORIGIN,problems:[],applicationServer,appRoot:'/app'};
  const server=createServer((req,res)=>routeRequest(state,req,res));
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));t.after(()=>new Promise(resolve=>server.close(resolve)));
  const port=server.address().port;
  const canonical=await fetchRaw(port,'/konto/anmelden',{Host:'app.example.test'});assert.equal(canonical.body,'application');
  const local=await fetchRaw(port,'/konto/anmelden?next=%2F',{Host:'umbrel.local:8876','X-Forwarded-Host':'attacker.test'});
  assert.equal(local.status,302);assert.equal(local.headers.location,'https://app.example.test/konto/anmelden?next=%2F');
  assert.equal((await fetchRaw(port,'/api/state',{Host:'attacker.test'})).status,403);
  assert.equal((await fetchRaw(port,'/api/account/sign-up/email',{Host:'attacker.test'},'POST')).status,403);
  for(const path of ['//attacker.test/path','/\\attacker.test/path'])assert.equal((await fetchRaw(port,path,{Host:'app.example.test'})).status,400);
  assert.equal((await fetchRaw(port,'/api/health',{Host:'localhost'})).body,'application');
  assert.equal(forwarded,2);
});

test('setup messages are escaped before rendering',()=>{
  assert.ok(setupPage(['<script>bad</script>']).includes('&lt;script&gt;bad&lt;/script&gt;'));
  assert.ok(!setupPage(['<script>bad</script>']).includes('<script>bad</script>'));
});
