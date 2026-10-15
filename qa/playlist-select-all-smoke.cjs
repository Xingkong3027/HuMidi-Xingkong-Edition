const { fixture, chromium } = require('./layout-smoke.cjs');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const out=process.env.HUMIDI_QA_OUTPUT || path.resolve(__dirname,'../qa-output');
fs.mkdirSync(out,{recursive:true});
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const result=[];
 for(const [width,height] of [[1180,780],[860,640]]){
  const context=await browser.newContext({viewport:{width,height},locale:'zh-CN'});
  await context.addInitScript(fixture);
  await context.addInitScript(()=>{
   const records=window.__records,seed=structuredClone(records.get('seed')); records.clear();
   for(let i=0;i<88;i++){const item=structuredClone(seed);item.metadata.id='song-'+i;item.metadata.name='Selection test '+i;records.set(item.metadata.id,item);}
  });
  const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:1420');
  await page.locator('.sidebar').getByRole('button',{name:'歌单',exact:true}).click();
  await page.locator('.playlist-row').first().click();
  await page.keyboard.press('Control+a');
  assert.equal(await page.locator('.playlist-row.is-selected').count(),88);
  await page.getByRole('button',{name:'批量修改设置',exact:true}).click();
  await page.getByRole('dialog',{name:'批量修改 88 首歌曲'}).waitFor();
  await page.keyboard.press('Escape');
  const search=page.getByPlaceholder('搜索曲目或来源…');await search.fill('Selection test 87');
  await search.press('Control+a');
  assert.deepEqual(await search.evaluate(e=>[e.selectionStart,e.selectionEnd]),[0,17]);
  await page.locator('.playlist-row').first().click();await page.keyboard.press('Control+a');
  assert.equal(await page.locator('.playlist-footer').innerText().then(t=>t.includes('已选择 88 首')),true);
  await search.fill('');await page.locator('.playlist-row').first().click();
  await page.getByRole('button',{name:'导入歌单',exact:true}).click();await page.keyboard.press('Control+a');
  await page.getByRole('button',{name:'取消',exact:true}).click();
  assert.equal(await page.locator('.playlist-row.is-selected').count(),1);
  await page.keyboard.press('Control+a');
  assert.equal(await page.locator('.playlist-row.is-selected').count(),88);
  await page.screenshot({path:path.join(out,`xk12-CtrlA-${width}.png`)});
  await page.locator('.sidebar').getByRole('button',{name:'演奏',exact:true}).click();await page.keyboard.press('Control+a');
  assert.equal(await page.locator('.playlist-page').count(),0);
  assert.deepEqual(errors,[]);result.push({width,height,selected:88,checks:['list-shortcut','batch-88','search-text-selection','hidden-items-scope','modal-guard','page-cleanup'],errors});
  await context.close();
 }
 await browser.close();fs.writeFileSync(path.join(out,'playlist-select-all-verification.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
})().catch(e=>{console.error(e);process.exit(1)});
