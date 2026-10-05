import { useEffect, useState } from 'react'
import { api, money, ROLE } from '../api.js'
import { useAuth } from '../App.jsx'

function Departments({ canEdit }) {
  const [rows, setRows] = useState([])
  const [f, setF] = useState({ name: '', annual_budget: '' })
  const [err, setErr] = useState('')
  const load = () => api('/departments').then(setRows)
  useEffect(() => { load() }, [])
  const add = async (e) => {
    e.preventDefault(); setErr('')
    try { await api('/departments', { method: 'POST', body: { name: f.name, annual_budget: Number(f.annual_budget) } }); setF({ name: '', annual_budget: '' }); load() } catch (x) { setErr(x.message) }
  }
  const edit = async (d) => {
    const v = window.prompt(`الميزانية السنوية الجديدة لقسم ${d.name}`, d.budget)
    if (v === null || isNaN(Number(v))) return
    await api(`/departments/${d.id}`, { method: 'PATCH', body: { name: d.name, annual_budget: Number(v) } }); load()
  }
  return (
    <div className="space-y-4">
      {canEdit && (
        <form onSubmit={add} className="card grid md:grid-cols-3 gap-3 items-end">
          <div><label className="lbl" htmlFor="dn">اسم القسم</label><input id="dn" className="input" required value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></div>
          <div><label className="lbl" htmlFor="db">الميزانية السنوية (ر.ع)</label><input id="db" className="input" type="number" min="0" required value={f.annual_budget} onChange={(e) => setF({ ...f, annual_budget: e.target.value })} /></div>
          <button className="btn btn-primary">إضافة قسم</button>
          {err && <p role="alert" className="text-bad md:col-span-3">{err}</p>}
        </form>
      )}
      <div className="card !p-0 overflow-x-auto"><table className="w-full min-w-[560px]">
        <thead><tr><th className="th">القسم</th><th className="th">الميزانية</th><th className="th">المصروف</th><th className="th">المحجوز</th><th className="th">المتبقي</th><th className="th"></th></tr></thead>
        <tbody>
          {rows.length === 0 && <tr><td className="td text-muted" colSpan="6">لا توجد أقسام.</td></tr>}
          {rows.map((d) => <tr key={d.id}><td className="td font-semibold">{d.name}</td><td className="td">{money(d.budget)}</td><td className="td">{money(d.spent)}</td><td className="td">{money(d.committed)}</td><td className="td">{money(d.remaining)}</td>
            <td className="td">{canEdit && <button className="btn btn-ghost" onClick={() => edit(d)}>تعديل الميزانية</button>}</td></tr>)}
        </tbody></table></div>
    </div>
  )
}

function Vendors({ canAdd }) {
  const [rows, setRows] = useState([])
  const [f, setF] = useState({ name: '', tax_number: '', email: '', phone: '' })
  const [err, setErr] = useState('')
  const load = () => api('/vendors').then(setRows)
  useEffect(() => { load() }, [])
  const add = async (e) => { e.preventDefault(); setErr(''); try { await api('/vendors', { method: 'POST', body: f }); setF({ name: '', tax_number: '', email: '', phone: '' }); load() } catch (x) { setErr(x.message) } }
  return (
    <div className="space-y-4">
      {canAdd && (
        <form onSubmit={add} className="card grid md:grid-cols-5 gap-3 items-end">
          <div className="md:col-span-2"><label className="lbl" htmlFor="vn">اسم المورد</label><input id="vn" className="input" required value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></div>
          <div><label className="lbl" htmlFor="vt">الرقم الضريبي (VATIN)</label><input id="vt" className="input" dir="ltr" value={f.tax_number} onChange={(e) => setF({ ...f, tax_number: e.target.value })} /></div>
          <div><label className="lbl" htmlFor="vp">الجوال</label><input id="vp" className="input" dir="ltr" placeholder="+968 9XXX XXXX" value={f.phone} onChange={(e) => setF({ ...f, phone: e.target.value })} /></div>
          <button className="btn btn-primary">إضافة مورد</button>
          {err && <p role="alert" className="text-bad md:col-span-5">{err}</p>}
        </form>
      )}
      <div className="card !p-0 overflow-x-auto"><table className="w-full min-w-[520px]">
        <thead><tr><th className="th">المورد</th><th className="th">الرقم الضريبي</th><th className="th">الجوال</th></tr></thead>
        <tbody>{rows.length === 0 && <tr><td className="td text-muted" colSpan="3">لا يوجد موردون.</td></tr>}
          {rows.map((v) => <tr key={v.id}><td className="td font-semibold">{v.name}</td><td className="td" dir="ltr">{v.tax_number || '—'}</td><td className="td" dir="ltr">{v.phone || '—'}</td></tr>)}</tbody></table></div>
    </div>
  )
}

function Users() {
  const [rows, setRows] = useState([])
  const [depts, setDepts] = useState([])
  const [f, setF] = useState({ name: '', email: '', password: '', role: 'employee', department_id: '' })
  const [err, setErr] = useState('')
  const load = () => api('/users').then(setRows)
  useEffect(() => { load(); api('/departments').then(setDepts) }, [])
  const needsDept = ['employee', 'dept_manager'].includes(f.role)
  const add = async (e) => {
    e.preventDefault(); setErr('')
    try { await api('/users', { method: 'POST', body: { ...f, department_id: needsDept ? Number(f.department_id) : null } }); setF({ ...f, name: '', email: '', password: '' }); load() } catch (x) { setErr(x.message) }
  }
  const toggle = async (u) => { try { await api(`/users/${u.id}`, { method: 'PATCH', body: { active: !u.active } }); load() } catch (x) { setErr(x.message) } }
  return (
    <div className="space-y-4">
      <form onSubmit={add} className="card grid md:grid-cols-6 gap-3 items-end">
        <div className="md:col-span-2"><label className="lbl" htmlFor="un">الاسم</label><input id="un" className="input" required value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></div>
        <div className="md:col-span-2"><label className="lbl" htmlFor="ue">البريد</label><input id="ue" className="input" type="email" dir="ltr" required value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} /></div>
        <div className="md:col-span-2"><label className="lbl" htmlFor="up">كلمة المرور (8 أحرف فأكثر)</label><input id="up" className="input" type="password" dir="ltr" minLength={8} required autoComplete="new-password" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} /></div>
        <div className="md:col-span-2"><label className="lbl" htmlFor="ur">الدور</label><select id="ur" className="input" value={f.role} onChange={(e) => setF({ ...f, role: e.target.value })}>{Object.entries(ROLE).map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></div>
        <div className="md:col-span-2"><label className="lbl" htmlFor="ud">القسم</label><select id="ud" className="input" disabled={!needsDept} required={needsDept} value={f.department_id} onChange={(e) => setF({ ...f, department_id: e.target.value })}><option value="">—</option>{depts.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}</select></div>
        <button className="btn btn-primary md:col-span-2">إضافة مستخدم</button>
        {err && <p role="alert" className="text-bad md:col-span-6">{err}</p>}
      </form>
      <div className="card !p-0 overflow-x-auto"><table className="w-full min-w-[640px]">
        <thead><tr><th className="th">الاسم</th><th className="th">البريد</th><th className="th">الدور</th><th className="th">القسم</th><th className="th">الحالة</th><th className="th"></th></tr></thead>
        <tbody>{rows.map((u) => <tr key={u.id}><td className="td font-semibold">{u.name}</td><td className="td" dir="ltr">{u.email}</td><td className="td">{u.role_label}</td><td className="td">{u.department || '—'}</td>
          <td className="td">{u.active ? 'فعّال' : 'معطّل'}</td><td className="td"><button className="btn btn-ghost" onClick={() => toggle(u)}>{u.active ? 'تعطيل' : 'تفعيل'}</button></td></tr>)}</tbody></table></div>
    </div>
  )
}

export default function Admin() {
  const user = useAuth()
  const tabs = [['depts', 'الأقسام والميزانيات'], ['vendors', 'الموردون'], ...(user.role === 'admin' ? [['users', 'المستخدمون']] : [])]
  const [tab, setTab] = useState('depts')
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">الإدارة</h1>
      <div className="flex gap-2 flex-wrap">{tabs.map(([k, l]) => <button key={k} className={`btn ${tab === k ? 'btn-primary' : 'btn-ghost'}`} onClick={() => setTab(k)}>{l}</button>)}</div>
      {tab === 'depts' && <Departments canEdit={['admin', 'finance_manager'].includes(user.role)} />}
      {tab === 'vendors' && <Vendors canAdd />}
      {tab === 'users' && <Users />}
    </div>
  )
}
