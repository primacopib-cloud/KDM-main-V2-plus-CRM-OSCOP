import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { MapPin, ArrowRight, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import NavBar from '../components/NavBar';
import i18n from '@/i18n';
import { CountrySelect, PhoneInput } from '../components/onboarding/CountryPhoneFields';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const inputCls = 'w-full h-11 rounded-xl px-3.5 text-sm text-white placeholder-white/35 bg-white/[0.05] border border-[#D9B35A]/25 focus:outline-none focus:ring-1 focus:ring-[#D9B35A]/60';

const Field = ({ label, children }) => (
  <div>
    <label className="block text-[11px] uppercase tracking-wider text-white/50 mb-1.5">{label}</label>
    {children}
  </div>
);

export default function PassRegistrationPage() {
  const navigate = useNavigate();
  const relay = (() => { try { return JSON.parse(localStorage.getItem('kdm_preselected_point') || 'null'); } catch { return null; } })();
  const [f, setF] = useState({ first_name: '', last_name: '', address: '', postal_code: '', city: '', phone: '', email: '', country: 'GP' });
  const [dial, setDial] = useState('+590|GP');
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const r = await fetch(`${API}/public/pass-registration`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...f, phone: `${dial.split('|')[0]} ${f.phone}`.trim(),
          phone_country: dial.split('|')[1], relay: relay || undefined,
        }),
      });
      if (!r.ok) throw new Error((await r.json()).detail || i18n.t('passReg.error'));
      toast.success(i18n.t('passReg.success'));
      navigate('/pass-lolodrive', { state: { firstName: f.first_name, relay } });
    } catch (err) { toast.error(String(err.message || err)); } finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen text-white" style={{ background: 'linear-gradient(180deg, #1F0A33 0%, #2A1045 100%)' }}>
      <NavBar />
      <main className="max-w-xl mx-auto px-4 pt-28 pb-20" data-testid="pass-registration-page">
        <p className="text-[11px] uppercase tracking-[0.2em] text-[#D9B35A] font-bold mb-2">PASS LOLODRIVE</p>
        <h1 className="text-4xl sm:text-5xl font-bold mb-3">{i18n.t('passReg.title')}</h1>
        <p className="text-sm text-white/60 mb-6">{i18n.t('passReg.subtitle')}</p>
        {relay && (
          <div className="flex items-center gap-2 rounded-xl px-3.5 py-2.5 mb-6 text-sm bg-white/[0.05] border border-[#D9B35A]/25" data-testid="pass-relay-preselected">
            <MapPin className="w-4 h-4 text-[#D9B35A]" />
            <span className="text-white/75">{i18n.t('passReg.relais_choisi')} <b className="text-[#E9CF8E]">{relay.name}</b>{relay.code ? ` (${relay.code})` : ''}</span>
          </div>
        )}
        <form onSubmit={submit} className="space-y-4">
          <div className="grid sm:grid-cols-2 gap-4">
            <Field label={i18n.t('passReg.prenom')}>
              <input required value={f.first_name} onChange={set('first_name')} className={inputCls} data-testid="pass-first-name" />
            </Field>
            <Field label={i18n.t('passReg.nom')}>
              <input required value={f.last_name} onChange={set('last_name')} className={inputCls} data-testid="pass-last-name" />
            </Field>
          </div>
          <Field label={i18n.t('passReg.adresse')}>
            <input required value={f.address} onChange={set('address')} className={inputCls} data-testid="pass-address" />
          </Field>
          <div className="grid sm:grid-cols-2 gap-4">
            <Field label={i18n.t('passReg.code_postal')}>
              <input required value={f.postal_code} onChange={set('postal_code')} className={inputCls} data-testid="pass-postal-code" />
            </Field>
            <Field label={i18n.t('passReg.ville')}>
              <input required value={f.city} onChange={set('city')} className={inputCls} data-testid="pass-city" />
            </Field>
          </div>
          <Field label={i18n.t('passReg.telephone')}>
            <PhoneInput dial={dial} number={f.phone} onDialChange={setDial}
              onNumberChange={(v) => setF({ ...f, phone: v })} testId="pass-phone" />
          </Field>
          <div className="grid sm:grid-cols-2 gap-4">
            <Field label={i18n.t('passReg.pays')}>
              <CountrySelect value={f.country} onChange={(v) => setF({ ...f, country: v })} testId="pass-country" />
            </Field>
            <Field label={i18n.t('passReg.email')}>
              <input required type="email" value={f.email} onChange={set('email')} className={inputCls} data-testid="pass-email" />
            </Field>
          </div>
          <button type="submit" disabled={busy} data-testid="pass-submit-btn"
            className="btn-gold w-full inline-flex items-center justify-center gap-2 rounded-[14px] py-3.5 text-sm font-semibold disabled:opacity-50">
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
            {i18n.t('passReg.obtenir_mon_pass')} <ArrowRight className="w-4 h-4" />
          </button>
        </form>
      </main>
    </div>
  );
}
