import { useState } from 'react'
import { Link, NavLink } from 'react-router-dom'

const P = {
  calendar: 'M8 2v4M16 2v4M3 10h18M5 4h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z',
  clock: 'M12 6v6l4 2M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20z',
  shield: 'M12 3l8 3v6c0 5-3.5 8.5-8 9-4.5-.5-8-4-8-9V6l8-3zM9 12l2 2 4-4',
  chart: 'M4 20V10M10 20V4M16 20v-7M22 20H2',
  bot: 'M12 3v3M7 8h10a3 3 0 0 1 3 3v6a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3v-6a3 3 0 0 1 3-3zM9 13h.01M15 13h.01M9 17h6',
  users: 'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM22 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8',
  finger: 'M12 11v3a6 6 0 0 1-1 3.4M8 14a4 4 0 0 1 8 0c0 2-.3 4-1.2 5.5M5 12a7 7 0 0 1 14 0c0 2.5-.3 5-1.5 7M3 9.5A10 10 0 0 1 21 9.5',
  bell: 'M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9M10.3 21a1.9 1.9 0 0 0 3.4 0',
  check: 'M20 6L9 17l-5-5',
  refresh: 'M21 12a9 9 0 0 1-15.5 6.2L3 16M3 12a9 9 0 0 1 15.5-6.2L21 8M21 3v5h-5M3 21v-5h5',
  wallet: 'M3 7a2 2 0 0 1 2-2h13v4M3 7v11a2 2 0 0 0 2 2h15V9H5a2 2 0 0 1-2-2zM16 14h.01',
  file: 'M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zM14 2v6h6M9 13h6M9 17h6',
  send: 'M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z',
  github: 'M9 19c-4.3 1.4-4.3-2.5-6-3m12 5v-3.5c0-1 .1-1.4-.5-2 2.8-.3 5.5-1.4 5.5-6a4.6 4.6 0 0 0-1.3-3.2 4.2 4.2 0 0 0-.1-3.2s-1.1-.3-3.5 1.3a12.3 12.3 0 0 0-6.2 0C6.5 2.8 5.4 3.1 5.4 3.1a4.2 4.2 0 0 0-.1 3.2A4.6 4.6 0 0 0 4 9.5c0 4.6 2.7 5.7 5.5 6-.6.6-.6 1.2-.5 2V21',
}

export const Icon = ({ name, size = 22, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true"><path d={P[name]} /></svg>
)

export function Logo({ light = true }) {
  return (
    <span className="inline-flex items-center gap-2 font-bold text-lg">
      <span className={`inline-grid place-items-center w-9 h-9 rounded-lg ${light ? 'bg-white/15' : 'bg-brand-800 text-white'}`}><Icon name="file" size={20} /></span>
      <span>نظام المشتريات والموافقات</span>
    </span>
  )
}

export function PublicHeader() {
  const [open, setOpen] = useState(false)
  const items = [['#features', 'المزايا'], ['#agents', 'الوكلاء'], ['#oman', 'الهوية العُمانية'], ['#how', 'كيف يعمل']]
  return (
    <header className="sticky top-0 z-30 bg-brand-900/95 backdrop-blur text-white border-b border-white/10">
      <div className="max-w-6xl mx-auto px-4 h-16 flex items-center gap-4">
        <Link to="/" className="me-auto"><Logo /></Link>
        <nav className="hidden md:flex gap-1" aria-label="الأقسام">{items.map(([h, l]) => <a key={h} href={h} className="px-3 py-2 rounded-md text-white/85 hover:bg-white/10 font-semibold">{l}</a>)}</nav>
        <Link to="/login" className="btn bg-white text-brand-800 hover:bg-brand-50">تسجيل الدخول</Link>
        <button className="md:hidden btn btn-ghost !px-3" aria-label="القائمة" aria-expanded={open} onClick={() => setOpen(!open)}>☰</button>
      </div>
      {open && <nav className="md:hidden px-4 pb-3 flex flex-col" aria-label="الأقسام">{items.map(([h, l]) => <a key={h} href={h} onClick={() => setOpen(false)} className="py-3 border-t border-white/10">{l}</a>)}</nav>}
    </header>
  )
}

export function Footer({ onHome }) {
  return (
    <footer className="bg-brand-900 text-white/80 mt-auto">
      <div className="max-w-6xl mx-auto px-4 py-10 grid gap-8 md:grid-cols-4">
        <div className="md:col-span-2 space-y-3">
          <div className="text-white"><Logo /></div>
          <p className="text-sm leading-7 max-w-md">نظام مشتريات لشركات سلطنة عُمان: طلبات شراء شفافة، عروض أسعار موثّقة، موافقات متعددة المستويات، وسجل تدقيق كامل مع وكلاء ذكاء اصطناعي.</p>
        </div>
        <div><h3 className="text-white font-bold mb-3">النظام</h3>
          <ul className="space-y-2 text-sm"><li><Link to="/about" className="hover:text-white">الصفحة التعريفية</Link></li><li><Link to="/" className="hover:text-white">لوحة التحكم</Link></li><li><Link to="/agents" className="hover:text-white">الوكلاء</Link></li></ul></div>
        <div><h3 className="text-white font-bold mb-3">المشروع</h3>
          <ul className="space-y-2 text-sm"><li><a className="hover:text-white inline-flex items-center gap-1" href="https://github.com/nooneinz/procurement-approval-system" target="_blank" rel="noreferrer"><Icon name="github" size={16} /> الكود على GitHub</a></li>
            <li>العملة: الريال العماني</li><li>توقيت مسقط (GMT+4)</li></ul></div>
      </div>
      <div className="border-t border-white/10 text-center text-xs py-4">© {new Date().getFullYear()} Procurement &amp; Approval System — جميع الحقوق محفوظة</div>
    </footer>
  )
}

export function AppHeader({ user, nav, right }) {
  const link = ({ isActive }) => `px-3 py-2 rounded-md font-semibold transition-colors ${isActive ? 'bg-white text-brand-800' : 'text-white/90 hover:bg-white/10'}`
  return (
    <header className="sticky top-0 z-30 bg-brand-800 text-white shadow">
      <div className="max-w-6xl mx-auto px-4 py-2 flex flex-wrap items-center gap-x-3 gap-y-2">
        <Link to="/" className="me-2"><Logo /></Link>
        <nav className="flex flex-wrap gap-1 flex-1" aria-label="التنقل الرئيسي">
          {nav.map(([to, label, end]) => <NavLink key={to} to={to} end={end} className={link}>{label}</NavLink>)}
        </nav>
        {right}
      </div>
    </header>
  )
}
