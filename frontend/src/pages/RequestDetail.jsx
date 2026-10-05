import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api, openFile, money, dateAr, STATUS, SEV, ROLE } from '../api.js'
import { useAuth } from '../App.jsx'

const REC = { approve: ['توصية: الموافقة', 'bg-emerald-100 text-emerald-900'], reject: ['توصية: الرفض', 'bg-red-100 text-red-900'], review: ['توصية: مراجعة بشرية', 'bg-amber-100 text-amber-900'] }

function QuoteForm({ rid, onDone }) {
  const [vendors, setVendors] = useState([])
  const [f, setF] = useState({ vendor_id: '', amount: '', delivery_days: '', notes: '' })
  const [file, setFile] = useState(null)
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const [newV, setNewV] = useState('')
  useEffect(() => { api('/vendors').then(setVendors) }, [])
  const addVendor = async () => {
    try { const v = await api('/vendors', { method: 'POST', body: { name: newV } }); setVendors([...vendors, v]); setF({ ...f, vendor_id: v.id }); setNewV('') } catch (e) { setErr(e.message) }
  }
  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setErr('')
    const fd = new FormData()
    Object.entries(f).forEach(([k, v]) => fd.append(k, v || (k === 'delivery_days' ? 0 : '')))
    if (file) fd.append('file', file)
    try { await api(`/requests/${rid}/quotes`, { method: 'POST', form: fd }); setF({ vendor_id: '', amount: '', delivery_days: '', notes: '' }); setFile(null); e.target.reset(); onDone() }
    catch (ex) { setErr(ex.message) } finally { setBusy(false) }
  }
  return (
    <form onSubmit={submit} className="border border-line rounded-lg p-4 space-y-3 bg-brand-50/50">
      <h3 className="font-bold">إضافة عرض سعر</h3>
      <div className="grid md:grid-cols-4 gap-3">
        <div className="md:col-span-2">
          <label className="lbl" htmlFor="v">المورد</label>
          <select id="v" className="input" required value={f.vendor_id} onChange={(e) => setF({ ...f, vendor_id: e.target.value })}>
            <option value="">اختر المورد…</option>
            {vendors.map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}
          </select>
        </div>
        <div><label className="lbl" htmlFor="a">إجمالي العرض (ر.ع)</label><input id="a" className="input" type="number" min="0.001" step="0.001" required value={f.amount} onChange={(e) => setF({ ...f, amount: e.target.value })} /></div>
        <div><label className="lbl" htmlFor="d">مدة التوريد (يوم)</label><input id="d" className="input" type="number" min="0" value={f.delivery_days} onChange={(e) => setF({ ...f, delivery_days: e.target.value })} /></div>
      </div>
      <div className="flex gap-2 items-end flex-wrap">
        <div className="flex-1 min-w-[200px]"><label className="lbl" htmlFor="nv">مورد غير مسجّل؟ أضفه</label><input id="nv" className="input" value={newV} onChange={(e) => setNewV(e.target.value)} placeholder="اسم المورد" /></div>
        <button type="button" className="btn btn-ghost" disabled={newV.length < 2} onClick={addVendor}>إضافة المورد</button>
      </div>
      <div className="grid md:grid-cols-2 gap-3">
        <div><label className="lbl" htmlFor="f">ملف العرض (PDF أو صورة)</label><input id="f" className="input" type="file" accept=".pdf,.png,.jpg,.jpeg,.webp" onChange={(e) => setFile(e.target.files[0])} /></div>
        <div><label className="lbl" htmlFor="no">ملاحظات</label><input id="no" className="input" value={f.notes} onChange={(e) => setF({ ...f, notes: e.target.value })} /></div>
      </div>
      {err && <p role="alert" className="text-bad font-semibold">{err}</p>}
      <button className="btn btn-primary" disabled={busy}>{busy ? 'جارٍ الرفع والفحص…' : 'إضافة العرض'}</button>
    </form>
  )
}

export default function RequestDetail() {
  const { id } = useParams()
  const user = useAuth()
  const [r, setR] = useState(null)
  const [err, setErr] = useState('')
  const [comment, setComment] = useState('')
  const [just, setJust] = useState(null)
  const [busy, setBusy] = useState(false)
  const load = useCallback(() => api(`/requests/${id}`).then((x) => { setR(x); setJust((j) => j ?? x.justification) }).catch((e) => setErr(e.message)), [id])
  useEffect(() => { load() }, [load])

  const act = async (fn) => { setBusy(true); setErr(''); try { await fn(); await load() } catch (e) { setErr(e.message) } finally { setBusy(false) } }
  if (err && !r) return <p role="alert" className="text-bad">{err}</p>
  if (!r) return <p>جارٍ التحميل…</p>

  const rec = r.ai_recommendation
  const bestQuote = rec?.best_quote_id
  const canAnalyze = ['dept_manager', 'finance_manager', 'general_manager', 'admin'].includes(user.role) && r.status === 'pending'

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap gap-3 items-center">
        <h1 className="text-2xl font-bold flex-1">{r.number} — {r.title}</h1>
        <span className={`badge ${STATUS[r.status][1]}`}>{STATUS[r.status][0]}</span>
      </div>
      <div className="grid md:grid-cols-4 gap-3 text-sm">
        <div className="card"><div className="text-muted">القسم</div><b>{r.department}</b></div>
        <div className="card"><div className="text-muted">مقدّم الطلب</div><b>{r.requester}</b></div>
        <div className="card"><div className="text-muted">المبلغ</div><b>{money(r.amount)}</b></div>
        <div className="card"><div className="text-muted">المتبقي من ميزانية القسم</div><b className={r.budget.remaining < 0 ? 'text-bad' : ''}>{money(r.budget.remaining)}</b></div>
      </div>
      {r.justification && <div className="card"><b>المبررات: </b>{r.justification}</div>}

      <section className="card">
        <h2 className="font-bold mb-2">البنود</h2>
        <table className="w-full"><thead><tr><th className="th">البند</th><th className="th">الكمية</th><th className="th">سعر الوحدة</th><th className="th">الإجمالي</th></tr></thead>
          <tbody>{r.items.map((i) => <tr key={i.id}><td className="td">{i.name}</td><td className="td">{i.quantity}</td><td className="td">{money(i.unit_price)}</td><td className="td">{money(i.quantity * i.unit_price)}</td></tr>)}</tbody></table>
      </section>

      <section className="card space-y-3">
        <h2 className="font-bold">عروض الأسعار</h2>
        {r.quotes.length === 0 && <p className="text-muted">لا توجد عروض بعد.</p>}
        <div className="grid md:grid-cols-2 gap-3">
          {r.quotes.map((q) => {
            const selected = r.selected_quote_id === q.id
            return (
              <div key={q.id} className={`border rounded-lg p-3 ${selected ? 'border-brand-700 bg-brand-50' : 'border-line'}`}>
                <div className="flex justify-between gap-2"><b>{q.vendor}</b>
                  <span>{selected && <span className="badge bg-brand-800 text-white me-1">المختار</span>}{bestQuote === q.id && <span className="badge bg-emerald-100 text-emerald-900">ترشيح الوكيل</span>}</span></div>
                <div className="text-xl font-bold my-1">{money(q.amount)}</div>
                <div className="text-sm text-muted">التوريد: {q.delivery_days ? `${q.delivery_days} يوم` : 'غير محدد'}{q.notes && ` — ${q.notes}`}</div>
                {q.analysis && ['ai', 'pdf_text'].includes(q.analysis.mode) && (
                  <div className="text-sm mt-2 p-2 rounded bg-white border border-line">
                    <b>{q.analysis.mode === 'ai' ? 'قراءة الملف بالذكاء الاصطناعي' : 'قراءة الملف (PDF نصّي)'}:</b> المجموع المقروء {money(q.analysis.total)}{' '}
                    {q.analysis.matches_entered_amount === true && <span className="text-ok">✓ يطابق المُدخل</span>}
                    {q.analysis.matches_entered_amount === false && <span className="text-bad">✗ لا يطابق المُدخل</span>}
                    {(q.analysis.red_flags || []).map((x, i) => <div key={i} className="text-warn">⚠ {x}</div>)}
                  </div>
                )}
                {q.analysis && !['ai', 'pdf_text'].includes(q.analysis.mode) && q.has_file && <p className="text-xs text-muted mt-2">{q.analysis.note}</p>}
                <div className="flex gap-2 mt-2 flex-wrap">
                  {q.has_file && <button className="btn btn-ghost" onClick={() => openFile(`/quotes/${q.id}/file`).catch((e) => setErr(e.message))}>عرض الملف: {q.file_name}</button>}
                  {r.can_edit && !selected && <button className="btn btn-primary" disabled={busy} onClick={() => act(() => api(`/requests/${id}/select-quote`, { method: 'POST', body: { quote_id: q.id, justification: just } }))}>اختيار هذا العرض</button>}
                  {r.can_edit && <button className="btn btn-ghost" disabled={busy} onClick={() => act(() => api(`/requests/${id}/quotes/${q.id}`, { method: 'DELETE' }))}>حذف</button>}
                </div>
              </div>
            )
          })}
        </div>
        {r.can_edit && <QuoteForm rid={id} onDone={load} />}
      </section>

      {r.can_edit && (
        <section className="card space-y-3">
          <label className="lbl" htmlFor="jj">مبررات اختيار العرض (مطلوبة إن لم يكن الأقل سعراً)</label>
          <textarea id="jj" className="input" rows="2" value={just ?? ''} onChange={(e) => setJust(e.target.value)} />
          <div className="flex gap-2 flex-wrap">
            <button className="btn btn-primary" disabled={busy} onClick={() => act(async () => { if (just !== r.justification && r.selected_quote_id) await api(`/requests/${id}/select-quote`, { method: 'POST', body: { quote_id: r.selected_quote_id, justification: just } }); await api(`/requests/${id}/submit`, { method: 'POST' }) })}>إرسال للموافقة</button>
            <button className="btn btn-ghost" disabled={busy} onClick={() => act(() => api(`/requests/${id}/cancel`, { method: 'POST' }))}>إلغاء الطلب</button>
          </div>
        </section>
      )}

      {rec && (
        <section className="card space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="font-bold flex-1">وكيل المشتريات {rec.mode === 'ai' ? '(ذكاء اصطناعي)' : '(قواعد)'}</h2>
            <span className={`badge ${REC[rec.recommendation][1]}`}>{REC[rec.recommendation][0]}</span>
            {canAnalyze && <button className="btn btn-ghost" disabled={busy} onClick={() => act(() => api(`/requests/${id}/reanalyze`, { method: 'POST' }))}>إعادة التحليل</button>}
          </div>
          <p>{rec.reasoning}</p>
          {(rec.risks || []).length > 0 && <ul className="list-disc ms-5 text-warn">{rec.risks.map((x, i) => <li key={i}>{x}</li>)}</ul>}
          <p className="text-xs text-muted">التوصية استشارية؛ القرار النهائي للمدير المعتمد.</p>
        </section>
      )}

      {r.flags.length > 0 && (
        <section className="card space-y-2">
          <h2 className="font-bold">تنبيهات وكيل التدقيق</h2>
          {r.flags.map((f) => (
            <div key={f.id} className={`flex gap-2 items-start ${f.resolved ? 'opacity-50' : ''}`}>
              <span className={`badge ${SEV[f.severity][1]}`}>{SEV[f.severity][0]}</span><span>{f.message}{f.resolved && ' (تمت المعالجة)'}</span>
            </div>
          ))}
        </section>
      )}

      {r.approvals.length > 0 && (
        <section className="card">
          <h2 className="font-bold mb-3">مسار الموافقات</h2>
          <ol className="space-y-3">
            {r.approvals.map((a) => (
              <li key={a.level} className="flex gap-3 items-start">
                <span className={`badge mt-1 ${a.decision === 'approved' ? 'bg-emerald-100 text-emerald-900' : a.decision === 'rejected' ? 'bg-red-100 text-red-900' : 'bg-slate-100 text-slate-700'}`}>
                  {a.decision === 'approved' ? 'وافق' : a.decision === 'rejected' ? 'رفض' : 'بانتظار'}
                </span>
                <div><b>{a.role_label}</b>{a.approver && ` — ${a.approver}`}<div className="text-sm text-muted">{a.decided_at ? dateAr(a.decided_at) : ''}{a.comment && ` — ${a.comment}`}</div></div>
              </li>
            ))}
          </ol>
        </section>
      )}

      {r.can_decide && (
        <section className="card space-y-3 border-brand-700">
          <h2 className="font-bold">قرارك بصفتك {ROLE[user.role]}</h2>
          <label className="lbl" htmlFor="c">تعليق (إلزامي عند الرفض)</label>
          <textarea id="c" className="input" rows="2" value={comment} onChange={(e) => setComment(e.target.value)} />
          <div className="flex gap-2">
            <button className="btn btn-ok" disabled={busy} onClick={() => act(() => api(`/requests/${id}/decision`, { method: 'POST', body: { decision: 'approved', comment } }))}>موافقة</button>
            <button className="btn btn-bad" disabled={busy} onClick={() => act(() => api(`/requests/${id}/decision`, { method: 'POST', body: { decision: 'rejected', comment } }))}>رفض</button>
          </div>
        </section>
      )}
      {err && <p role="alert" className="text-bad font-semibold">{err}</p>}
    </div>
  )
}
