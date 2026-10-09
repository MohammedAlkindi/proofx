// Exercise the generated page against the published data, without a web server.
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { JSDOM } = require('jsdom');

const root = path.resolve(__dirname, '../src');
const html = fs.readFile(path.join(root, 'research.html'), 'utf8');

async function waitFor(predicate) {
  for (let i = 0; i < 100; i++) {
    if (predicate()) return;
    await new Promise(resolve => setTimeout(resolve, 10));
  }
  assert.fail('Page did not reach the expected state');
}

async function load(fail = false) {
  let csv;
  const dom = new JSDOM(await html, {
    url: 'https://www.proofx.org/research.html',
    runScripts: 'dangerously',
    beforeParse(window) {
      window.fetch = async url => {
        if (fail) return { ok: false, status: 503 };
        assert.match(url, /^\/experiments\/gb-001\/[a-z0-9.-]+$/);
        const data = await fs.readFile(path.join(root, url), 'utf8');
        return { ok: true, json: async () => JSON.parse(data), text: async () => data };
      };
      window.Blob = Blob;
      window.URL.createObjectURL = blob => { csv = blob; return 'blob:test'; };
      window.URL.revokeObjectURL = () => {};
      window.HTMLAnchorElement.prototype.click = function () {};
      window.HTMLElement.prototype.scrollIntoView = function () {};
    },
  });
  return { dom, csv: () => csv };
}

(async () => {
  const { dom, csv } = await load();
  const doc = dom.window.document;
  await waitFor(() => doc.querySelectorAll('#experiment-rows tr').length === 9);
  assert.equal(doc.querySelector('#experiment-table').hidden, false);
  assert.equal(doc.querySelectorAll('h1').length, 1);
  const seed = doc.querySelector('#experiment-seed');
  seed.value = '1';
  seed.dispatchEvent(new dom.window.Event('change'));
  assert.equal(doc.querySelectorAll('#experiment-rows tr').length, 3);
  assert.deepEqual([...doc.querySelectorAll('#experiment-rows tr')].map(tr => tr.cells[2].textContent), ['12', '4', '26']);
  doc.querySelector('#experiment-rows button').click();
  await waitFor(() => doc.querySelectorAll('#candidate-rows tr').length === 64);
  assert.equal(doc.querySelector('#candidate-inspector').hidden, false);
  doc.querySelector('#experiment-csv').click();
  const lines = (await csv().text()).split('\n');
  assert.equal(lines.length, 4);
  assert.match(lines[1], /^directed,1,12,/);
  dom.window.close();

  const failed = await load(true);
  await waitFor(() => failed.dom.window.document.querySelector('#experiment-status').textContent.includes('could not be loaded'));
  assert.equal(failed.dom.window.document.querySelector('#experiment-table').hidden, true);
  assert.equal(failed.dom.window.document.querySelectorAll('#experiment-rows tr').length, 0);
  failed.dom.window.close();
  console.log('Research page: data loading, seed filtering, inspection, CSV and error state passed');
})().catch(error => { console.error(error); process.exitCode = 1; });
