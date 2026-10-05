import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, dateAr, SEV } from '../api.js'

const ACTIONS = {
  'auth.login': 'تسجيل دخول', 'auth.login_failed': 'محاولة دخول فاشلة', 'request.create': 'إنشاء طلب', 'request.submit': 'إرسال للموافقة',
  'request.approved': 'موافقة', 'request.rejected': 'رفض', 'request.cancel': 'إلغاء طلب', 'quote.add': 'إضافة عرض', 'quote.select': 'اختيار عرض',
  'quote.delete': 'حذف عرض', 'user.create': 'إنشاء مستخدم', 'user.update': 'تعديل مستخدم', 'department.create': 'إنشاء قسم', 'department.update': 'تعديل قسم',
  'vendor.create': 'إضافة مورد', 'agent.reanalyze': 'إعادة تحليل الوكلاء', 'agent.audit_scan': 'فحص وكيل التدقيق', 'flag.resolve': 'معالجة تنبيه', 'system.bootstrap': 'تهيئة النظام',
}

export default function Audit() {
  const [tab, setTab] = useState('flags')
  const [flags, setFlags] = useState([])
  const [logs, setLogs] = useState([])
  const [chain, setChain] = useState(null)
  const [msg, setMsg] = useState('')
  const load = () => { api('/audit/flags').then(setFlags); api('/audit/logs').then(setLogs); api('/audit/verify').then(setChain) }
  useEffect(() => { load() }, [])
  const resolve = async (f) => {
    const note = window.prompt('اكتب سبب/نتيجة المعالجة')
    if (!note || note.length < 3) return
    await api(`/audit/flags/${f.id}/resolve`, { method: 'POST', body: { note } }); load()
  }
  const scan = async () => { const r = await api('/audit/scan', { method: 'POST' }); setMsg(`اكتمل الفحص: ${r.flags_found} تنبيه على الطلبات المعلّقة.`); load() }
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-bold flex-1">التدقيق والرقابة</h1>
        <button className="btn btn-primary" onClick={scan}>تشغيل وكيل التدقيق الآن</button>
      </div>
      {msg && <p role="status" className="text-ok font-semibold">{msg}</p>}
      {chain && <p className={`card font-semibold ${chain.valid ? 'text-ok' : 'text-bad'}`}>{chain.valid ? `سلامة السجل: ✓ تم التحقق من ${chain.checked} حركة — لا يوجد أي تعديل غير مصرّح به.` : `⚠ تم اكتشاف تلاعب في السجل عند الحركة رقم ${chain.broken_at}`}</p>}
      <div className="flex gap-2">
        <button className={`btn ${tab === 'flags' ? 'btn-primary' : 'btn-ghost'}`} onClick={() => setTab('flags')}>التنبيهات ({flags.filter((f) => !f.resolved).length})</button>
        <button className={`btn ${tab === 'logs' ? 'btn-primary' : 'btn-ghost'}`} onClick={() => setTab('logs')}>سجل الحركات</button>
      </div>
      {tab === 'flags' && (
        <div className="card !p-0 overflow-x-auto"><table className="w-full min-w-[640px]">
          <thead><tr><th className="th">الطلب</th><th className="th">الخطورة</th><th className="th">التنبيه</th><th className="th"></th></tr></thead>
          <tbody>
            {flags.length === 0 && <tr><td className="td text-muted" colSpan="4">لا توجد تنبيهات.</td></tr>}
            {flags.map((f) => <tr key={f.id} className={f.resolved ? 'opacity-50' : ''}>
              <td className="td"><Link className="underline text-brand-800 font-semibold" to={`/requests/${f.request_id}`}>{f.number}</Link><div className="text-sm text-muted">{f.title}</div></td>
              <td className="td"><span className={`badge ${SEV[f.severity][1]}`}>{SEV[f.severity][0]}</span></td>
              <td className="td">{f.message}</td>
              <td className="td">{!f.resolved && <button className="btn btn-ghost" onClick={() => resolve(f)}>معالجة</button>}</td></tr>)}
          </tbody></table></div>
      )}
      {tab === 'logs' && (
        <div className="card !p-0 overflow-x-auto"><table className="w-full min-w-[640px]">
          <thead><tr><th className="th">الوقت</th><th className="th">المستخدم</th><th className="th">الإجراء</th><th className="th">التفاصيل</th></tr></thead>
          <tbody>{logs.map((l) => <tr key={l.id}><td className="td text-sm whitespace-nowrap">{dateAr(l.ts)}</td><td className="td">{l.user}</td><td className="td font-semibold">{ACTIONS[l.action] || l.action}</td><td className="td text-sm">{l.details}</td></tr>)}</tbody></table></div>
      )}
    </div>
  )
}
