const KEY = 'pas_token'

export const getToken = () => localStorage.getItem(KEY)
export const setToken = (t) => (t ? localStorage.setItem(KEY, t) : localStorage.removeItem(KEY))

export async function api(path, { method = 'GET', body, form } = {}) {
  const headers = {}
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  let payload
  if (form) payload = form
  else if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
    payload = JSON.stringify(body)
  }
  const res = await fetch(`/api${path}`, { method, headers, body: payload })
  if (res.status === 401 && token) {
    setToken(null)
    window.location.href = '/login'
    throw new Error('انتهت الجلسة')
  }
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const d = data.detail
    throw new Error(typeof d === 'string' ? d : Array.isArray(d) ? d.map((x) => x.msg).join('، ') : 'حدث خطأ')
  }
  return data
}

export async function openFile(path) {
  const res = await fetch(`/api${path}`, { headers: { Authorization: `Bearer ${getToken()}` } })
  if (!res.ok) throw new Error('تعذّر فتح الملف')
  window.open(URL.createObjectURL(await res.blob()), '_blank')
}

export const money = (n) => `${Number(n || 0).toLocaleString('en-US', { maximumFractionDigits: 0 })} ر.س`
export const dateAr = (s) => (s ? new Date(s + (s.endsWith('Z') ? '' : 'Z')).toLocaleString('ar-SA', { dateStyle: 'medium', timeStyle: 'short' }) : '—')

export const STATUS = {
  draft: ['مسودة', 'bg-slate-100 text-slate-700'],
  pending: ['بانتظار الموافقة', 'bg-amber-100 text-amber-900'],
  approved: ['معتمد', 'bg-emerald-100 text-emerald-900'],
  rejected: ['مرفوض', 'bg-red-100 text-red-900'],
  cancelled: ['ملغي', 'bg-slate-200 text-slate-600'],
}
export const ROLE = {
  employee: 'موظف', dept_manager: 'مدير قسم', finance_manager: 'مدير مالي', general_manager: 'مدير عام', admin: 'مشرف النظام',
}
export const SEV = { high: ['عالية', 'bg-red-100 text-red-900'], medium: ['متوسطة', 'bg-amber-100 text-amber-900'], low: ['منخفضة', 'bg-slate-100 text-slate-700'] }
