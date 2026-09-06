import { useState, useEffect } from 'react';
import { Landmark, Loader2, CheckCircle2 } from 'lucide-react';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const COUNTRIES = [
  { code: 'FR', name: 'France', prefix: '+33' },
  { code: 'GP', name: 'Guadeloupe', prefix: '+590' },
  { code: 'MQ', name: 'Martinique', prefix: '+596' },
  { code: 'GF', name: 'Guyane', prefix: '+594' },
  { code: 'RE', name: 'La Réunion', prefix: '+262' },
  { code: 'BE', name: 'Belgique', prefix: '+32' },
  { code: 'CH', name: 'Suisse', prefix: '+41' },
  { code: 'LU', name: 'Luxembourg', prefix: '+352' },
  { code: 'CA', name: 'Canada', prefix: '+1' },
  { code: 'US', name: 'États-Unis', prefix: '+1' },
];
// Image de drapeau (les emoji drapeaux ne s'affichent pas sous Windows)
const Flag = ({ code }) => (
  <img src={`https://flagcdn.com/w40/${code.toLowerCase()}.png`} alt={code} width={22} height={15}
    className="absolute left-3 top-1/2 -translate-y-1/2 rounded-[2px] pointer-events-none shadow-sm"
    data-testid={`flag-img-${code}`} />
);
const RIGHTS = ['Data room', 'Qualification fournisseur', 'Analyse économique', 'Analyse logistique', "Bon d'Engagement", 'Workflow de paiement', 'Reporting', 'Clôture'];
const fmtEur = (n) => n.toLocaleString('fr-FR') + ' €';

export const InvestorApplyForm = () => {
  const [plans, setPlans] = useState([]);
  const [form, setForm] = useState({ legal_name: '', country: 'FR', phone_prefix: '+33', phone: '', siren: '', email: '', plan_id: '' });
  const [prefixCountry, setPrefixCountry] = useState('FR');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetch(`${API_URL}/api/investor-plans`).then((r) => r.json())
      .then((d) => setPlans(d.plans || [])).catch(() => {});
  }, []);

  const submit = async (e) => {
    e.preventDefault();
    if (!form.plan_id) { toast.error('Choisissez un plan d\'abonnement'); return; }
    setBusy(true);
    try {
      const res = await fetch(`${API_URL}/api/investor-plans/apply`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(form),
      });
      const d = await res.json();
      if (!res.ok) throw new Error(d.detail || 'Erreur');
      window.location.href = d.checkout_url;
    } catch (err) {
      toast.error(err.message);
      setBusy(false);
    }
  };

  const inputCls = 'h-10 px-3 rounded-xl bg-white/[0.06] border border-white/15 text-white text-sm placeholder:text-white/35 w-full';
  return (
    <form onSubmit={submit} id="financer" className="rounded-[22px] p-6 mb-6" data-testid="investor-apply-form"
      style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(217,179,90,0.3)' }}>
      <h2 className="text-2xl font-bold text-[#D9B35A] flex items-center gap-2 m-0 mb-1">
        <Landmark className="w-5 h-5" /> FINANCER
      </h2>
      <p className="text-white/60 text-sm mt-1 mb-4">Ouvrez votre compte investisseur : adhésion mensuelle réglée par carte bancaire, espace créé immédiatement avec identifiant provisoire.</p>

      <div className="grid sm:grid-cols-2 gap-3 mb-4">
        <input required value={form.legal_name} onChange={(e) => setForm({ ...form, legal_name: e.target.value })}
          placeholder="Raison sociale" data-testid="invest-legal-name" className={inputCls} />
        <div className="relative">
          <Flag code={form.country} />
          <select value={form.country} data-testid="invest-country"
            onChange={(e) => { const c = COUNTRIES.find((x) => x.code === e.target.value); setForm({ ...form, country: c.code, phone_prefix: c.prefix }); setPrefixCountry(c.code); }}
            className={`${inputCls} bg-[#2B1548] pl-10`}>
            {COUNTRIES.map((c) => <option key={c.code} value={c.code}>{c.name}</option>)}
          </select>
        </div>
        <div className="flex gap-2">
          <div className="relative w-32 shrink-0">
            <Flag code={prefixCountry} />
            <select value={prefixCountry} data-testid="invest-phone-prefix"
              onChange={(e) => { const c = COUNTRIES.find((x) => x.code === e.target.value); setPrefixCountry(c.code); setForm({ ...form, phone_prefix: c.prefix }); }}
              className="h-10 pl-10 pr-1 rounded-xl bg-[#2B1548] border border-white/15 text-white text-sm w-full">
              {COUNTRIES.map((c) => <option key={c.code} value={c.code}>{c.prefix}</option>)}
            </select>
          </div>
          <input required value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })}
            placeholder="Téléphone" data-testid="invest-phone" className={inputCls} />
        </div>
        <input required value={form.siren} onChange={(e) => setForm({ ...form, siren: e.target.value })}
          placeholder="N° Immatriculation / SIREN" data-testid="invest-siren" className={inputCls} />
        <input required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })}
          placeholder="Adresse email" data-testid="invest-email" className={`${inputCls} sm:col-span-2`} />
      </div>

      <div className="grid sm:grid-cols-3 gap-3 mb-4">
        {plans.map((p) => (
          <button type="button" key={p.id} onClick={() => setForm({ ...form, plan_id: p.id })}
            data-testid={`invest-plan-${p.code}`}
            className={`text-left rounded-2xl p-4 border transition-colors ${form.plan_id === p.id ? 'border-[#D9B35A] bg-[#D9B35A]/10' : 'border-white/10 bg-white/[0.03] hover:border-[#D9B35A]/40'}`}>
            <p className="text-[#D9B35A] font-bold text-sm m-0">{p.name}</p>
            <p className="text-white text-lg font-bold m-0">{fmtEur(p.price_eur)} <span className="text-white/40 text-xs font-normal">/ mois</span></p>
            <p className="text-[11px] text-[#8CC63E] m-0 mt-1">CREDI'SCOP-INVEST : {p.monthly_invest_uc.toLocaleString('fr-FR')} uc de financement / mois</p>
            <p className="text-[11px] text-white/55 m-0 mt-1.5">{p.description}</p>
            {form.plan_id === p.id && <CheckCircle2 className="w-4 h-4 text-[#D9B35A] mt-2" />}
          </button>
        ))}
      </div>

      <div className="rounded-xl p-4 mb-4 bg-white/[0.03] border border-white/10" data-testid="crediscop-invest-explainer">
        <p className="text-sm font-semibold text-[#E9CF8E] m-0 mb-1.5">Qu'est-ce que le Compteur d'unités de services CREDI'SCOP-INVEST ?</p>
        <p className="text-[12.5px] text-white/70 m-0 mb-2">
          C'est un compteur fermé d'unités de services internes coopératifs, sans valeur monétaire, non convertible et non transférable.
          Il n'est jamais un moyen de paiement des produits, de la logistique ou des fournisseurs. Il ouvre droit à :
        </p>
        <div className="flex flex-wrap gap-1.5">
          {RIGHTS.map((r) => <span key={r} className="px-2 py-0.5 rounded-full bg-white/[0.05] border border-white/10 text-white/75 text-[11px]">{r}</span>)}
        </div>
        <p className="text-[12px] text-[#D9B35A] mt-3 mb-0 font-semibold">
          Chaque investissement réel fait l'objet d'un Bon d'Engagement et d'un paiement distinct en monnaie ayant cours légal.
        </p>
      </div>

      <button type="submit" disabled={busy} data-testid="invest-submit"
        className="force-white inline-flex items-center gap-2 rounded-[14px] px-5 py-3 text-sm font-bold text-black bg-[#D9B35A] hover:bg-[#c9a34a] transition-colors disabled:opacity-50">
        {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
        Adhérer et payer par carte
      </button>
    </form>
  );
};
