import { useState } from 'react'
import { api, setToken } from '../api.js'

export default function Login({ onLogin }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true); setErr('')
    try {
      const r = await api('/auth/login', { method: 'POST', body: { email, password } })
      setToken(r.token); onLogin(r.user); window.history.replaceState({}, '', '/')
    } catch (ex) { setErr(ex.message) } finally { setBusy(false) }
  }

  return (
    <div className="min-h-screen grid md:grid-cols-2">
      <div className="bg-navy-800 text-white p-10 flex flex-col justify-center">
        <h1 className="text-3xl font-bold mb-4">نظام المشتريات والموافقات</h1>
        <p className="text-white/85 max-w-md leading-8">
          طلبات شراء شفافة، عروض أسعار موثّقة، وموافقات متعددة المستويات حسب الصلاحية،
          مع سجل تدقيق كامل لكل حركة ووكلاء ذكاء اصطناعي يراجعون العروض ويرصدون المخالفات.
        </p>
      </div>
      <div className="flex items-center justify-center p-6">
        <form onSubmit={submit} className="card w-full max-w-sm space-y-4">
          <h2 className="text-xl font-bold">تسجيل الدخول</h2>
          <div>
            <label className="lbl" htmlFor="email">البريد الإلكتروني</label>
            <input id="email" className="input" type="email" dir="ltr" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div>
            <label className="lbl" htmlFor="pw">كلمة المرور</label>
            <input id="pw" className="input" type="password" dir="ltr" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
          {err && <p role="alert" className="text-bad font-semibold">{err}</p>}
          <button className="btn btn-primary w-full" disabled={busy}>{busy ? 'جارٍ الدخول…' : 'دخول'}</button>
        </form>
      </div>
    </div>
  )
}
