// The same Git HTTP helper used by Umbrel's integration tests, restricted to
// a single fixture repository and loopback. Never serves application source.
const http = require('node:http');
const path = require('node:path');
const fs = require('node:fs');

const root = path.resolve(process.argv[2]);
const { Git } = require(path.join(root, 'node_modules/node-git-server'));
const repositories = new Git(path.join(root, 'repositories'), { autoCreate: false });
const server = http.createServer((request, response) => {
  const allowed = new Set([
    '/umbrel-apps.git/info/refs?service=git-upload-pack',
    '/umbrel-apps.git/git-upload-pack',
  ]);
  if (!allowed.has(request.url)) {
    response.writeHead(403);
    response.end('Read-only CI repository');
    return;
  }
  repositories.handle(request, response);
});
server.listen(0, '127.0.0.1', () => {
  const url = `http://127.0.0.1:${server.address().port}/umbrel-apps.git`;
  fs.writeFileSync(path.join(root, 'url'), url + '\n');
  console.log('CI community repository ready on loopback.');
});
