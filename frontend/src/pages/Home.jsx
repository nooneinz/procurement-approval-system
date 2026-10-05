import { Link } from 'react-router-dom'
import { Icon } from '../layout.jsx'

const FEATURES = [
  ['file', 'طلبات شراء منظّمة', 'بنود وكميات وأسعار تقديرية ومبررات واضحة، وكل طلب برقم تسلسلي يُتتبع من الإنشاء حتى الاعتماد.'],
  ['wallet', 'عروض أسعار موثّقة', 'رفع ملفات PDF أو صور لكل عرض، مقارنة بين الموردين، واختيار العرض مع تبريره إن لم يكن الأقل سعراً.'],
  ['check', 'موافقات متعددة المستويات', 'مدير القسم ثم المدير المالي ثم المدير العام حسب قيمة الطلب، ولا يوافق أحد على طلبه.'],
  ['chart', 'ميزانيات الأقسام', 'المصروف والمحجوز والمتبقي لحظياً، وتنبيه فوري عند تجاوز الميزانية قبل أن يصل الطلب للمدير.'],
  ['shield', 'سجل تدقيق مقاوم للتلاعب', 'كل حركة بتجزئة SHA-256 متسلسلة؛ أي تعديل على سجل قديم يُكتشف فوراً.'],
  ['bell', 'تنبيهات فورية', 'يصل التنبيه لصاحب القرار التالي عند كل مرحلة: وصول طلب، موافقة، رفض، اعتماد.'],
]

const STEPS = [
  ['1', 'إنشاء الطلب', 'الموظف يحدد البنود والمبررات ويرفق عروض الموردين.'],
  ['2', 'فحص الوكلاء', 'وكيل التدقيق يرصد المخالفات ووكيل المشتريات يوصي.'],
  ['3', 'الموافقات', 'تتدرج الموافقة حسب القيمة والصلاحية.'],
  ['4', 'الاعتماد والتوثيق', 'يُسجَّل القرار ويُحتسب على ميزانية القسم.'],
]

export default function Home({ authed }) {
  return (
    <>
      <section className="relative overflow-hidden bg-gradient-to-br from-brand-900 via-brand-800 to-brand-700 text-white">
        <div className="absolute inset-0 pattern opacity-[0.07]" aria-hidden="true" />
        <div className="relative max-w-6xl mx-auto px-4 py-16 md:py-24 grid md:grid-cols-2 gap-10 items-center">
          <div className="space-y-6">
            <span className="badge bg-white/15 text-white">لشركات سلطنة عُمان</span>
            <h1 className="text-3xl md:text-5xl font-bold leading-[1.4]">مشتريات شفافة، وموافقات منضبطة، ووكلاء يراجعون قبل أن تُصرف الأموال</h1>
            <p className="text-white/85 text-lg leading-8 max-w-xl">من طلب الشراء إلى عرض السعر إلى الاعتماد — نظام واحد يضبط الميزانية والصلاحيات ويوثّق كل حركة.</p>
            <div className="flex flex-wrap gap-3">
              <Link to={authed ? '/' : '/login'} className="btn bg-white text-brand-800 hover:bg-brand-50 !min-h-[48px] px-6">{authed ? 'الذهاب إلى لوحة التحكم' : 'تسجيل الدخول'}</Link>
              <a href="#features" className="btn border border-white/40 text-white hover:bg-white/10 !min-h-[48px] px-6">اكتشف المزايا</a>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3" aria-hidden="true">
            {[['file', 'طلب شراء'], ['wallet', 'عروض أسعار'], ['bot', 'وكيل التدقيق'], ['chart', 'الميزانية'], ['check', 'موافقة'], ['shield', 'سجل تدقيق']].map(([i, t], k) => (
              <div key={t} className={`rounded-xl bg-white/10 border border-white/15 p-5 flex items-center gap-3 ${k % 2 ? 'translate-y-4' : ''}`}><Icon name={i} size={26} /><span className="font-semibold">{t}</span></div>
            ))}
          </div>
        </div>
      </section>

      <section id="features" className="max-w-6xl mx-auto px-4 py-16 scroll-mt-20">
        <h2 className="text-2xl md:text-3xl font-bold text-center mb-2">ضبط كامل لدورة الشراء</h2>
        <p className="text-center text-muted mb-10">بدل رسائل متفرقة وملفات لا يعرف أحد آخر نسخة منها.</p>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {FEATURES.map(([i, t, d]) => (
            <article key={t} className="card hover:shadow-md transition-shadow">
              <span className="inline-grid place-items-center w-11 h-11 rounded-lg bg-brand-50 text-brand-800 mb-3"><Icon name={i} /></span>
              <h3 className="font-bold mb-1">{t}</h3><p className="text-sm text-muted leading-7">{d}</p>
            </article>
          ))}
        </div>
      </section>

      <section id="agents" className="bg-white border-y border-line scroll-mt-20">
        <div className="max-w-6xl mx-auto px-4 py-16">
          <h2 className="text-2xl md:text-3xl font-bold text-center mb-2">وكلاء ذكاء اصطناعي تتحدث معهم</h2>
          <p className="text-center text-muted mb-10">اسأل بالعربية، فيستدعي الوكيل أدوات النظام ويجيبك بأرقام حقيقية من بياناتك — دون أن يغيّر شيئاً بنفسه.</p>
          <div className="grid md:grid-cols-2 gap-6">
            <article className="card space-y-3"><div className="flex items-center gap-3"><span className="grid place-items-center w-11 h-11 rounded-lg bg-brand-800 text-white"><Icon name="wallet" /></span><h3 className="font-bold text-lg">وكيل المشتريات</h3></div>
              <p className="text-sm text-muted leading-7">يقرأ ملفات عروض الأسعار ويقارن الإجمالي بالمُدخل وبالميزانية وبسجل المورد، ثم يوصي المدير بالموافقة أو الرفض أو المراجعة مع السبب.</p>
              <ul className="text-sm space-y-1 list-disc ms-5"><li>«ما الطلبات المعلّقة؟»</li><li>«قارن عروض الطلب PR-2026-0001»</li><li>«ما سجل المورد شركة مسقط؟»</li></ul></article>
            <article className="card space-y-3"><div className="flex items-center gap-3"><span className="grid place-items-center w-11 h-11 rounded-lg bg-brand-800 text-white"><Icon name="shield" /></span><h3 className="font-bold text-lg">وكيل التدقيق</h3></div>
              <p className="text-sm text-muted leading-7">يفحص كل طلب قبل أن يصل للمدراء: طلب مكرر، تجزئة مشتريات لتفادي الحدود، مبلغ قريب من حد الموافقة، عرض واحد، تجاوز الميزانية، أو عدم تطابق الملف.</p>
              <ul className="text-sm space-y-1 list-disc ms-5"><li>«ما تنبيهات التدقيق المفتوحة؟»</li><li>«لخّص الإنفاق حسب القسم»</li><li>«اشرح الطلب PR-2026-0001»</li></ul></article>
          </div>
        </div>
      </section>

      <section id="oman" className="max-w-6xl mx-auto px-4 py-16 scroll-mt-20">
        <div className="grid md:grid-cols-2 gap-10 items-center">
          <div className="space-y-4">
            <h2 className="text-2xl md:text-3xl font-bold">مصمم لبيئة الأعمال في سلطنة عُمان</h2>
            <p className="text-muted leading-8">العملة هي الريال العماني بثلاث خانات عشرية (البيسة)، وحدود الموافقة قابلة للضبط بما يناسب سياسة شركتك.</p>
          </div>
          <ul className="grid grid-cols-2 gap-3">
            {[['wallet', 'الريال العماني بالبيسة'], ['check', 'حدود موافقة قابلة للضبط'], ['users', 'صلاحيات حسب الدور'], ['file', 'ضريبة القيمة المضافة في العروض'], ['bell', 'تنبيهات فورية'], ['shield', 'سجل تدقيق كامل']].map(([i, t]) => (
              <li key={t} className="card !p-4 flex items-center gap-3 text-sm font-semibold"><span className="text-brand-700"><Icon name={i} /></span>{t}</li>
            ))}
          </ul>
        </div>
      </section>

      <section id="how" className="bg-brand-50 border-y border-line scroll-mt-20">
        <div className="max-w-6xl mx-auto px-4 py-16">
          <h2 className="text-2xl md:text-3xl font-bold text-center mb-10">كيف يعمل</h2>
          <ol className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {STEPS.map(([n, t, d]) => (
              <li key={n} className="card space-y-2"><span className="inline-grid place-items-center w-9 h-9 rounded-full bg-brand-800 text-white font-bold">{n}</span><h3 className="font-bold">{t}</h3><p className="text-sm text-muted leading-7">{d}</p></li>
            ))}
          </ol>
        </div>
      </section>

      <section className="max-w-6xl mx-auto px-4 py-16 text-center space-y-4">
        <h2 className="text-2xl md:text-3xl font-bold">جاهز للبدء؟</h2>
        <p className="text-muted">سجّل الدخول وأنشئ أول طلب شراء.</p>
        <Link to={authed ? '/' : '/login'} className="btn btn-primary !min-h-[48px] px-8">{authed ? 'لوحة التحكم' : 'تسجيل الدخول'}</Link>
      </section>
    </>
  )
}
