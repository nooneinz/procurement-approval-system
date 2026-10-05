import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, money } from '../api.js'
import { useAuth } from '../App.jsx'

function Stat({ label, value, to, tone = '' }) {
  const body = (
    <div className={`card h-full ${to ? 'hover:border-navy-700' : ''}`}>
      <div className="text-muted text-sm">{label}</div>
      <div className={`text-2xl font-bold mt-1 ${tone}`}>{value}</div>
    </div>
  )
  return to ? <Link to={to}>{body}</Link> : body
}

export default function Dashboard() {
  const user = useAuth()
  const [d, setD] = useState(null)
  const [depts, setDepts] = useState([])
  const [agents, setAgents] = useState(null)
  useEffect(() => {
    api('/dashboard').then(setD)
    api('/departments').then(setDepts)
    api('/agents/status').then(setAgents)
  }, [])
  if (!d) return <p>جارٍ التحميل…</p>
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">مرحباً، {user.name}</h1>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Stat label="بانتظار قراري" value={d.to_approve} to="/requests?scope=to_approve" tone={d.to_approve ? 'text-warn' : ''} />
        <Stat label="طلبات معلّقة" value={`${d.counts.pending} (${money(d.pending_total)})`} to="/requests" />
        <Stat label="طلبات معتمدة" value={`${d.counts.approved} (${money(d.approved_total)})`} to="/requests" tone="text-ok" />
        {d.open_flags !== null
          ? <Stat label="تنبيهات تدقيق مفتوحة" value={d.open_flags} to="/audit" tone={d.open_flags ? 'text-bad' : ''} />
          : <Stat label="طلبات مرفوضة" value={d.counts.rejected} />}
      </div>

      <section className="card">
        <h2 className="font-bold mb-3">ميزانيات الأقسام</h2>
        {depts.length === 0 && <p className="text-muted">لم تُضف أقسام بعد{user.role === 'admin' ? ' — أضفها من صفحة الإدارة.' : '.'}</p>}
        <div className="space-y-4">
          {depts.map((x) => {
            const used = x.budget ? Math.min(100, ((x.spent + x.committed) / x.budget) * 100) : 0
            return (
              <div key={x.id}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="font-semibold">{x.name}</span>
                  <span className="text-muted">المتبقي {money(x.remaining)} من {money(x.budget)}</span>
                </div>
                <div className="h-3 rounded-full bg-navy-50 overflow-hidden" role="progressbar" aria-valuenow={Math.round(used)} aria-valuemin="0" aria-valuemax="100" aria-label={`استهلاك ميزانية ${x.name}`}>
                  <div className={`h-full ${used > 90 ? 'bg-bad' : 'bg-navy-700'}`} style={{ width: `${used}%` }} />
                </div>
              </div>
            )
          })}
        </div>
      </section>

      {agents && (
        <section className="card">
          <h2 className="font-bold mb-2">وكلاء الذكاء الاصطناعي</h2>
          <ul className="space-y-1 text-sm leading-7">
            <li><b>وكيل التدقيق:</b> فعّال — يفحص كل طلب عند الإرسال (تكرار، تجزئة مشتريات، تجاوز الميزانية، قرب الحدود، عرض واحد).</li>
            <li><b>وكيل المشتريات:</b> {agents.ai_enabled ? `فعّال بنموذج ${agents.model} — يقرأ ملفات العروض ويوصي بالموافقة أو الرفض.` : 'يعمل بالقواعد حالياً؛ قراءة ملفات PDF والصور تتطلب إضافة مفتاح ANTHROPIC_API_KEY.'}</li>
            <li><b>حدود الموافقة:</b> مدير مالي من {money(agents.thresholds.finance_from)}، ومدير عام من {money(agents.thresholds.general_manager_from)}.</li>
          </ul>
        </section>
      )}

      {['employee', 'dept_manager'].includes(user.role) && (
        <Link to="/requests/new" className="btn btn-primary">طلب شراء جديد</Link>
      )}
    </div>
  )
}
