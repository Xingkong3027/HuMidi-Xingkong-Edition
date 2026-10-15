const { fixture, chromium } = require('./layout-smoke.cjs');
const assert = require('assert'), fs = require('fs'), path = require('path');
const out = process.env.HUMIDI_QA_OUTPUT || path.resolve(__dirname, '../qa-output');
fs.mkdirSync(out, { recursive: true });
(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const results = [];
  for (const [width, height] of [[1180, 780], [860, 640]]) {
    const context = await browser.newContext({ viewport: { width, height }, locale: 'zh-CN' });
    await context.addInitScript(fixture);
    await context.addInitScript(() => {
      const old = window.__TAURI_INTERNALS__.invoke;
      window.__TAURI_INTERNALS__.invoke = async (cmd, args) => {
        const result = await old(cmd, args);
        if (cmd === 'plugin:dialog|open') return args.options?.directory ? 'C:/旧版数据' : 'C:/旧版/normal.json';
        if (cmd === 'playlist_import' || cmd === 'playlist_import_library') return { imported: 2, errors: [] };
        return result;
      };
    });
    const page = await context.newPage(), errors = [], checks = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.goto('http://127.0.0.1:1420');
    await page.getByRole('button', { name: '歌单', exact: true }).click();
    await page.getByRole('button', { name: '导入歌单', exact: true }).click();
    const modal = page.getByRole('dialog');
    await modal.getByText('读取本地歌库文件夹', { exact: true }).waitFor();
    assert((await modal.textContent()).includes('index.json'));
    const box = await modal.boundingBox();
    assert(box.x >= 0 && box.y >= 0 && box.x + box.width <= width + 1 && box.y + box.height <= height + 1);
    checks.push('file-and-local-library-choices-clear-and-visible');
    await page.screenshot({ path: path.join(out, `import-migration-${width}.png`), fullPage: false });
    await page.getByRole('button', { name: '选择新旧版歌单文件（推荐）', exact: true }).click();
    await page.waitForFunction(() => window.__calls.some(x => x.cmd === 'playlist_import'));
    const fileCalls = await page.evaluate(() => window.__calls);
    const fileOpen = fileCalls.find(x => x.cmd === 'plugin:dialog|open');
    assert.equal(fileOpen.args.options.directory, false);
    assert(fileOpen.args.options.filters[0].extensions.includes('json'));
    assert(fileOpen.args.options.filters[0].extensions.includes('zip'));
    assert.equal(fileCalls.find(x => x.cmd === 'playlist_import').args.path, 'C:/旧版/normal.json');
    checks.push('legacy-json-file-reaches-normal-import');
    await page.getByRole('button', { name: '完成', exact: true }).click();
    await page.getByRole('button', { name: '导入歌单', exact: true }).click();
    await page.getByRole('button', { name: '读取本地歌库文件夹', exact: true }).click();
    await page.waitForFunction(() => window.__calls.some(x => x.cmd === 'playlist_import_library'));
    const directoryCalls = await page.evaluate(() => window.__calls);
    assert.equal(directoryCalls.find(x => x.cmd === 'playlist_import_library').args.path, 'C:/旧版数据');
    assert.equal(directoryCalls.filter(x => x.cmd === 'plugin:dialog|open').at(-1).args.options.directory, true);
    checks.push('local-data-folder-reaches-library-migration');
    assert.deepEqual(errors, []);
    results.push({ width, height, checks, errors });
    await context.close();
  }
  await browser.close();
  fs.writeFileSync(path.join(out, 'import-migration-verification.json'), JSON.stringify(results, null, 2));
  console.log(JSON.stringify({ layouts: results.length, checks: results.reduce((n, r) => n + r.checks.length, 0) }));
})().catch(e => { console.error(e); process.exit(1); });
