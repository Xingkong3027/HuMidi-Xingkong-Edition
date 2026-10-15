const {fixture,chromium}=require('./layout-smoke.cjs');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const out=process.env.HUMIDI_QA_OUTPUT||path.resolve(__dirname,'../qa-output');fs.mkdirSync(out,{recursive:true});
async function nav(page,name){await page.locator('.sidebar').getByRole('button',{name,exact:true}).click();const v=page.viewportSize();await page.mouse.move(v.width-8,v.height-8);await page.waitForFunction(()=>!document.querySelector('.sidebar').classList.contains('sidebar--expanded'));}
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true}),results=[];
 for(const [width,height] of [[1180,780],[860,640]]){
  const context=await browser.newContext({viewport:{width,height},locale:'zh-CN'});
  await context.addInitScript(fixture);
  await context.addInitScript(()=>{
   const seed=structuredClone(window.__records.get('seed'));window.__records.clear();
   for(let i=0;i<88;i++){const d=structuredClone(seed);d.metadata.id='song-'+i;d.metadata.name='Song '+i;Object.assign(d.song.playback_settings,{release_pedal_on_start:false,auto_pause:true,debug_mode:false});window.__records.set(d.metadata.id,d);}
  });
  const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:1420/');
  await page.getByText('新曲目默认值 · 自动保存，仅用于之后新导入的曲目。').waitFor();
  assert.equal(await page.getByRole('switch',{name:'开始时释放空格（踏板）',exact:true}).count(),0);
  assert.equal(await page.getByRole('switch',{name:'调试输出',exact:true}).count(),0);
  await page.getByRole('button',{name:'全局设置',exact:true}).click();
  const names=['开始时释放空格（踏板）','播放时自动切换到 Roblox 窗口','本窗口获得焦点时暂停演奏','单曲试听结束后停留在曲尾','调试输出'];
  for(const name of names)await page.getByRole('switch',{name,exact:true}).click();
  await page.waitForFunction(()=>window.__config.xk_global_release_pedal_on_start===true&&window.__config.xk_global_auto_pause===false&&window.__config.xk_global_debug_mode===true&&window.__config.auto_focus_roblox===true&&window.__config.pause_on_app_focus===true);
  const mutations=()=>page.evaluate(()=>window.__calls.filter(x=>['playlist_put','compile_notes','compile_pedal'].includes(x.cmd)).length);
  assert.equal(await mutations(),0,'global switches compiled or saved a song');
  await page.mouse.move(width-10,height-10);
  await page.locator('.playback-tab .tab-page__page').evaluate(e=>e.scrollTop=0);
  await page.screenshot({path:path.join(out,`xk15-global-top-${width}.png`)});
  await page.locator('.playback-tab .tab-page__page').evaluate(e=>e.scrollTop=e.scrollHeight);
  const debug=page.getByRole('switch',{name:'调试输出',exact:true});
  const visible=await debug.evaluate(e=>{const r=e.getBoundingClientRect();const top=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);return e===top||e.contains(top)});
  assert(visible,'global debug switch is clipped or covered');
  await page.screenshot({path:path.join(out,`xk15-global-bottom-${width}.png`)});
  await nav(page,'歌单');
  await page.locator('.playlist-row').first().click();await page.getByRole('button',{name:'修改歌曲',exact:true}).click();
  await page.getByRole('button',{name:'全局设置',exact:true}).click();
  for(const [name,value] of names.map((n,i)=>[n,i!==3]))assert.equal(await page.getByRole('switch',{name,exact:true}).getAttribute('aria-checked'),String(value),'old song changed '+name);
  const before=await mutations();
  await page.getByRole('switch',{name:'调试输出',exact:true}).click();
  assert.equal(await mutations(),before);
  assert.equal(await page.locator('.apply-toast--visible').count(),0);
  await page.getByRole('button',{name:'独立设置',exact:true}).click();
  await page.locator('.editor-scope-note').filter({hasText:'当前曲目独立设置'}).waitFor();
  assert.equal(await page.getByRole('switch',{name:'开始时释放空格（踏板）',exact:true}).count(),0);
  await nav(page,'设置');
  await page.getByRole('button',{name:'显示',exact:true}).click();
  assert.equal(await page.getByRole('switch',{name:'本窗口获得焦点时暂停演奏',exact:true}).count(),0);
  await page.getByRole('combobox',{name:'语言',exact:true}).selectOption('en');
  await nav(page,'Playback');
  await page.getByRole('button',{name:'Global settings',exact:true}).click();
  await page.getByRole('switch',{name:'Keep position at the end of single-song previews',exact:true}).waitFor();
  await page.getByRole('switch',{name:'Automatically focus the Roblox window when playing',exact:true}).waitFor();
  assert.deepEqual(errors,[]);
  results.push({width,height,library:88,globalControls:5,legacySongCannotOverride:true,changesDoNotSaveOrCompileSong:true,scopesExplained:true,oldSettingsLocationRemoved:true,englishTranslated:true,bottomReachable:visible,errors});
  await context.close();
 }
 await browser.close();fs.writeFileSync(path.join(out,'global-playback-verification.json'),JSON.stringify(results,null,2));console.log(JSON.stringify(results));
})().catch(e=>{console.error(e);process.exit(1)});
