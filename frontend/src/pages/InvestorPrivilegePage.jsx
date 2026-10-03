import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Crown, TrendingUp, Ship, ShieldCheck, Landmark, ArrowRight, Coins, RefreshCcw, PiggyBank, Scale, FileSignature, CreditCard, Building2, CheckCircle2, X } from 'lucide-react';
import { toast } from 'sonner';
import { apiCall, getSessionToken } from '../services/http';
import { HeaderBackButton } from '../components/HeaderBackButton';
import { BackToShowcase } from '../components/BackToShowcase';
import { Reveal } from '../components/Reveal';
import i18n from '@/i18n';
import INV_T from '../i18n/invPrivPage.json';

const L = (i18n.language || 'fr').split('-')[0];
const T = INV_T[L] || INV_T.fr;

const fmtEur = (n) => `${Number(n).toLocaleString('fr-FR')} €`;

const TIER_STYLE = {
  BRONZE: { ring: 'border-[#b08d57]/50', chip: 'from-[#b08d57] to-[#8a6a3b]', glow: 'rgba(176,141,87,0.15)' },
  ARGENT: { ring: 'border-slate-300/50', chip: 'from-slate-300 to-slate-500', glow: 'rgba(203,213,225,0.12)' },
  OR: { ring: 'border-[#F2D07A]/60', chip: 'from-[#F2D07A] to-[#D9B35A]', glow: 'rgba(217,179,90,0.2)' },
};

const CYCLE = [
  [T.cyc1_t, T.cyc1_d],
  [T.cyc2_t, T.cyc2_d],
  [T.cyc3_t, T.cyc3_d],
  [T.cyc4_t, T.cyc4_d],
];

const GARANTIES = [
  [ShieldCheck, T.g1_t, T.g1_d],
  [RefreshCcw, T.g2_t, T.g2_d],
  [Scale, T.g3_t, T.g3_d],
];

const ARGUMENTS = [
  [PiggyBank, T.a1_t, T.a1_d],
  [ShieldCheck, T.a2_t, T.a2_d],
  [TrendingUp, T.a3_t, T.a3_d],
];

// Formulaire de souscription : signature convention puis choix du paiement
const SubscribeDialog = ({ pack, convention, onClose }) => {
  const navigate = useNavigate();
  const isLogged = Boolean(getSessionToken());
  const [signer, setSigner] = useState('');
  const [company, setCompany] = useState('');
  const [siret, setSiret] = useState('');
  const [accept, setAccept] = useState(false);
  const [method, setMethod] = useState('STRIPE');
  const [busy, setBusy] = useState(false);
  const [transferInfo, setTransferInfo] = useState(null);

  const submit = async () => {
    if (!accept || !signer.trim() || !company.trim()) {
      toast.error('Complétez la signature : nom, société et acceptation de la convention');
      return;
    }
    setBusy(true);
    try {
      const r = await apiCall('/investor/privilege/subscribe', {
        method: 'POST',
        body: JSON.stringify({
          pack_id: pack.id, payment_method: method, signer_name: signer,
          company_name: company, siret, accept, origin_url: window.location.origin,
        }),
      });
      if (r.checkout_url) { window.location.href = r.checkout_url; return; }
      setTransferInfo(r);
    } catch (e) { toast.error(e.message); }
    setBusy(false);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4"
      data-testid="privilege-subscribe-dialog">
      <div className="w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl border border-[#D9B35A]/40 bg-[#1E0C34] p-6">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-[10px] font-black uppercase tracking-[0.18em] text-[#D9B35A]">Souscription — {pack.name}</p>
            <p className="text-lg font-black mt-1">{fmtEur(pack.amount_eur)} → <span className="text-[#F2D07A]">{fmtEur(pack.credits_eur)} de crédits (+{pack.bonus_pct} %)</span></p>
          </div>
          <button onClick={onClose} data-testid="privilege-dialog-close"
            className="p-1.5 rounded-full text-white/50 hover:text-white hover:bg-white/10 transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>
        {!isLogged ? (
          <div className="mt-6 text-center">
            <p className="text-sm text-white/70">Connectez-vous ou créez votre compte pour signer la convention d'investissement.</p>
            <button onClick={() => navigate('/connexion')} data-testid="privilege-login-btn"
              className="mt-4 inline-flex items-center gap-2 px-6 h-11 rounded-full bg-[#D9B35A] text-black text-sm font-bold hover:bg-[#E9CF8E] transition-colors on-gold">
              Se connecter <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        ) : transferInfo ? (
          <div className="mt-6 rounded-xl border border-emerald-400/40 bg-emerald-500/10 p-5" data-testid="privilege-transfer-info">
            <p className="text-sm font-bold text-emerald-300 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4" /> Convention signée — référence {transferInfo.reference}
            </p>
            <p className="text-xs text-white/70 mt-2 leading-relaxed">{transferInfo.instructions}</p>
            <Link to="/espace-investisseur" data-testid="privilege-goto-space"
              className="inline-flex items-center gap-2 mt-4 px-5 h-10 rounded-full border border-white/25 text-xs font-bold hover:bg-white/10 transition-colors">
              Accéder à mon espace investisseur <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        ) : (
          <>
            <div className="mt-5 rounded-xl border border-white/10 bg-white/[0.03] p-4 max-h-56 overflow-y-auto"
              data-testid="privilege-convention-text">
              <p className="text-[11px] font-black text-[#E9CF8E] uppercase tracking-wide flex items-center gap-1.5">
                <FileSignature className="w-3.5 h-3.5" /> Convention de préfinancement logistique — v{convention.version}
              </p>
              <p className="text-[11px] text-white/60 mt-2">{convention.parties}</p>
              {convention.articles.map((a) => (
                <div key={a.title} className="mt-3">
                  <p className="text-[11px] font-bold text-white/80">{a.title}</p>
                  <p className="text-[11px] text-white/55 leading-relaxed">{a.text}</p>
                </div>
              ))}
            </div>
            <div className="grid sm:grid-cols-2 gap-3 mt-4">
              <input value={signer} onChange={(e) => setSigner(e.target.value)} placeholder="Nom du signataire *"
                data-testid="privilege-signer-input"
                className="h-10 px-3 rounded-lg bg-white/[0.06] border border-white/15 text-sm placeholder:text-white/35 focus:border-[#D9B35A]/60 outline-none" />
              <input value={company} onChange={(e) => setCompany(e.target.value)} placeholder="Raison sociale *"
                data-testid="privilege-company-input"
                className="h-10 px-3 rounded-lg bg-white/[0.06] border border-white/15 text-sm placeholder:text-white/35 focus:border-[#D9B35A]/60 outline-none" />
              <input value={siret} onChange={(e) => setSiret(e.target.value)} placeholder="SIREN / SIRET"
                data-testid="privilege-siret-input"
                className="h-10 px-3 rounded-lg bg-white/[0.06] border border-white/15 text-sm placeholder:text-white/35 focus:border-[#D9B35A]/60 outline-none sm:col-span-2" />
            </div>
            <label className="flex items-start gap-2.5 mt-4 cursor-pointer" data-testid="privilege-accept-label">
              <input type="checkbox" checked={accept} onChange={(e) => setAccept(e.target.checked)}
                data-testid="privilege-accept-checkbox" className="mt-0.5 accent-[#D9B35A]" />
              <span className="text-[11px] text-white/65 leading-relaxed">
                Je reconnais avoir lu la convention (articles 1 à 7, incluant force majeure Outre-mer et retards
                maritimes) et je la signe électroniquement au nom de ma structure.
              </span>
            </label>
            <div className="mt-5">
              <p className="text-[11px] font-bold text-white/60 uppercase tracking-wide mb-2">Mode de versement</p>
              <div className="grid sm:grid-cols-2 gap-3">
                {[['STRIPE', CreditCard, 'Carte bancaire (Stripe)', 'Activation immédiate après paiement sécurisé'],
                  ['TRANSFER', Landmark, 'Virement bancaire', 'Compte séquestre SCIC — activation par la direction financière']].map(([m, Icon, label, sub]) => (
                  <button key={m} type="button" onClick={() => setMethod(m)} data-testid={`privilege-method-${m.toLowerCase()}`}
                    className={`text-left rounded-xl border p-3.5 transition-colors ${
                      method === m ? 'border-[#D9B35A] bg-[#D9B35A]/10' : 'border-white/15 hover:border-white/35'}`}>
                    <Icon className={`w-4 h-4 ${method === m ? 'text-[#F2D07A]' : 'text-white/50'}`} />
                    <p className="text-xs font-bold mt-1.5">{label}</p>
                    <p className="text-[10px] text-white/45 mt-0.5">{sub}</p>
                  </button>
                ))}
              </div>
            </div>
            <button onClick={submit} disabled={busy} data-testid="privilege-submit-btn"
              className="w-full mt-5 inline-flex items-center justify-center gap-2 h-12 rounded-full bg-[#D9B35A] text-black text-sm font-black hover:bg-[#E9CF8E] disabled:opacity-50 transition-colors on-gold">
              {busy ? 'Traitement…' : `Signer et verser ${fmtEur(pack.amount_eur)}`} <ArrowRight className="w-4 h-4" />
            </button>
          </>
        )}
      </div>
    </div>
  );
};

export default function InvestorPrivilegePage() {
  const [data, setData] = useState(null);
  const [selected, setSelected] = useState(null);
  useEffect(() => { apiCall('/investor/privilege/packs').then(setData).catch(() => {}); }, []);
  if (!data) return <div className="min-h-screen bg-[#12081f]" />;

  return (
    <div className="min-h-screen text-white relative" data-testid="investor-privilege-page"
      style={{ background: 'linear-gradient(180deg, #12081f 0%, #2A1045 55%, #1a0b2c 100%)' }}>
      <div className="absolute top-0 left-1/3 w-[30rem] h-[30rem] rounded-full bg-[#D9B35A]/[0.06] blur-3xl pointer-events-none" />
      <div className="max-w-5xl mx-auto px-6 py-10 relative">
        <HeaderBackButton fallback="/" className="!px-3 !rounded-full border border-white/20 hover:border-white/40 mb-3" />
        <div className="mb-8"><BackToShowcase page="investors" /></div>
        <Reveal>
          <div className="flex items-center gap-2 text-[#D9B35A] text-xs font-bold uppercase tracking-[0.2em]">
            <Crown className="w-4 h-4" /> {T.kicker}
          </div>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black mt-4 leading-tight">
            {T.h1a}
            <span className="block text-[#F2D07A]">{T.h1b}</span>
          </h1>
          <p className="text-base text-white/65 mt-5 max-w-2xl">
            {T.intro}
          </p>
        </Reveal>

        <div className="grid lg:grid-cols-3 gap-4 mt-12" data-testid="privilege-packs">
          {data.packs.map((p, i) => {
            const st = TIER_STYLE[p.id];
            return (
              <Reveal key={p.id} delay={i * 100}>
                <div className={`group relative h-full rounded-2xl border ${st.ring} bg-white/[0.03] p-6 transition-[transform,background-color] duration-300 hover:-translate-y-2`}
                  style={{ boxShadow: `0 0 40px ${st.glow}` }} data-testid={`privilege-pack-${p.id}`}>
                  <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-wide bg-gradient-to-r ${st.chip} text-[#1E0C34]`}>
                    <Crown className="w-3 h-3" /> {p.tier}
                  </span>
                  <p className="text-sm font-bold mt-3">{p.name}</p>
                  <p className="text-3xl font-black mt-2 text-white">{fmtEur(p.amount_eur)}</p>
                  <p className="text-sm font-bold text-[#F2D07A] mt-1" data-testid={`privilege-pack-${p.id}-credits`}>
                    → {fmtEur(p.credits_eur)} de crédits <span className="text-emerald-300">(+{p.bonus_pct} %)</span>
                  </p>
                  <p className="text-[11px] text-white/50 mt-3 leading-relaxed"><b className="text-white/70">{T.target}</b> {p.cible}</p>
                  <p className="text-[11px] text-white/50 mt-1.5 leading-relaxed"><b className="text-white/70">{T.dest}</b> {p.destination}</p>
                  <ul className="mt-4 space-y-1.5">
                    {p.privileges.map((pr) => (
                      <li key={pr} className="flex items-start gap-1.5 text-[11px] text-white/65">
                        <CheckCircle2 className="w-3.5 h-3.5 text-[#D9B35A] shrink-0 mt-px" /> {pr}
                      </li>
                    ))}
                  </ul>
                  <button onClick={() => setSelected(p)} data-testid={`privilege-subscribe-${p.id}`}
                    className="w-full mt-5 inline-flex items-center justify-center gap-2 h-11 rounded-full bg-[#D9B35A] text-black text-sm font-bold hover:bg-[#E9CF8E] active:scale-95 transition-[background-color,transform] on-gold">
                    {T.subscribe} <ArrowRight className="w-4 h-4 transition-transform duration-300 group-hover:translate-x-1" />
                  </button>
                </div>
              </Reveal>
            );
          })}
        </div>

        <Reveal>
          <section className="mt-16" data-testid="privilege-cycle">
            <h2 className="text-base md:text-lg font-bold text-[#E9CF8E] flex items-center gap-2">
              <RefreshCcw className="w-4 h-4" /> {T.cycle_title}
            </h2>
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3 mt-5">
              {CYCLE.map(([t, d], i) => (
                <Reveal key={t} delay={i * 80}>
                  <div className="group h-full rounded-2xl border border-white/10 bg-white/[0.03] p-4 transition-[transform,border-color] duration-300 hover:-translate-y-1 hover:border-[#D9B35A]/50">
                    <p className="text-xs font-black text-[#F2D07A]">{t}</p>
                    <p className="text-[11px] text-white/60 mt-1.5 leading-relaxed">{d}</p>
                  </div>
                </Reveal>
              ))}
            </div>
            <div className="mt-4 rounded-2xl border border-[#D9B35A]/25 bg-[#D9B35A]/[0.05] p-4 text-center text-[11px] font-mono text-white/60 overflow-x-auto"
              data-testid="privilege-flow-diagram">
              [ Apport investisseur ] ─► [ Compte séquestre O'SCOP ] ─► [ Préfinancement fret LOGI'SCOP ]<br />
              [ Rendement en nature ] ◄─ [ Revente / rotation des stocks ] ◄─┘
            </div>
          </section>
        </Reveal>

        <Reveal>
          <section className="mt-14" data-testid="privilege-guarantees">
            <h2 className="text-base md:text-lg font-bold text-[#E9CF8E] flex items-center gap-2">
              <ShieldCheck className="w-4 h-4" /> {T.guar_title}
            </h2>
            <div className="grid sm:grid-cols-3 gap-4 mt-5">
              {GARANTIES.map(([Icon, t, d], i) => (
                <Reveal key={t} delay={i * 80}>
                  <div className="group h-full rounded-2xl border border-emerald-400/20 bg-emerald-500/[0.04] p-5 transition-[transform,border-color] duration-300 hover:-translate-y-1 hover:border-emerald-400/50">
                    <Icon className="w-5 h-5 text-emerald-300 transition-transform duration-300 group-hover:scale-110" />
                    <p className="text-sm font-bold mt-2">{t}</p>
                    <p className="text-[11px] text-white/60 mt-1 leading-relaxed">{d}</p>
                  </div>
                </Reveal>
              ))}
            </div>
          </section>
        </Reveal>

        <Reveal>
          <section className="mt-14" data-testid="privilege-arguments">
            <h2 className="text-base md:text-lg font-bold text-[#E9CF8E] flex items-center gap-2">
              <TrendingUp className="w-4 h-4" /> {T.args_title}
            </h2>
            <div className="grid sm:grid-cols-3 gap-4 mt-5">
              {ARGUMENTS.map(([Icon, t, d]) => (
                <div key={t} className="rounded-2xl border border-white/10 bg-white/[0.03] p-5 transition-colors duration-300 hover:bg-white/[0.06]">
                  <Icon className="w-5 h-5 text-[#D9B35A]" />
                  <p className="text-sm font-bold mt-2">{t}</p>
                  <p className="text-[11px] text-white/60 mt-1 leading-relaxed">{d}</p>
                </div>
              ))}
            </div>
          </section>
        </Reveal>

        <Reveal>
          <section className="mt-14 rounded-2xl border border-[#7BC94E]/30 bg-[#7BC94E]/[0.05] p-6" data-testid="privilege-pass-impact">
            <h2 className="text-base md:text-lg font-bold text-[#B9E89A] flex items-center gap-2">
              <Ship className="w-4 h-4" /> {T.pass_title}
            </h2>
            <div className="grid sm:grid-cols-3 gap-4 mt-4 text-[11px] text-white/65 leading-relaxed">
              <p>{T.p1}</p>
              <p>{T.p2}</p>
              <p>{T.p3}</p>
            </div>
          </section>
        </Reveal>

        <Reveal>
          <div className="mt-12 flex flex-wrap items-center gap-3">
            <Coins className="w-4 h-4 text-[#D9B35A]" />
            <p className="text-[11px] text-white/45 max-w-3xl leading-relaxed">
              {T.disclaimer}
            </p>
          </div>
        </Reveal>
      </div>
      {selected && <SubscribeDialog pack={selected} convention={data.convention} onClose={() => setSelected(null)} />}
    </div>
  );
}
