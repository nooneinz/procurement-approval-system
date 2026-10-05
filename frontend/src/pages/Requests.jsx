import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api, money, dateAr, STATUS, ROLE } from '../api.js'
import { useAuth } from '../App.jsx'

export default function Requests() {
  const user = useAuth()
  const [sp, setSp] = useSearchParams()
  const scope = sp.get('scope') || 'visible'
  const [rows, setRows] = useState(null)
  const [status, setStatus] = useState('')
  useEffect(() => { setRows(null); api(`/requests?scope=${scope}`).then(setRows) }, [scope])
  const shown = (rows || []).filter((r) => !status || r.status === status)
  const tabs = [['visible', 'الكل'], ['mine', 'طلباتي'], ['to_approve', 'بانتظار قراري']]
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-bold flex-1">طلبات الشراء</h1>
        {['employee', 'dept_manager'].includes(user.role) && <Link to="/requests/new" className="btn btn-primary">طلب جديد</Link>}
      </div>
      <div className="flex flex-wrap gap-2 items-center">
        {tabs.map(([k, l]) => (
          <button key={k} onClick={() => setSp(k === 'visible' ? {} : { scope: k })} className={`btn ${scope === k ? 'btn-primary' : 'btn-ghost'}`}>{l}</button>
        ))}
        <select className="input !w-auto" value={status} onChange={(e) => setStatus(e.target.value)} aria-label="تصفية بالحالة">
          <option value="">كل الحالات</option>
          {Object.entries(STATUS).map(([k, [l]]) => <option key={k} value={k}>{l}</option>)}
        </select>
      </div>
      <div className="card !p-0 overflow-x-auto">
        <table className="w-full min-w-[720px]">
          <thead><tr><th className="th">الرقم</th><th className="th">العنوان</th><th className="th">القسم</th><th className="th">مقدّم الطلب</th><th className="th">المبلغ</th><th className="th">الحالة</th><th className="th">التاريخ</th></tr></thead>
          <tbody>
            {rows === null && <tr><td className="td" colSpan="7">جارٍ التحميل…</td></tr>}
            {rows && shown.length === 0 && <tr><td className="td text-muted" colSpan="7">لا توجد طلبات.</td></tr>}
            {shown.map((r) => (
              <tr key={r.id} className="hover:bg-brand-50">
                <td className="td font-semibold"><Link className="text-brand-800 underline" to={`/requests/${r.id}`}>{r.number}</Link></td>
                <td className="td">{r.title}{r.flags_open > 0 && <span className="badge bg-red-100 text-red-900 ms-2">⚑ {r.flags_open}</span>}</td>
                <td className="td">{r.department}</td>
                <td className="td">{r.requester}</td>
                <td className="td">{money(r.amount)}</td>
                <td className="td">
                  <span className={`badge ${STATUS[r.status][1]}`}>{STATUS[r.status][0]}</span>
                  {r.waiting_role && <div className="text-xs text-muted mt-1">عند: {ROLE[r.waiting_role]}</div>}
                </td>
                <td className="td text-sm text-muted">{dateAr(r.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
