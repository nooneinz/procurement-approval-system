import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, money, dateAr } from '../api.js'
import { useAuth } from '../App.jsx'

const CODES = {
  DUPLICATE: 'طلب مكرر', SPLIT_PURCHASE: 'تجزئة مشتريات', NEAR_THRESHOLD: 'قريب من حد الموافقة', SINGLE_QUOTE: 'عرض سعر واحد',
  OVER_BUDGET: 'تجاوز الميزانية', QUOTE_MISMATCH: 'البنود لا تطابق العرض', NOT_LOWEST: 'عرض أعلى بلا مبرر',
  FILE_MISMATCH: 'الملف لا يطابق المبلغ', QUOTE_FILE_ISSUE: 'ملاحظة في ملف العرض',
}
const REC = { approve: ['الموافقة', 'bg-emerald-100 text-emerald-900'], reject: ['الرفض', 'bg-red-100 text-red-900'], review: ['مراجعة بشرية', 'bg-amber-100 text-amber-900'] }

function Num({ label, value, tone = '' }) {
  return <div className="rounded-lg bg-navy-50 p-3 text-center"><div className={`text-2xl font-bold ${tone}`}>{value}</div><div className="text-xs text-muted">{label}</div></div>
}

export default function Agents() {
  const user = useAuth()
  const [d, setD] = useState(null)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState('')
  const load = useCallback(() => api('/agents/overview').then(setD), [])
  useEffect(() => { load(); const t = setInterval(load, 10000); return () => clearInterval(t) }, [load])
  const canRun = ['admin', 'finance_manager', 'general_manager'].includes(user.role)
  const scan = async () => {
    setBusy(true)
    try { const r = await api('/audit/scan', { method: 'POST' }); setMsg(`اكتمل الفحص: ${r.flags_found} تنبيه على الطلبات المعلّقة.`); await load() } finally { setBusy(false) }
  }
  if (!d) return <p>جارٍ التحميل…</p>
  const noKey = !d.ai_enabled
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">وكلاء الذكاء الاصطناعي</h1>
      <div className="grid md:grid-cols-2 gap-4">
        <section className="card space-y-4" aria-labelledby="pa">
          <div className="flex items-center gap-2">
            <h2 id="pa" className="font-bold text-lg flex-1">وكيل المشتريات</h2>
            <span className={`badge ${noKey ? 'bg-amber-100 text-amber-900' : 'bg-emerald-100 text-emerald-900'}`}>{noKey ? 'يعمل بالقواعد' : `ذكاء اصطناعي — ${d.model}`}</span>
          </div>
          <p className="text-sm text-muted leading-7">يقرأ ملفات عروض الأسعار، ويقارن الإجمالي بما أُدخل وبميزانية القسم وسجل المورد، ثم يوصي المدير بالموافقة أو الرفض أو المراجعة.</p>
          <div className="grid grid-cols-3 gap-2">
            <Num label="موافقة" value={d.recs.approve} tone="text-ok" />
            <Num label="مراجعة" value={d.recs.review} tone="text-warn" />
            <Num label="رفض" value={d.recs.reject} tone="text-bad" />
          </div>
          <div className="text-sm">
            <b>الملفات المقروءة:</b> {d.files.ai} بالذكاء الاصطناعي، {d.files.pdf_text} PDF نصّي، {d.files.unread} بانتظار قراءة
            {noKey && d.files.unread > 0 && <span className="text-warn"> (الصور والملفات الممسوحة تحتاج مفتاح ANTHROPIC_API_KEY)</span>}
          </div>
          <div className="text-sm text-muted">إجمالي الطلبات المحلَّلة: {d.analyzed}</div>
        </section>

        <section className="card space-y-4" aria-labelledby="aa">
          <div className="flex items-center gap-2">
            <h2 id="aa" className="font-bold text-lg flex-1">وكيل التدقيق</h2>
            <span className="badge bg-emerald-100 text-emerald-900">فعّال</span>
          </div>
          <p className="text-sm text-muted leading-7">يفحص كل طلب فور إرساله قبل أن يصل للمدراء، ويرصد الطلبات المكررة والمجزأة والمشبوهة.</p>
          <div className="grid grid-cols-2 gap-2">
            <Num label="تنبيهات مفتوحة" value={d.open_flags} tone={d.open_flags ? 'text-bad' : ''} />
            <Num label="طلبات معلّقة" value={d.pending.length} />
          </div>
          {Object.keys(d.flags_by_code).length > 0 && (
            <ul className="text-sm space-y-1">{Object.entries(d.flags_by_code).map(([c, n]) => <li key={c} className="flex justify-between"><span>{CODES[c] || c}</span><b>{n}</b></li>)}</ul>
          )}
          {canRun && <button className="btn btn-primary" disabled={busy} onClick={scan}>{busy ? 'جارٍ الفحص…' : 'تشغيل الفحص الآن'}</button>}
          {msg && <p role="status" className="text-ok font-semibold text-sm">{msg}</p>}
        </section>
      </div>

      <section className="card !p-0 overflow-x-auto">
        <h2 className="font-bold p-4 pb-2">الطلبات المعلّقة وتوصية الوكيل</h2>
        <table className="w-full min-w-[560px]">
          <thead><tr><th className="th">الطلب</th><th className="th">المبلغ</th><th className="th">توصية وكيل المشتريات</th><th className="th">تنبيهات التدقيق</th></tr></thead>
          <tbody>
            {d.pending.length === 0 && <tr><td className="td text-muted" colSpan="4">لا توجد طلبات معلّقة — تظهر هنا فور إرسال أي طلب للموافقة.</td></tr>}
            {d.pending.map((r) => (
              <tr key={r.id}>
                <td className="td"><Link className="underline text-navy-800 font-semibold" to={`/requests/${r.id}`}>{r.number}</Link><div className="text-sm text-muted">{r.title}</div></td>
                <td className="td">{money(r.amount)}</td>
                <td className="td">{r.recommendation ? <span className={`badge ${REC[r.recommendation][1]}`}>{REC[r.recommendation][0]}</span> : '—'}</td>
                <td className="td">{r.flags_open ? <span className="badge bg-red-100 text-red-900">⚑ {r.flags_open}</span> : <span className="text-ok">لا يوجد</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {d.activity.length > 0 && (
        <section className="card">
          <h2 className="font-bold mb-3">نشاط الوكلاء (يتجدد تلقائياً)</h2>
          <ul className="space-y-3">
            {d.activity.map((a) => (
              <li key={a.id} className="flex gap-3 items-start">
                <span className={`badge mt-1 whitespace-nowrap ${a.agent === 'وكيل التدقيق' ? 'bg-navy-50 text-navy-800' : 'bg-emerald-100 text-emerald-900'}`}>{a.agent}</span>
                <div className="text-sm"><div>{a.details}</div><div className="text-xs text-muted">{dateAr(a.ts)}</div></div>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}
