import { useState } from "react";
import { Modal } from "../components/Modal";
import { Button } from "../components/Button";
import { t } from "../lib/i18n";
import { finishDialog, type DialogRequest } from "../lib/appDialogs";
const COLORS=["#ffffff","#000000","#64748b","#ef4444","#f97316","#eab308","#22c55e","#14b8a6","#06b6d4","#3b82f6","#6366f1","#a855f7","#ec4899","#171b22","#263549","#94a3b8"];
export function ColorPickerDialog({request}:{request:DialogRequest}) {
  const initial=/^#[0-9a-f]{6}$/i.test(request.value??"")?request.value!:"#000000";
  const [hex,setHex]=useState(initial),[color,setColor]=useState(initial);
  const valid=/^#[0-9a-f]{6}$/i.test(hex);
  const rgb=[1,3,5].map(i=>parseInt(color.slice(i,i+2),16));
  function choose(value:string){setColor(value);setHex(value);}
  function channel(index:number,value:number){const next=[...rgb];next[index]=value;choose("#"+next.map(v=>v.toString(16).padStart(2,"0")).join(""));}
  return <Modal title={t("选择颜色")} onClose={()=>finishDialog(request.id,null)} width={460} height={400} footer={<><Button onClick={()=>finishDialog(request.id,null)}>{t("取消")}</Button><Button variant="accent" disabled={!valid} onClick={()=>finishDialog(request.id,color)}>{t("确定")}</Button></>}>
    <div className="color-picker__preview" style={{background:color}} />
    <div className="color-picker__palette">{COLORS.map(c=><button type="button" key={c} aria-label={c} title={c} style={{background:c}} onClick={()=>choose(c)} />)}</div>
    <label className="color-picker__row">{t("颜色值")}<input className="field" aria-label={t("颜色值")} value={hex} onChange={e=>{setHex(e.target.value);if(/^#[0-9a-f]{6}$/i.test(e.target.value))setColor(e.target.value);}} /></label>
    {["红","绿","蓝"].map((label,i)=><label className="color-picker__row" key={label}>{t(label)}<input aria-label={t(label)} className="range" type="range" min={0} max={255} value={rgb[i]} onChange={e=>channel(i,Number(e.target.value))}/><span>{rgb[i]}</span></label>)}
    {!valid&&<p role="alert">{t("颜色格式应为 #RRGGBB")}</p>}
  </Modal>;
}
