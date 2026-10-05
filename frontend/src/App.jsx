import { useEffect, useState, createContext, useContext, useCallback } from 'react'
import { Routes, Route, Navigate, NavLink, Link, useNavigate } from 'react-router-dom'
import { api, getToken, setToken, ROLE } from './api.js'
import Login from './pages/Login.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Requests from './pages/Requests.jsx'
import NewRequest from './pages/NewRequest.jsx'
import RequestDetail from './pages/RequestDetail.jsx'
import Admin from './pages/Admin.jsx'
import Audit from './pages/Audit.jsx'

const Auth = createContext(null)
export const useAuth = () => useContext(Auth)

function Notifications() {
  const [items, setItems] = useState([])
  const [open, setOpen] = useState(false)
  const nav = useNavigate()
  const load = useCallback(() => api('/notifications').then(setItems).catch(() => {}), [])
  useEffect(() => { load(); const t = setInterval(load, 15000); return () => clearInterval(t) }, [load])
  const unread = items.filter((n) => !n.read).length
  const toggle = async () => {
    setOpen(!open)
    if (!open && unread) { await api('/notifications/read', { method: 'POST' }); setTimeout(load, 1500) }
  }
  return (
    <div className="relative">
      <button className="btn btn-ghost !min-h-[44px]" onClick={toggle} aria-label="التنبيهات" aria-expanded={open}>
        التنبيهات {unread > 0 && <span className="badge bg-red-700 text-white">{unread}</span>}
      </button>
      {open && (
        <div className="absolute end-0 mt-2 w-80 max-w-[85vw] card shadow-lg z-20 max-h-96 overflow-auto !p-2">
          {items.length === 0 && <p className="p-3 text-muted">لا توجد تنبيهات.</p>}
          {items.map((n) => (
            <button key={n.id} className={`block w-full text-start p-3 rounded-md hover:bg-navy-50 ${n.read ? '' : 'font-semibold'}`}
              onClick={() => { setOpen(false); n.request_id && nav(`/requests/${n.request_id}`) }}>
              {n.message}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function Shell({ user, onLogout, children }) {
  const canAudit = ['admin', 'finance_manager', 'general_manager'].includes(user.role)
  const link = ({ isActive }) => `px-3 py-2 rounded-md font-semibold ${isActive ? 'bg-white text-navy-800' : 'text-white/90 hover:bg-white/10'}`
  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-navy-800 text-white">
        <div className="max-w-6xl mx-auto px-4 py-3 flex flex-wrap items-center gap-3">
          <Link to="/" className="font-bold text-lg ms-1">نظام المشتريات والموافقات</Link>
          <nav className="flex flex-wrap gap-1 flex-1" aria-label="التنقل الرئيسي">
            <NavLink to="/" end className={link}>لوحة التحكم</NavLink>
            <NavLink to="/requests" className={link}>الطلبات</NavLink>
            {canAudit && <NavLink to="/audit" className={link}>التدقيق</NavLink>}
            {['admin', 'finance_manager', 'dept_manager'].includes(user.role) && <NavLink to="/admin" className={link}>الإدارة</NavLink>}
          </nav>
          <span className="text-sm text-white/80">{user.name} — {ROLE[user.role]}</span>
          <div className="[&_.btn]:!text-navy-800"><Notifications /></div>
          <button className="btn btn-ghost !text-navy-800" onClick={onLogout}>خروج</button>
        </div>
      </header>
      <main className="max-w-6xl w-full mx-auto px-4 py-6 flex-1">{children}</main>
      <footer className="text-center text-sm text-muted py-4">Procurement &amp; Approval System</footer>
    </div>
  )
}

export default function App() {
  const [user, setUser] = useState(null)
  const [ready, setReady] = useState(false)
  useEffect(() => {
    if (!getToken()) return setReady(true)
    api('/me').then(setUser).catch(() => setToken(null)).finally(() => setReady(true))
  }, [])
  const logout = () => { setToken(null); setUser(null) }
  if (!ready) return <p className="p-8">جارٍ التحميل…</p>
  if (!user) return (
    <Routes>
      <Route path="/login" element={<Login onLogin={setUser} />} />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
  return (
    <Auth.Provider value={user}>
      <Shell user={user} onLogout={logout}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/requests" element={<Requests />} />
          <Route path="/requests/new" element={<NewRequest />} />
          <Route path="/requests/:id" element={<RequestDetail />} />
          <Route path="/audit" element={<Audit />} />
          <Route path="/admin" element={<Admin />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Shell>
    </Auth.Provider>
  )
}
