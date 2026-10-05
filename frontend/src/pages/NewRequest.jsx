import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, money } from '../api.js'

export default function NewRequest() {
  const nav = useNavigate()
  const [title, setTitle] = useState('')
  const [justification, setJ] = useState('')
  const [items, setItems] = useState([{ name: '', quantity: 1, unit_price: 0 }])
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const set = (i, k, v) => setItems(items.map((x, j) => (j === i ? { ...x, [k]: v } : x)))
  const total = items.reduce((s, x) => s + Number(x.quantity) * Number(x.unit_price), 0)

  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setErr('')
    try {
      const r = await api('/requests', { method: 'POST', body: { title, justification, items: items.map((x) => ({ ...x, quantity: Number(x.quantity), unit_price: Number(x.unit_price) })) } })
      nav(`/requests/${r.id}`)
    } catch (ex) { setErr(ex.message) } finally { setBusy(false) }
  }

  return (
    <form onSubmit={submit} className="space-y-5 max-w-3xl">
      <h1 className="text-2xl font-bold">طلب شراء جديد</h1>
      <div className="card space-y-4">
        <div><label className="lbl" htmlFor="t">عنوان الطلب</label><input id="t" className="input" required minLength={3} value={title} onChange={(e) => setTitle(e.target.value)} /></div>
        <div><label className="lbl" htmlFor="j">مبررات الشراء</label><textarea id="j" className="input" rows="3" value={justification} onChange={(e) => setJ(e.target.value)} placeholder="لماذا نحتاج هذه المشتريات؟ ولماذا هذا المورد إن لم يكن الأقل سعراً؟" /></div>
      </div>
      <div className="card space-y-3">
        <h2 className="font-bold">البنود المطلوبة</h2>
        {items.map((x, i) => (
          <div key={i} className="grid grid-cols-12 gap-2 items-end">
            <div className="col-span-12 md:col-span-6"><label className="lbl" htmlFor={`n${i}`}>البند</label><input id={`n${i}`} className="input" required value={x.name} onChange={(e) => set(i, 'name', e.target.value)} /></div>
            <div className="col-span-5 md:col-span-2"><label className="lbl" htmlFor={`q${i}`}>الكمية</label><input id={`q${i}`} className="input" type="number" min="0.01" step="any" required value={x.quantity} onChange={(e) => set(i, 'quantity', e.target.value)} /></div>
            <div className="col-span-5 md:col-span-3"><label className="lbl" htmlFor={`p${i}`}>سعر الوحدة التقديري</label><input id={`p${i}`} className="input" type="number" min="0" step="any" required value={x.unit_price} onChange={(e) => set(i, 'unit_price', e.target.value)} /></div>
            <div className="col-span-2 md:col-span-1">{items.length > 1 && <button type="button" className="btn btn-ghost w-full" aria-label="حذف البند" onClick={() => setItems(items.filter((_, j) => j !== i))}>✕</button>}</div>
          </div>
        ))}
        <div className="flex justify-between items-center">
          <button type="button" className="btn btn-ghost" onClick={() => setItems([...items, { name: '', quantity: 1, unit_price: 0 }])}>+ إضافة بند</button>
          <b>الإجمالي التقديري: {money(total)}</b>
        </div>
      </div>
      {err && <p role="alert" className="text-bad font-semibold">{err}</p>}
      <button className="btn btn-primary" disabled={busy}>{busy ? 'جارٍ الحفظ…' : 'حفظ كمسودة والمتابعة لعروض الأسعار'}</button>
    </form>
  )
}
