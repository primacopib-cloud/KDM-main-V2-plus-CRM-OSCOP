import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { CreditCard, FileSignature, CheckCircle2, Loader2, Mail, ArrowRight } from 'lucide-react';
import { toast } from 'sonner';
import NavBar from '../components/NavBar';
import { PlanPicker } from '../components/onboarding/PlanPicker';
import { API } from '../services/http';

const TERRITOIRES = ['Guadeloupe', 'Martinique', 'Guyane', 'La Réunion', 'Mayotte', 'Saint-Martin'];
const inputCls = 'w-full h-11 rounded-xl px-3.5 text-sm text-white placeholder-white/35 bg-white/[0.05] border border-[#D9B35A]/25 focus:outline-none focus:ring-1 focus:ring-[#D9B35A]/60';
const labelCls = 'block text-xs text-white/60 mb-1.5';

const Stepper = ({ current }) => {
  const { t } = useTranslation();
  const steps = [t('vendorOnboarding.stepPayment'), t('vendorOnboarding.stepConvention'), t('vendorOnboarding.stepSignature'), t('vendorOnboarding.stepActivation')];
  return (
    <div className="flex items-center justify-center gap-2 mb-8" data-testid="vendor-onboarding-stepper">
      {steps.map((s, i) => (
        <div key={s} className="flex items-center gap-2">
          <span className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${
            i < current ? 'bg-[#7BC94E] text-[#12240a]' : i === current ? 'bg-[#D4AF37] text-[#1F0A33]' : 'bg-white/10 text-white/50'
          }`}>{i < current ? '✓' : i + 1}</span>
          <span className={`text-xs hidden sm:inline ${i === current ? 'text-[#E9CF8E] font-semibold' : 'text-white/45'}`}>{s}</span>
          {i < steps.length - 1 && <span className="w-6 h-px bg-white/15" />}
        </div>
      ))}
    </div>
  );
};

export default function VendorOnboardingPage() {
  const [params] = useSearchParams();
  const { t, i18n } = useTranslation();
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const [, setOb] = useState(null);
  const [start, setStart] = useState({ company: '', contact_name: '', email: '', phone: '', siret: '', plan_slug: params.get('plan') || 'ess-acces-pro', member_type: 'vendor' });
  const [conv, setConv] = useState({ forme_sociale: '', capital: '', rcs_ville: '', adresse: '', rep_nom: '', rep_prenom: '', rep_qualite: '', territoires: [], lieu_signature: '' });
  const [sign, setSign] = useState({ nom: '', qualite: '', lu_approuve: false });

  const oid = params.get('onboarding_id');

  useEffect(() => {
    if (params.get('step') === 'paid' && oid) {
      fetch(`${API}/vendor-onboarding/${oid}/status`)
        .then((r) => r.json())
        .then((d) => {
          setOb(d);
          if (d.status === 'PAID' || d.status === 'INFO_COMPLETED') { setStep(1); toast.success(t('vendorOnboarding.paidToast')); }
          else if (d.status === 'SIGNED' || d.status === 'ACTIVATED') setStep(3);
          else toast.info(t('vendorOnboarding.pendingToast'));
        });
    }
    if (params.get('step') === 'cancelled') toast.error(t('vendorOnboarding.cancelledToast'));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const launchPayment = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const r = await fetch(`${API}/vendor-onboarding/start`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...start, origin_url: window.location.origin, locale: (i18n.language || 'fr').slice(0, 2) }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Erreur');
      window.location.href = d.checkout_url;
    } catch (err) { toast.error(err.message); setBusy(false); }
  };

  const saveConvention = async (e) => {
    e.preventDefault();
    if (conv.territoires.length === 0) return toast.error(t('vendorOnboarding.territoireErr'));
    setBusy(true);
    try {
      const r = await fetch(`${API}/vendor-onboarding/${oid}/convention-fields`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(conv),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Erreur');
      setStep(2);
    } catch (err) { toast.error(err.message); } finally { setBusy(false); }
  };

  const doSign = async () => {
    if (!sign.lu_approuve) return toast.error(t('vendorOnboarding.signCheckErr'));
    if (!sign.nom || !sign.qualite) return toast.error(t('vendorOnboarding.signFieldsErr'));
    setBusy(true);
    try {
      const r = await fetch(`${API}/vendor-onboarding/${oid}/sign`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(sign),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Erreur');
      toast.success(t('vendorOnboarding.signedToast', { code: d.verification_code }));
      setStep(3);
    } catch (err) { toast.error(err.message); } finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen" data-testid="vendor-onboarding-page">
      <NavBar />
      <div className="max-w-3xl mx-auto px-4 pt-28 pb-16">
        <h1 className="text-3xl font-bold text-white text-center mb-2" style={{ fontFamily: '"Playfair Display", serif' }}>
          {t('vendorOnboarding.title')} <span className="text-[#D9B35A]">{t('vendorOnboarding.titleAccent')}</span>
        </h1>
        <p className="text-white/60 text-sm text-center mb-8">{t('vendorOnboarding.subtitle')}</p>
        <Stepper current={step} />

        {step === 0 && (
          <form onSubmit={launchPayment} className="glass-panel rounded-[22px] p-6 space-y-4" data-testid="vendor-start-form">
            <div>
              <p className="text-xs text-white/60 mb-2">{t('vendorOnboarding.memberTypeLabel')}</p>
              <div className="grid sm:grid-cols-2 gap-3" data-testid="member-type-choice">
                {[
                  { value: 'vendor', title: t('vendorOnboarding.vendorTitle'), desc: t('vendorOnboarding.vendorDesc') },
                  { value: 'buyer', title: t('vendorOnboarding.buyerTitle'), desc: t('vendorOnboarding.buyerDesc') },
                ].map((tp) => (
                  <button type="button" key={tp.value} data-testid={`member-type-${tp.value}`}
                    onClick={() => setStart({ ...start, member_type: tp.value })}
                    className={`text-left p-4 rounded-xl border transition-colors ${
                      start.member_type === tp.value
                        ? 'border-[#D9B35A] bg-[#D9B35A]/12'
                        : 'border-white/15 hover:border-white/35'
                    }`}>
                    <span className={`block text-sm font-bold ${start.member_type === tp.value ? 'text-[#E9CF8E]' : 'text-white/85'}`}>{tp.title}</span>
                    <span className="block text-[11px] text-white/55 mt-1">{tp.desc}</span>
                  </button>
                ))}
              </div>
            </div>
            <div className="grid sm:grid-cols-2 gap-4">
              <div><label className={labelCls}>{t('vendorOnboarding.company')}</label>
                <input required className={inputCls} data-testid="vendor-company-input" value={start.company} onChange={(e) => setStart({ ...start, company: e.target.value })} placeholder={t('vendorOnboarding.companyPh')} /></div>
              <div><label className={labelCls}>{t('vendorOnboarding.contact')}</label>
                <input required className={inputCls} data-testid="vendor-contact-input" value={start.contact_name} onChange={(e) => setStart({ ...start, contact_name: e.target.value })} placeholder={t('vendorOnboarding.contactPh')} /></div>
              <div><label className={labelCls}>{t('vendorOnboarding.email')}</label>
                <input required type="email" className={inputCls} data-testid="vendor-email-input" value={start.email} onChange={(e) => setStart({ ...start, email: e.target.value })} placeholder={t('vendorOnboarding.emailPh')} /></div>
              <div><label className={labelCls}>{t('vendorOnboarding.phone')}</label>
                <input required className={inputCls} value={start.phone} onChange={(e) => setStart({ ...start, phone: e.target.value })} placeholder="06 00 00 00 00" /></div>
              <div className="sm:col-span-2"><label className={labelCls}>{t('vendorOnboarding.siret')}</label>
                <input required minLength={9} className={inputCls} data-testid="vendor-siret-input" value={start.siret} onChange={(e) => setStart({ ...start, siret: e.target.value })} placeholder={t('vendorOnboarding.siretPh')} /></div>
            </div>
            <PlanPicker value={start.plan_slug} onChange={(slug) => setStart({ ...start, plan_slug: slug })} />
            <button type="submit" disabled={busy} data-testid="vendor-pay-btn"
              className="w-full h-13 py-3.5 rounded-xl inline-flex items-center justify-center gap-2 text-sm font-bold disabled:opacity-50"
              style={{ background: 'linear-gradient(135deg, #D9B35A 0%, #b8933e 100%)', color: '#1F0A33' }}>
              {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <CreditCard className="w-4 h-4" />} {t('vendorOnboarding.payBtn')}
            </button>
            <p className="text-[11px] text-white/45 text-center">{t('vendorOnboarding.payNote')}</p>
          </form>
        )}

        {step === 1 && (
          <form onSubmit={saveConvention} className="glass-panel rounded-[22px] p-6 space-y-4" data-testid="vendor-convention-form">
            <p className="text-sm text-white/70">{t('vendorOnboarding.convIntro')}</p>
            <div className="grid sm:grid-cols-2 gap-4">
              <div><label className={labelCls}>{t('vendorOnboarding.formeSociale')}</label>
                <input className={inputCls} value={conv.forme_sociale} onChange={(e) => setConv({ ...conv, forme_sociale: e.target.value })} placeholder={t('vendorOnboarding.formeSocialePh')} /></div>
              <div><label className={labelCls}>{t('vendorOnboarding.capital')}</label>
                <input required className={inputCls} data-testid="vendor-capital-input" value={conv.capital} onChange={(e) => setConv({ ...conv, capital: e.target.value })} placeholder="10 000" /></div>
              <div><label className={labelCls}>{t('vendorOnboarding.rcs')}</label>
                <input required className={inputCls} data-testid="vendor-rcs-input" value={conv.rcs_ville} onChange={(e) => setConv({ ...conv, rcs_ville: e.target.value })} placeholder="Pointe-à-Pitre" /></div>
              <div><label className={labelCls}>{t('vendorOnboarding.adresse')}</label>
                <input required className={inputCls} value={conv.adresse} onChange={(e) => setConv({ ...conv, adresse: e.target.value })} /></div>
              <div><label className={labelCls}>{t('vendorOnboarding.repPrenom')}</label>
                <input required className={inputCls} value={conv.rep_prenom} onChange={(e) => setConv({ ...conv, rep_prenom: e.target.value })} /></div>
              <div><label className={labelCls}>{t('vendorOnboarding.repNom')}</label>
                <input required className={inputCls} data-testid="vendor-rep-nom-input" value={conv.rep_nom} onChange={(e) => setConv({ ...conv, rep_nom: e.target.value })} /></div>
              <div><label className={labelCls}>{t('vendorOnboarding.repQualite')}</label>
                <input required className={inputCls} value={conv.rep_qualite} onChange={(e) => setConv({ ...conv, rep_qualite: e.target.value })} placeholder={t('vendorOnboarding.repQualitePh')} /></div>
              <div><label className={labelCls}>{t('vendorOnboarding.lieuSignature')}</label>
                <input required className={inputCls} value={conv.lieu_signature} onChange={(e) => setConv({ ...conv, lieu_signature: e.target.value })} placeholder="Baie-Mahault" /></div>
            </div>
            <div>
              <label className={labelCls}>{t('vendorOnboarding.territoires')}</label>
              <div className="flex flex-wrap gap-2">
                {TERRITOIRES.map((tt) => (
                  <button type="button" key={tt} data-testid={`vendor-territoire-${tt}`}
                    onClick={() => setConv({ ...conv, territoires: conv.territoires.includes(tt) ? conv.territoires.filter((x) => x !== tt) : [...conv.territoires, tt] })}
                    className={`px-3 py-1.5 rounded-full text-xs font-semibold border transition-colors ${
                      conv.territoires.includes(tt) ? 'bg-[#D9B35A]/20 border-[#D9B35A] text-[#E9CF8E]' : 'border-white/20 text-white/60 hover:border-white/40'
                    }`}>{tt}</button>
                ))}
              </div>
            </div>
            <button type="submit" disabled={busy} data-testid="vendor-convention-submit"
              className="w-full py-3.5 rounded-xl inline-flex items-center justify-center gap-2 text-sm font-bold disabled:opacity-50"
              style={{ background: 'linear-gradient(135deg, #D9B35A 0%, #b8933e 100%)', color: '#1F0A33' }}>
              {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowRight className="w-4 h-4" />} {t('vendorOnboarding.generateBtn')}
            </button>
          </form>
        )}

        {step === 2 && (
          <div className="glass-panel rounded-[22px] p-6 space-y-4" data-testid="vendor-sign-step">
            <p className="text-sm text-white/70 flex items-center gap-2"><FileSignature className="w-4 h-4 text-[#D9B35A]" />
              {t('vendorOnboarding.signIntro')}</p>
            <iframe title="Convention" src={`${API}/vendor-onboarding/${oid}/convention.pdf`} className="w-full rounded-xl border border-[#D9B35A]/25" style={{ height: 420, background: 'white' }} data-testid="vendor-convention-preview" />
            <div className="grid sm:grid-cols-2 gap-4">
              <div><label className={labelCls}>{t('vendorOnboarding.signNom')}</label>
                <input required className={inputCls} data-testid="vendor-sign-nom" value={sign.nom} onChange={(e) => setSign({ ...sign, nom: e.target.value })} /></div>
              <div><label className={labelCls}>{t('vendorOnboarding.signQualite')}</label>
                <input required className={inputCls} data-testid="vendor-sign-qualite" value={sign.qualite} onChange={(e) => setSign({ ...sign, qualite: e.target.value })} placeholder={t('vendorOnboarding.signQualitePh')} /></div>
            </div>
            <label className="flex items-start gap-2.5 text-sm text-white/80 cursor-pointer">
              <input type="checkbox" checked={sign.lu_approuve} data-testid="vendor-sign-checkbox"
                onChange={(e) => setSign({ ...sign, lu_approuve: e.target.checked })} className="mt-0.5 accent-[#D4AF37]" />
              <span>{t('vendorOnboarding.luApprouve')}</span>
            </label>
            <button type="button" onClick={doSign} disabled={busy} data-testid="vendor-sign-btn"
              className="w-full py-3.5 rounded-xl inline-flex items-center justify-center gap-2 text-sm font-bold disabled:opacity-50"
              style={{ background: 'linear-gradient(135deg, #D9B35A 0%, #b8933e 100%)', color: '#1F0A33' }}>
              {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileSignature className="w-4 h-4" />} {t('vendorOnboarding.signBtn')}
            </button>
          </div>
        )}

        {step === 3 && (
          <div className="glass-panel rounded-[22px] p-10 text-center" data-testid="vendor-done-step">
            <CheckCircle2 className="w-14 h-14 mx-auto text-[#7BC94E] mb-4" />
            <h2 className="text-xl font-bold text-white mb-2">{t('vendorOnboarding.doneTitle')}</h2>
            <p className="text-white/70 text-sm flex items-center justify-center gap-2 mb-4">
              <Mail className="w-4 h-4 text-[#D9B35A]" /> {t('vendorOnboarding.doneEmail')}
            </p>
            <p className="text-white/50 text-xs mb-6">{t('vendorOnboarding.doneHint')}</p>
            <a href={`${API}/vendor-onboarding/${oid}/convention.pdf`} target="_blank" rel="noreferrer"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-bold"
              style={{ background: 'rgba(217,179,90,0.15)', color: '#E9CF8E', border: '1px solid rgba(217,179,90,0.4)' }}
              data-testid="vendor-download-convention">
              {t('vendorOnboarding.downloadBtn')}
            </a>
          </div>
        )}
      </div>
    </div>
  );
}
