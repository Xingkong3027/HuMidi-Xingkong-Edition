const {fixture,chromium}=require('./layout-smoke.cjs');
const assert=require('assert'),fs=require('fs'),path=require('path');
const out=process.env.HUMIDI_QA_OUTPUT||path.resolve(__dirname,'../qa-output');fs.mkdirSync(out,{recursive:true});
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});const context=await browser.newContext({viewport:{width:900,height:720},locale:'zh-CN'});await context.addInitScript(fixture);
 const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto('http://127.0.0.1:1420');
 await page.getByRole('button',{name:'设置',exact:true}).click();await page.getByRole('button',{name:'快捷键',exact:true}).click();
 for(const action of ['上一首','下一首'])assert.equal(await page.getByRole('button',{name:action+'快捷键 1',exact:true}).innerText(),'未设置');
 await page.getByRole('button',{name:'下一首快捷键 1',exact:true}).click();await page.keyboard.press('Control+k');
 await page.getByRole('button',{name:'下一首快捷键 1',exact:true}).filter({hasText:'Ctrl+K'}).waitFor();assert.equal(await page.locator('.shortcut-grid').count(),1,'Ctrl+K collapsed app while recording');
 await page.getByRole('button',{name:'清除下一首快捷键 1',exact:true}).click();await page.getByRole('button',{name:'下一首快捷键 1',exact:true}).filter({hasText:'未设置'}).waitFor();
 await page.getByRole('button',{name:'下一首快捷键 1',exact:true}).click();await page.evaluate(()=>document.dispatchEvent(new KeyboardEvent('keydown',{key:'MediaTrackNext',code:'MediaTrackNext',bubbles:true,cancelable:true})));
 await page.getByRole('button',{name:'下一首快捷键 1',exact:true}).filter({hasText:'MediaNext'}).waitFor();
 await page.getByRole('button',{name:'上一首快捷键 1',exact:true}).click();await page.keyboard.press('Escape');await page.getByRole('button',{name:'上一首快捷键 1',exact:true}).filter({hasText:'未设置'}).waitFor();
 assert.equal(errors.length,0,errors.join('\n'));assert.equal(await page.evaluate(()=>window.__calls.filter(x=>x.cmd==='start_playback').length),0);
 await page.screenshot({path:path.join(out,'xk6-快捷键.png')});fs.writeFileSync(path.join(out,'xk6-shortcuts-verification.json'),JSON.stringify({checks:['unbound-navigation','combination-recording','no-compact-toggle','clear','media-recording','escape-cancel','no-playback'],errors},null,2));
 await browser.close();console.log('7 shortcut UI checks passed');
})().catch(error=>{console.error(error);process.exit(1)});
