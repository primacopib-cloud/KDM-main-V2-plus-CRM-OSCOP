import { useState } from 'react';
import { Handshake, ChevronDown, Loader2, CheckCircle2 } from 'lucide-react';
import { toast } from 'sonner';
import { SearchableCountryDropdown } from '../onboarding/CountryPhoneFields';
import { COUNTRIES } from '../onboarding/countries';

const API = process.env.REACT_APP_BACKEND_URL;

// Pied de page d'accueil : présentation du rôle COOPER'S + formulaire dépliable d'inscription
export const CooperSignupAccordion = () => {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: '', email: '', phone: '', country: 'Guadeloupe', motivation: '' });
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const r = await fetch(`${API}/api/public/cooper-applications`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });
      if (!r.ok) throw new Error((await r.json()).detail || 'Erreur');
      setSent(true);
      toast.success('Candidature COOPER\'S envoyée — un email de confirmation vient de partir');
    } catch (err) { toast.error(err.message); } finally { setBusy(false); }
  };

  const inp = 'w-full h-10 px-3 rounded-lg bg-white/[0.05] border border-white/15 text-white text-sm placeholder:text-white/35 focus:outline-none focus:ring-1 focus:ring-[#D9B35A]/50';

  return (
    <section className="py-10 px-5" data-testid="cooper-signup-section">
      <div className="max-w-4xl mx-auto rounded-3xl border border-white/[0.08] overflow-hidden"
        style={{ background: 'radial-gradient(120% 140% at 50% -20%, rgba(217,179,90,0.08), rgba(20,8,38,0.5))' }}>
        <button type="button" onClick={() => setOpen(!open)} data-testid="cooper-accordion-toggle"
          className="w-full flex items-center justify-between gap-3 px-6 py-5 text-left hover:bg-white/[0.02] transition-colors">
          <span className="flex items-center gap-3">
            <span className="w-10 h-10 rounded-xl flex items-center justify-center bg-[#D9B35A]/15 border border-[#D9B35A]/30">
              <Handshake className="w-5 h-5 text-[#D9B35A]" />
            </span>
            <span>
              <span className="block text-base font-bold text-[#E9CF8E]">Devenir COOPER'S — rejoignez l'équipe coopérative</span>
              <span className="block text-xs text-white/50">Inscription en tant que COOPER'S · cliquez pour déplier</span>
            </span>
          </span>
          <ChevronDown className={`w-5 h-5 text-white/50 transition-transform ${open ? 'rotate-180' : ''}`} />
        </button>
        {open && (
          <div className="px-6 pb-6 border-t border-white/[0.06]" data-testid="cooper-accordion-content">
            <div className="grid md:grid-cols-2 gap-6 pt-5">
              <div className="text-sm text-white/70 space-y-2.5">
                <h4 className="text-sm font-bold text-white m-0">Le rôle du COOPER'S</h4>
                <p className="m-0">Le COOPER'S est un membre actif de l'équipe coopérative O'SCOP. Il participe au fonctionnement de la centrale au plus près du terrain :</p>
                <ul className="m-0 pl-4 space-y-1.5 list-disc marker:text-[#D9B35A]">
                  <li>Instruire les <b>besoins d'achat</b> qui lui sont assignés par la centrale</li>
                  <li>Qualifier les fournisseurs et suivre les <b>adhésions</b> en attente</li>
                  <li>Coordonner les transporteurs <b>LOGI'SCOP</b> sur son territoire</li>
                  <li>Animer la communauté d'acheteurs et de vendeurs de son pays</li>
                </ul>
                <p className="m-0 text-xs text-white/45">Après étude de votre candidature, la centrale ouvre votre espace COOPER'S et vous accompagne à la prise en main.</p>
              </div>
              {sent ? (
                <div className="flex flex-col items-center justify-center text-center py-8" data-testid="cooper-form-success">
                  <CheckCircle2 className="w-10 h-10 text-emerald-400 mb-3" />
                  <p className="text-emerald-300 font-semibold m-0">Candidature envoyée !</p>
                  <p className="text-white/60 text-sm m-0 mt-1">Vérifiez votre boîte mail — la Centrale O'SCOP vous recontacte rapidement.</p>
                </div>
              ) : (
                <form onSubmit={submit} className="space-y-2.5" data-testid="cooper-signup-form">
                  <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
                    placeholder="Nom complet *" data-testid="cooper-input-name" className={inp} />
                  <input required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })}
                    placeholder="Email *" data-testid="cooper-input-email" className={inp} />
                  <div className="grid grid-cols-2 gap-2.5">
                    <SearchableCountryDropdown
                      value={(COUNTRIES.find((c) => c.name === form.country) || {}).code || 'GP'}
                      display={form.country || 'Pays'} testId="cooper-input-country"
                      onSelect={(c) => setForm({ ...form, country: c.name })} />
                    <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })}
                      placeholder="Téléphone" data-testid="cooper-input-phone" className={inp} />
                  </div>
                  <textarea value={form.motivation} onChange={(e) => setForm({ ...form, motivation: e.target.value })}
                    placeholder="Votre motivation, votre territoire d'action… (optionnel)" rows={3}
                    data-testid="cooper-input-motivation"
                    className="w-full px-3 py-2 rounded-lg bg-white/[0.05] border border-white/15 text-white text-sm placeholder:text-white/35 focus:outline-none focus:ring-1 focus:ring-[#D9B35A]/50" />
                  <button type="submit" disabled={busy} data-testid="cooper-form-submit-btn"
                    className="w-full h-11 rounded-xl font-bold text-sm text-[#1F0A33] disabled:opacity-60"
                    style={{ background: 'linear-gradient(135deg, #D9B35A, #b8933e)' }}>
                    {busy ? <Loader2 className="w-4 h-4 animate-spin inline" /> : "Envoyer ma candidature COOPER'S"}
                  </button>
                </form>
              )}
            </div>
          </div>
        )}
      </div>
    </section>
  );
};
