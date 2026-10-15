const { fixture,chromium }=require('./layout-smoke.cjs');
const assert=require('assert'),fs=require('fs'),path=require('path');
const out=process.env.HUMIDI_QA_OUTPUT||path.resolve(__dirname,'../qa-output');fs.mkdirSync(out,{recursive:true});
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true}),results=[];
 for(const [width,height] of [[900,720],[1180,780]]){
  const context=await browser.newContext({viewport:{width,height},locale:'zh-CN'});await context.addInitScript(fixture);
  await context.addInitScript(()=>{
   const first=window.__records.get('seed');first.song.playback_settings.use_88_key_layout=false;
   const second=structuredClone(first);second.metadata.id='wide';second.metadata.name='88键测试曲目';second.song.playback_settings.use_88_key_layout=true;second.song.source.original_filename='88键.mid';second.midi_path='/library/wide.mid';window.__records.set('wide',second);
  });
  const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto('http://127.0.0.1:1420');
  const checks=[];
  assert.equal(await page.locator('.sidebar a[href*="discord"]').count(),0);checks.push('no-inherited-discord');
  await page.getByRole('button',{name:'设置',exact:true}).click();await page.getByRole('button',{name:'系统',exact:true}).click();
  const version=page.locator('.settings-tab__version');await version.filter({hasText:'2.1.2-xk.12'}).waitFor();assert((await version.locator('xpath=ancestor::*[contains(concat(" ",normalize-space(@class)," ")," card ")]').first().textContent()).includes('更新'));checks.push('version-in-update-card');
  await page.getByRole('button',{name:'歌单',exact:true}).click();await page.locator('.playlist-row').filter({hasText:'缓存测试曲目'}).click();await page.locator('.transport-bar button[title="播放"]').click();await page.waitForFunction(()=>window.__calls.filter(x=>x.cmd==='start_playback').length===1);
  await page.locator('.transport-bar button[title="暂停"]').click();await page.locator('.transport-bar button[title="播放"]').waitFor();
  await page.locator('.playlist-row').filter({hasText:'88键测试曲目'}).click();await page.locator('.transport-bar button[title="播放"]').click();await page.waitForFunction(()=>window.__calls.filter(x=>x.cmd==='start_playback').length===2);
  const calls=await page.evaluate(()=>window.__calls),start=calls.filter(x=>x.cmd==='start_playback').at(-1);assert.equal(start.args.config.use_88_key_layout,true);assert(calls.some(x=>x.cmd==='playlist_restore_cache'&&x.args.id==='wide'));checks.push('paused-selection-starts-new-song');
  assert.equal(calls.filter(x=>x.cmd==='toggle_pause').length,1);
  await page.locator('.transport-bar button[title="暂停"]').click();await page.locator('.transport-bar button[title="播放"]').click();await page.waitForFunction(()=>window.__calls.filter(x=>x.cmd==='toggle_pause').length===3);assert.equal(await page.evaluate(()=>window.__calls.filter(x=>x.cmd==='start_playback').length),2);checks.push('same-selection-resumes');
  await page.getByRole('button',{name:'可视化',exact:true}).click();await page.waitForFunction(()=>document.querySelectorAll('.piano-keyboard__key--white').length===52);assert.equal(await page.locator('.piano-keyboard__key--black').count(),36);checks.push('runtime-88-key-visualizer');
  await page.screenshot({path:path.join(out,`xk8-88键可视化-${width}.png`)});
  await page.getByRole('button',{name:'演奏',exact:true}).click();await page.getByText('全局默认设置 · 自动保存，仅用于之后新导入的曲目。').waitFor();assert.equal(await page.getByRole('button',{name:'保存修改并返回歌单',exact:true}).count(),0);assert.equal(await page.getByRole('switch',{name:'88 键布局',exact:true}).getAttribute('aria-checked'),'false');checks.push('playback-keeps-import-defaults-and-editor-separate');
  assert.equal(await page.locator('.apply-toast--visible').count(),0);checks.push('no-apply-toast-during-library-play');
  assert.equal(errors.length,0,errors.join('\n'));results.push({width,height,checks,errors});await context.close();
 }
 await browser.close();fs.writeFileSync(path.join(out,'xk8-playback-ui-verification.json'),JSON.stringify(results,null,2));console.log(JSON.stringify({layouts:results.length,checks:results.reduce((n,r)=>n+r.checks.length,0),errors:0}));
})().catch(e=>{console.error(e);process.exit(1)});
