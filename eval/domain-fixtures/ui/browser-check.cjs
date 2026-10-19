// Reviewed local fixture only. CDP communicates over anonymous pipes, never a
// listening debug port. No --no-sandbox; no credential-bearing user profile.
const {spawn} = require('node:child_process');
const fs = require('node:fs');
const [browser, profile, fixture] = process.argv.slice(2);
let nextId = 1;
const pending = new Map();
let buffer = Buffer.alloc(0);
const child = spawn(browser, [
  '--headless=new', '--remote-debugging-pipe', '--user-data-dir=' + profile,
  '--no-first-run', '--no-default-browser-check', '--disable-background-networking',
  '--disable-component-update', '--disable-sync', '--disable-extensions',
  '--disable-default-apps', '--disable-quic', '--metrics-recording-only',
  '--proxy-server=http://127.0.0.1:9', '--proxy-bypass-list=<-loopback>',
  '--host-resolver-rules=MAP * 0.0.0.0',
  '--disable-features=MediaRouter,OptimizationHints,AutofillServerCommunication',
  'about:blank'
], {stdio: ['ignore', 'ignore', 'ignore', 'pipe', 'pipe'], windowsHide: true});
const deadline = setTimeout(() => { child.kill(); process.exitCode = 2; }, 30000);
child.on('error', () => { clearTimeout(deadline); process.exitCode = 2; });
child.on('exit', () => {
  for (const item of pending.values()) item.reject(new Error('Browser exited'));
  pending.clear();
});
child.stdio[4].on('data', chunk => {
  buffer = Buffer.concat([buffer, chunk]);
  if (buffer.length > 2 * 1024 * 1024) { child.kill(); return; }
  let end;
  while ((end = buffer.indexOf(0)) >= 0) {
    const raw = buffer.subarray(0, end).toString();
    buffer = buffer.subarray(end + 1);
    let message;
    try { message = JSON.parse(raw); } catch { child.kill(); return; }
    const item = pending.get(message.id);
    if (item) {
      pending.delete(message.id);
      message.error ? item.reject(new Error('CDP command failed')) : item.resolve(message.result);
    }
  }
});
function command(method, params = {}, sessionId) {
  return new Promise((resolve, reject) => {
    const id = nextId++;
    pending.set(id, {resolve, reject});
    child.stdio[3].write(JSON.stringify({id, method, params, ...(sessionId ? {sessionId} : {})}) + '\0');
  });
}
(async () => {
  try {
    const {targetId} = await command('Target.createTarget', {url: 'about:blank'});
    const {sessionId} = await command('Target.attachToTarget', {targetId, flatten: true});
    const send = (method, params = {}) => command(method, params, sessionId);
    await send('Page.enable');
    await send('Network.enable');
    await send('Network.setBlockedURLs', {urls: ['http://*', 'https://*', 'ws://*', 'wss://*', 'ftp://*']});
    const {frameTree} = await send('Page.getFrameTree');
    await send('Page.setDocumentContent', {frameId: frameTree.frame.id, html: fs.readFileSync(fixture, 'utf8')});
    const evaluate = async expression => {
      const answer = await send('Runtime.evaluate', {expression, returnByValue: true});
      if (answer.exceptionDetails) throw new Error('Fixture script failed');
      return answer.result.value;
    };
    const ax = await send('Accessibility.getFullAXTree');
    const label = ax.nodes.some(n => n.role?.value === 'textbox' && n.name?.value === 'Email');
    const button = ax.nodes.some(n => n.role?.value === 'button' && n.name?.value === 'Save');
    await evaluate("document.getElementById('email').focus()");
    await send('Input.insertText', {text: 'invalid-email'});
    await send('Input.dispatchKeyEvent', {type: 'keyDown', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13, text: '\r', unmodifiedText: '\r'});
    await send('Input.dispatchKeyEvent', {type: 'keyUp', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13});
    const invalid = await evaluate("!document.getElementById('email').checkValidity() && document.getElementById('status').textContent === ''");
    await evaluate("document.getElementById('email').value = ''; document.getElementById('email').focus()");
    await send('Input.insertText', {text: 'fixture@example.invalid'});
    await send('Input.dispatchKeyEvent', {type: 'keyDown', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13, text: '\r', unmodifiedText: '\r'});
    await send('Input.dispatchKeyEvent', {type: 'keyUp', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13});
    const submitted = await evaluate("document.getElementById('status').textContent === 'fixture@example.invalid' && document.getElementById('status').getAttribute('aria-live') === 'polite'");
    process.stdout.write(JSON.stringify({label_in_accessibility_tree: label, semantic_button: button,
      invalid_email_blocks_submit: invalid, keyboard_submit_updates_live_region: submitted}) + '\n');
    await command('Browser.close');
  } catch {
    process.exitCode = 2;
    child.kill();
  } finally {
    clearTimeout(deadline);
  }
})();
