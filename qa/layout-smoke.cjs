const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs=require('fs'),path=require('path'),assert=require('assert');
const out=process.env.HUMIDI_QA_OUTPUT || path.resolve(__dirname,'../qa-output'); fs.mkdirSync(out,{recursive:true});
function fixture(){
 const callbacks=new Map(), listeners=new Map(); let seq=1;
 const curves={on:[{time:0,value:.6},{time:5,value:.65}],off:[{time:0,value:.4},{time:5,value:.42}]};
 const cfg={ui_language:'zh-CN',ui_active_page:'playback',ui_editor_subtab:0,tempo:135,countdown:false,auto_check_updates:false,show_update_prompt:false,switch_to_visualizer_on_play:false};
 const song={song_version:3,source:{type:'midi',original_filename:'测试.mid'},selected_tracks:[{index:0,role:'Auto-Detect'}],playback_settings:{tempo:.8,countdown:false,humanization_mode:'individual',humanization_on:true,humanization_seed_mode:'dynamic',pedal_style:'ai',pedal_curve_on:curves.on,pedal_curve_off:curves.off}};
 const records=new Map([['seed',{metadata:{id:'seed',name:'缓存测试曲目',source_type:'midi',source_label:'测试.mid',duration:10,midi_available:true,sheet_available:false,cache_available:true,humanization_mode:'individual',random_seed_mode:'dynamic',humanization_active:false,random_effect_active:false},midi_path:'/library/seed.mid',cache_path:'/cache/seed.json',song}]]);
 let shortcuts={version:3,bindings:{play_pause:['F6',null],stop:['F7',null],next:[null,null],previous:[null,null]}},capture=null,saveLabel='Ctrl+S';
 window.__calls=[];window.__records=records;window.__config=cfg;
 window.__emit=(event,payload)=>{for(const [id,v] of listeners)if(v.event===event)callbacks.get(v.handler)?.({event,id,payload})};
 window.__TAURI_INTERNALS__={metadata:{currentWindow:{label:'main'},currentWebview:{label:'main'}},transformCallback:(fn)=>{const id=seq++;callbacks.set(id,fn);return id;},unregisterCallback:(id)=>callbacks.delete(id),invoke:async(cmd,args={})=>{
  window.__calls.push({cmd,args:structuredClone(args)});
  if(cmd==='plugin:event|listen'){const id=seq++;listeners.set(id,args);return id;}
  if(cmd==='plugin:event|unlisten'){listeners.delete(args.eventId);return;}
  if(cmd==='load_app_config')return structuredClone(cfg);
  if(cmd==='save_app_config'){Object.assign(cfg,args.patch);return;}
  if(cmd==='playlist_list')return [...records.values()].map(x=>structuredClone(x.metadata));
  if(cmd==='playlist_get')return structuredClone(records.get(args.id));
  if(cmd==='playlist_put'){
   const id=args.id||'imported'; const old=records.get(id);
   const record={metadata:{...(old?.metadata||{}),id,name:args.name,source_type:'midi',source_label:args.song.source.original_filename,duration:args.duration,midi_available:true,sheet_available:false,cache_available:false,humanization_mode:'individual',random_seed_mode:'dynamic',humanization_active:false},song:structuredClone(args.song),midi_path:args.midiPath||old?.midi_path||'/imported.mid',cache_path:''};records.set(id,record);return record.metadata;
  }
  if(cmd==='playlist_prepare_cache'){await new Promise(r=>setTimeout(r,80));records.get(args.id).metadata.cache_available=true;return;}
  if(cmd==='playlist_restore_cache')return {timeline:{final_notes:[],played_notes:[],total_dur:10,tempo_events:[],time_signatures:[],measure_boundaries:[]},pedal_intervals:[[.2,2]],confidence:Array.from({length:501},(_,i)=>.5+.3*Math.sin(i/10)),confidence_fps:50,curve_on:curves.on,curve_off:curves.off};
  if(cmd==='parse_midi_structure_with_options'||cmd==='parse_midi_structure')return {initial_bpm:120,tracks:[{index:0,name:'Piano',instrument_name:'Acoustic Grand Piano',note_count:20,is_drum:false}]};
  if(cmd==='toggle_pause')return;
  if(cmd==='start_playback'){window.__emit('playback_started',null);return;}
  if(cmd==='stop_playback'||cmd==='clear_loaded_song'){window.__emit('playback_finished',null);return;}
  if(cmd==='plugin:dialog|open')return args.options?.directory?'/new':args.options?.multiple?['/new/新曲.mid']:'/new/新曲.mid';
  if(cmd==='plugin:dialog|save')return '/new/'+(args.options?.defaultPath||'backup.json');
  if(cmd==='get_shortcuts')return structuredClone(shortcuts);
  if(cmd==='get_hotkeys')return ['F6',saveLabel];
  if(cmd==='start_shortcut_binding'){capture={action:args.action,slot:args.slot};return;}
  if(cmd==='start_save_binding'){capture={action:'save'};return;}
  if(cmd==='cancel_shortcut_binding'){capture=null;return;}
  if(cmd==='set_shortcuts'){shortcuts=structuredClone(args.shortcuts);return structuredClone(shortcuts);}
  if(cmd==='finish_shortcut_binding'){
   if(capture?.action==='save')saveLabel=args.combo;
   else if(capture){for(const slots of Object.values(shortcuts.bindings))for(let i=0;i<2;i++)if(slots[i]===args.combo)slots[i]=null;shortcuts.bindings[capture.action][capture.slot]=args.combo;}
   capture=null;return {shortcuts:structuredClone(shortcuts),save_label:saveLabel};
  }
  if(cmd==='get_custom_themes')return [];
  if(cmd==='get_active_theme_name')return 'Midnight';
  if(cmd==='plugin:app|version')return '2.1.2-xk.12';
  if(cmd==='get_save_dir')return '/saves';
  if(cmd.includes('inner_size')||cmd.includes('outer_size'))return {width:860,height:640};
  if(cmd==='plugin:window|scale_factor')return 1;
  if(cmd==='list_saves')return [];
  if(cmd==='check_for_updates_now')return null;
  return null;
 }};
 window.__TAURI_EVENT_PLUGIN_INTERNALS__={unregisterListener:()=>{}};
}
async function checkBottom(page,target,description){
 const viewport=page.locator('.playback-tab .tab-page__page');
 await viewport.evaluate(e=>e.scrollTop=e.scrollHeight);
 await page.waitForTimeout(80);
 const box=await target.boundingBox(),bounds=await viewport.boundingBox();assert(box&&bounds,description+' missing');
 assert(box.y>=bounds.y-1 && box.y+box.height<=bounds.y+bounds.height+1,description+' clipped: '+JSON.stringify({box,bounds}));
 const point=await target.evaluate(e=>{const r=e.getBoundingClientRect();const top=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);return e===top||e.contains(top)});assert(point,description+' covered');
 return {description,box,bounds};
}
module.exports={fixture,checkBottom,chromium};
if(require.main===module)(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});const result=[];
 for(const [width,height,font] of [[860,640,12],[860,640,16],[1180,780,12]]){
  console.log(`checking ${width}x${height} ${font}px`); const context=await browser.newContext({viewport:{width,height},locale:'zh-CN'});await context.addInitScript(fixture);const page=await context.newPage();
  const errors=[];page.on('pageerror',e=>errors.push(String(e)));await page.goto('http://127.0.0.1:1420/');await page.getByText('全局默认设置 · 自动保存，仅用于之后新导入的曲目。').waitFor();
  await page.evaluate(f=>document.documentElement.style.setProperty('--font-size',f+'px'),font);
  await page.getByRole('button',{name:'模拟人演奏',exact:true}).click();
  const row=page.locator('.hum-row').filter({has:page.getByRole('switch',{name:'失误概率',exact:true})});
  await page.getByRole('switch',{name:'失误概率',exact:true}).click();
  const tabs=page.locator('.tab-page__tabs').first();assert(await tabs.evaluate(e=>getComputedStyle(e).overflowX==='visible'&&getComputedStyle(e).overflowY==='visible'),'tab bar uses a scroll container');
  const input=row.locator('input[type=number]');await input.fill('2.3');await input.dispatchEvent('change');
  const checks=[];checks.push(await checkBottom(page,input,'mistake input'));checks.push(await checkBottom(page,row.locator('input[type=range]'),'mistake slider'));
  assert(await page.locator('.apply-toast--visible').count()===0,'defaults showed song apply footer');
  await page.screenshot({path:path.join(out,`xk3-滚动-${width}x${height}-${font}px.png`)});
  await page.getByRole('button',{name:'歌单',exact:true}).click();await page.locator('.playlist-row').filter({hasText:'缓存测试曲目'}).click();await page.getByRole('button',{name:'修改歌曲',exact:true}).click();
  await page.getByRole('button',{name:'演奏设置',exact:true}).click();await page.getByText('编辑阈值曲线',{exact:false}).count();
  const card=page.locator('.pedal-ai-card');await card.locator('button[title="编辑阈值曲线"]').waitFor();checks.push(await checkBottom(page,card.locator('.pedal-ai-card__legend'),'pedal threshold legend'));
  // Editing a parameter introduces a footer; the bottom control must remain reachable.
  await page.locator('.performance-card input[type=number]').fill('2');
  await page.locator('.apply-toast--visible').waitFor();checks.push(await checkBottom(page,card.locator('.pedal-ai-card__legend'),'pedal threshold legend with footer'));
  await page.screenshot({path:path.join(out,`xk3-踏板-${width}x${height}-${font}px.png`)});
  await page.getByRole('button',{name:'应用修改',exact:true}).click();await page.getByRole('heading',{name:'我的歌单'}).waitFor();
  assert(await page.evaluate(()=>window.__calls.filter(x=>x.cmd==='compile_pedal').length)===0,'saving unexpectedly generated pedal on foreground');
  if(width===860&&font===12){
   await page.locator('.playlist-row').filter({hasText:'缓存测试曲目'}).click();await page.getByRole('button',{name:'播放选中曲目',exact:true}).click();
   await page.waitForTimeout(120);await page.locator('.sidebar').getByRole('button',{name:'演奏',exact:true}).click();
   await page.getByText('全局默认设置 · 自动保存，仅用于之后新导入的曲目。').waitFor();
   await page.locator('.sidebar').getByRole('button',{name:'可视化',exact:true}).click();
   assert(await page.locator('.piano-keyboard__key').first().evaluate(e=>getComputedStyle(e).borderRadius==='0px'),'piano key is rounded');
   await page.screenshot({path:path.join(out,'xk4-直角钢琴.png')});
   await page.locator('.sidebar').getByRole('button',{name:'演奏',exact:true}).click();
   assert(await page.getByRole('button',{name:'保存修改并返回歌单',exact:true}).count()===0,'play entered song editor');
   const tempo=await page.evaluate(()=>window.__config.xk_default_settings?.tempo??window.__config.tempo);assert.equal(tempo,135,'song playback overwrote defaults');
   await page.getByRole('button',{name:'模拟人演奏',exact:true}).click();
   await page.getByRole('switch',{name:'失误概率',exact:true}).click();
   await page.getByRole('button',{name:'演奏设置',exact:true}).click();
   await page.getByRole('button',{name:'导入 MIDI',exact:true}).click();await page.getByRole('button',{name:'确定',exact:true}).click();
   await page.getByText('正在设置导入草稿，加入歌单后保存。').waitFor();
   assert(await page.getByRole('button',{name:'放弃导入',exact:true}).count()===1);assert(await page.locator('.apply-toast--visible').count()===0);
   await page.locator('.performance-card input[type=number]').fill('4');assert(await page.locator('.apply-toast--visible').count()===0);
   await page.getByRole('button',{name:'加入歌单',exact:true}).click();await page.getByRole('heading',{name:'我的歌单'}).waitFor();
   await page.waitForTimeout(120);
   const calls=await page.evaluate(()=>window.__calls);const imported=calls.find(x=>x.cmd==='playlist_put'&&!x.args.id);assert(imported);assert.equal(imported.args.song.playback_settings.tempo,1.35);
   assert(calls.some(x=>x.cmd==='playlist_prepare_cache'&&x.args.id==='imported'));
  }
  assert.equal(errors.length,0,errors.join('\n'));result.push({width,height,font,checks,errors});await context.close();
 }
 await browser.close();fs.writeFileSync(path.join(out,'xk3-ui-verification.json'),JSON.stringify(result,null,2));console.log(JSON.stringify({layouts:result.length,checks:result.reduce((a,r)=>a+r.checks.length,0),flows:'defaults/edit/save/play/import/cache passed'}));
})().catch(e=>{console.error(e);process.exit(1)});
