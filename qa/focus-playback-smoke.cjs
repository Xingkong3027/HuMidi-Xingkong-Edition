const {fixture,chromium}=require('./layout-smoke.cjs');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const out=process.env.HUMIDI_QA_OUTPUT||path.resolve(__dirname,'../qa-output');
fs.mkdirSync(out,{recursive:true});
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true}),results=[];
 for(const [width,height] of [[1180,780],[860,640]]){
  const context=await browser.newContext({viewport:{width,height},locale:'zh-CN'});
  await context.addInitScript(fixture);
  await context.addInitScript(()=>{const seed=structuredClone(window.__records.get('seed'));window.__records.clear();for(let i=0;i<88;i++){const d=structuredClone(seed);d.metadata.id='song-'+i;d.metadata.name='Song '+i;window.__records.set(d.metadata.id,d);}});
  const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:1420/');
  await page.locator('.sidebar').getByRole('button',{name:'歌单',exact:true}).click();
  const next=page.locator('.transport-bar__controls button').last();
  const starts=()=>page.evaluate(()=>window.__calls.filter(x=>x.cmd==='start_playback').length);
  await next.click();await page.waitForFunction(()=>window.__calls.some(x=>x.cmd==='start_playback'));
  const before=await starts();
  assert.equal(await next.evaluate(e=>e===document.activeElement),false);
  for(let i=0;i<8;i++){await page.keyboard.press('Space');await page.waitForTimeout(50);}
  assert.equal(await starts(),before,'pedal Space restarted a song after mouse activation');
  // Deliberate keyboard activation remains supported.
  await next.evaluate(e=>e.focus());await page.keyboard.press('Space');
  await page.waitForFunction(n=>window.__calls.filter(x=>x.cmd==='start_playback').length===n,before+1);
  assert.equal(await next.evaluate(e=>e===document.activeElement),true);
  await page.evaluate(()=>{window.__emit('progress_updated',3.5);window.__emit('focus_paused',null);});
  await page.locator('.transport-bar__controls button[title="播放"]').waitFor();
  const seeks=await page.evaluate(()=>window.__calls.filter(x=>x.cmd==='seek_playback').length);
  const count=await starts();await page.waitForTimeout(100);assert.equal(await starts(),count);
  await page.locator('.transport-bar__controls button[title="播放"]').click();
  assert.equal(await page.evaluate(()=>window.__calls.filter(x=>x.cmd==='seek_playback').length),seeks);
  await page.locator('.sidebar').getByRole('button',{name:'设置',exact:true}).click();
  await page.getByRole('button',{name:'显示',exact:true}).click();
  const setting=page.getByRole('switch',{name:'本窗口获得焦点时暂停演奏',exact:true});
  assert.equal(await setting.getAttribute('aria-checked'),'true');
  await setting.click();assert.equal(await page.evaluate(()=>window.__config.pause_on_app_focus),false);
  await setting.click();assert.equal(await page.evaluate(()=>window.__config.pause_on_app_focus),true);
  await page.mouse.move(width-10,height-10);
  await page.waitForFunction(()=>{
   const side=document.querySelector('.sidebar'),area=document.querySelector('.app-page-area');
   return side && area && side.getBoundingClientRect().right<=parseFloat(getComputedStyle(area).marginLeft)+2;
  });
  await page.screenshot({path:path.join(out,`xk13-focus-settings-${width}.png`)});
  await page.getByRole('combobox',{name:'语言',exact:true}).selectOption('en');
  await page.getByRole('switch',{name:'Pause playback when this window has focus',exact:true}).waitFor();
  assert.deepEqual(errors,[]);
  results.push({width,height,library:88,mouseStarts:before,extraStartsAfterEightSpaces:0,keyboardActivationPreserved:true,focusPauseDidNotAdvance:true,resumeDidNotSeek:true,policyPersisted:true,englishTranslated:true,errors});
  await context.close();
 }
 await browser.close();fs.writeFileSync(path.join(out,'focus-playback-verification.json'),JSON.stringify(results,null,2));console.log(JSON.stringify(results));
})().catch(e=>{console.error(e);process.exit(1)});
