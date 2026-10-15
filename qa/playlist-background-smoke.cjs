const { fixture, chromium } = require('./layout-smoke.cjs');
const assert = require('assert'), fs = require('fs'), path = require('path');
const out = process.env.HUMIDI_QA_OUTPUT || path.resolve(__dirname, '../qa-output');
fs.mkdirSync(out, { recursive: true });
(async () => {
  const browser = await chromium.launch({ channel:'msedge',headless:true });
  const results=[];
  for (const [width,height] of [[1180,780],[860,640]]) {
    const context=await browser.newContext({viewport:{width,height},locale:'zh-CN'});
    await context.addInitScript(fixture);
    await context.addInitScript(() => {
      const records=window.__records, seed=structuredClone(records.get('seed'));
      records.clear(); window.__pendingCaches=[];
      for(let i=0;i<40;i++) {
        const record=structuredClone(seed), id='song-'+i;
        record.metadata.id=id;
        record.metadata.name=i===1?'后台测试超长歌曲名称'.repeat(30):'旧歌单测试 '+i;
        record.song.playback_settings={tempo:1,tempo_unit:'ratio',pedal_style:'hybrid',humanization_mode:'disabled',humanization_seed:null,pedal_curve_on:null,pedal_curve_off:null};
        record.midi_path='/library/'+id+'.mid'; records.set(id,record);
      }
      window.__markForBackground=()=>{for(let i=0;i<3;i++)records.get('song-'+i).metadata.cache_available=false;};
      const old=window.__TAURI_INTERNALS__.invoke;
      const timeline={final_notes:[[0,60,0.5,90,'Auto-Detect']],played_notes:[],total_dur:1,tempo_events:[],time_signatures:[],measure_boundaries:[]};
      window.__TAURI_INTERNALS__.invoke=async(cmd,args={})=>{
        if(cmd==='playlist_prepare_cache') {
          window.__calls.push({cmd,args:structuredClone(args)});
          return new Promise((resolve,reject)=>window.__pendingCaches.push({id:args.id,finish:(failed=false)=>{
            records.get(args.id).metadata.cache_available=true;
            // Simulate an xk.10 entry that already has null curves on disk.
            if(failed)reject(new Error('test cache failure'));else resolve();
          }}));
        }
        if(cmd==='playlist_restore_cache') {
          window.__calls.push({cmd,args:structuredClone(args)});
          throw new Error('test cache fallback');
        }
        if(cmd==='compile_notes'||cmd==='compile_pedal') {
          window.__calls.push({cmd,args:structuredClone(args)});
          const sent=JSON.parse(JSON.stringify(args.config));
          if(!Array.isArray(sent.pedal_curve_on)||!Array.isArray(sent.pedal_curve_off))throw new Error('null sequence sent to backend');
          return cmd==='compile_notes'?structuredClone(timeline):{pedal_intervals:[],curve_on:[],curve_off:[],confidence:[],confidence_fps:50};
        }
        if(cmd==='playlist_cache_current') {window.__calls.push({cmd,args:structuredClone(args)});records.get(args.id).metadata.cache_available=true;return;}
        return old(cmd,args);
      };
    });
    const page=await context.newPage(),errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    await page.goto('http://127.0.0.1:1420');
    await page.getByRole('button',{name:'歌单',exact:true}).click();
    await page.locator('.playlist-row').nth(8).click();
    const list=page.locator('.playlist-list'),status=page.locator('.playlist-background-status');
    await list.evaluate(e=>e.scrollTop=280);
    const geometry=async()=>page.evaluate(()=>{
      const list=document.querySelector('.playlist-list'), rect=list.getBoundingClientRect();
      return {y:rect.y,height:rect.height,scrollTop:list.scrollTop,selected:[...document.querySelectorAll('.playlist-row.is-selected')].map(e=>e.textContent)};
    });
    const baseline=await geometry(),samples=[{phase:'idle',...baseline}];
    await page.evaluate(()=>window.__markForBackground());
    await page.locator('.playlist-toolbar button[title="刷新"]').click();
    for(let index=0;index<3;index++) {
      await page.waitForFunction(i=>window.__pendingCaches.some(job=>job.id==='song-'+i),index);
      await status.filter({hasText:index===1?'后台测试超长歌曲名称':'旧歌单测试 '+index}).waitFor();
      assert.equal(await page.locator('.playlist-page [role="status"]').count(),1);
      const sample={phase:'processing-'+index,...await geometry()};samples.push(sample);
      assert.deepEqual({...sample,phase:undefined},{...baseline,phase:undefined},'list geometry, scroll or selection shifted');
      assert.equal(await status.evaluate(e=>e.getBoundingClientRect().height),18);
      await page.evaluate(i=>window.__pendingCaches.find(job=>job.id==='song-'+i).finish(i===1),index);
    }
    await page.waitForFunction(()=>!document.querySelector('.playlist-background-status').textContent.trim());
    samples.push({phase:'finished',...await geometry()});
    assert.deepEqual(await geometry(),baseline);
    await page.screenshot({path:path.join(out,`background-stable-${width}.png`)});
    // Actual React playlist/engine path, fallback compilation and start command.
    await page.locator('.playlist-row').first().click();
    await page.getByRole('button',{name:'播放选中曲目',exact:true}).click();
    await page.waitForFunction(()=>window.__calls.some(x=>x.cmd==='start_playback'));
    const calls=await page.evaluate(()=>window.__calls);
    for(const cmd of ['compile_notes','compile_pedal','start_playback']) {
      const config=calls.find(x=>x.cmd===cmd).args.config;
      assert(Array.isArray(config.pedal_curve_on)&&Array.isArray(config.pedal_curve_off));
      assert.equal(config.tempo,1);assert.equal(config.performance_optimization,false);
    }
    assert.equal(await page.getByText('歌单操作未完成',{exact:true}).count(),0);
    assert.deepEqual(errors,[]);
    results.push({width,height,samples,errors,legacy_null_to_start_command:true});
    await context.close();
  }
  await browser.close();
  fs.writeFileSync(path.join(out,'playlist-background-verification.json'),JSON.stringify(results,null,2));
  console.log(JSON.stringify({layouts:results.length,queue_failure_and_long_names:true,geometry_scroll_selection_preserved:true,legacy_null_compilation_and_start:true}));
})().catch(e=>{console.error(e);process.exit(1)});
