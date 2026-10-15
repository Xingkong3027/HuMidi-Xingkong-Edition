const {fixture,chromium}=require('./layout-smoke.cjs');
const assert=require('assert'),fs=require('fs'),path=require('path');
const out=process.env.HUMIDI_QA_OUTPUT||path.resolve(__dirname,'../qa-output');fs.mkdirSync(out,{recursive:true});
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true}),results=[];
 for(const [width,height,font] of [[900,720,12],[860,640,16]]){
  const context=await browser.newContext({viewport:{width,height},locale:'zh-CN'});await context.addInitScript(fixture);
  await context.addInitScript(()=>{
   const old=window.__TAURI_INTERNALS__.invoke;
   const curves={on:[{time:0,value:.6},{time:10,value:.65}],off:[{time:0,value:.4},{time:10,value:.42}]};
   window.__TAURI_INTERNALS__.invoke=async(cmd,args)=>{
    const result=await old(cmd,args);
    if(cmd==='compile_notes')return {final_notes:[{id:0,pitch:60,velocity:80,start_time:0,duration:10,hand:'right'}],played_notes:[{id:0,pitch:60,velocity:80,start_time:0,duration:10,hand:'right'}],total_dur:10,tempo_events:[[0,500000]],time_signatures:[],measure_boundaries:[]};
    if(cmd==='compile_pedal')return {pedal_intervals:[[.4,1.2],[2,3]],curve_on:curves.on,curve_off:curves.off,confidence:Array.from({length:501},(_,i)=>.5+.3*Math.sin(i/10)),confidence_fps:50};
    if(cmd==='forward_key'&&args.pressed&&args.code==='F6')window.__emit('hotkey_toggle_requested',null);
    return result;
   };
  });
  const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto('http://127.0.0.1:1420');await page.evaluate(f=>document.documentElement.style.setProperty('--font-size',f+'px'),font);
  const mode=page.getByRole('combobox',{name:'生成方式',exact:true});assert.equal(await mode.inputValue(),'auto');const checks=['new-default-auto'];
  await page.getByRole('switch',{name:'开始时释放空格（踏板）',exact:true}).click();checks.push('start-release-setting');
  await page.getByRole('button',{name:'导入 MIDI',exact:true}).click();await page.getByRole('button',{name:'确定',exact:true}).click();await page.getByText('正在设置导入草稿，加入歌单后保存。').waitFor();
  await page.getByRole('button',{name:'生成踏板事件',exact:true}).click();await page.getByRole('button',{name:'重新生成',exact:true}).waitFor();assert.equal(await mode.inputValue(),'auto');assert.equal(await page.locator('.pedal-ai-card__legend').count(),0);
  await page.getByRole('button',{name:'重新生成',exact:true}).click();await page.waitForFunction(()=>window.__calls.filter(x=>x.cmd==='compile_pedal').length===2);assert.equal(await mode.inputValue(),'auto');const auto=await page.evaluate(()=>window.__calls.filter(x=>x.cmd==='compile_pedal').map(x=>x.args.config.pedal_ai_mode));assert.deepEqual(auto,['auto','auto']);checks.push('auto-regenerate-stable');
  await mode.selectOption('custom');await page.getByRole('button',{name:'重新生成',exact:true}).click();await page.waitForFunction(()=>window.__calls.filter(x=>x.cmd==='compile_pedal').length===3);assert.equal((await page.evaluate(()=>window.__calls.filter(x=>x.cmd==='compile_pedal').at(-1))).args.config.pedal_ai_mode,'custom');assert.equal(await page.locator('.pedal-ai-card__legend').count(),1);checks.push('explicit-custom-mode');
  await page.screenshot({path:path.join(out,`xk8-自定义踏板-${width}.png`)});
  await page.getByRole('button',{name:'加入歌单',exact:true}).click();await page.getByRole('heading',{name:'我的歌单'}).waitFor();const stored=await page.evaluate(()=>window.__calls.filter(x=>x.cmd==='playlist_put'&&!x.args.id).at(-1));assert.equal(stored.args.song.playback_settings.pedal_ai_mode,'custom');assert.equal(stored.args.song.playback_settings.release_pedal_on_start,true);checks.push('per-song-mode-and-start-option-persist');
  await page.locator('.playlist-row').filter({hasText:'缓存测试曲目'}).click();await page.locator('.transport-bar button[title="播放"]').click();await page.locator('.transport-bar button[title="暂停"]').waitFor();const count=await page.evaluate(()=>window.__calls.filter(x=>x.cmd==='toggle_pause').length);await page.keyboard.press('F6');await page.waitForFunction(n=>window.__calls.filter(x=>x.cmd==='toggle_pause').length===n+1,count);await page.locator('.transport-bar button[title="播放"]').waitFor();checks.push('focused-window-playback-hotkey');
  const putBefore=await page.evaluate(()=>window.__calls.filter(x=>x.cmd==='playlist_put').length);await page.evaluate(()=>window.__emit('hotkey_save_requested',null));await page.waitForTimeout(50);assert.equal(await page.evaluate(()=>window.__calls.filter(x=>x.cmd==='playlist_put').length),putBefore);checks.push('library-playback-save-does-not-copy-song');
  assert.equal(errors.length,0,errors.join('\n'));results.push({width,height,font,checks,errors});await context.close();
 }
 await browser.close();fs.writeFileSync(path.join(out,'xk8-integration-verification.json'),JSON.stringify(results,null,2));console.log(JSON.stringify({layouts:results.length,checks:results.reduce((a,r)=>a+r.checks.length,0),errors:0}));
})().catch(e=>{console.error(e);process.exit(1)});
