import { useState } from 'react';
import { Handshake, Send, Loader2, CheckCircle2, Link2 } from 'lucide-react';
import { toast } from 'sonner';
import Header from '../components/Header';
import Footer from '../components/Footer';
import { apiCall } from '../services/http';

const PARTNER_TYPES = [
  { value: 'LOGISCOP', label: "Transporteur LOGI'SCOP" },
  { value: 'COOPER', label: 'COOPER (coopérateur opérationnel)' },
  { value: 'FOURNISSEUR', label: 'Fournisseur / Producteur' },
  { value: 'RELAIS', label: 'Relais LOLODRIVE' },
  { value: 'AUTRE', label: 'Autre partenariat' },
];

const TERRITORIES = ['Guadeloupe', 'Martinique', 'Guyane', 'La Réunion', 'Hexagone', 'Autre'];

export default function PartnershipPage() {
  const [form, setForm] = useState({
    structure_name: '', siret: '', partner_type: 'LOGISCOP', territory: 'Guadeloupe',
    contact_name: '', contact_email: '', contact_phone: '', message: '',
  });
  const [sending, setSending] = useState(false);
  const [reference, setReference] = useState(null);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSending(true);
    try {
      const res = await apiCall('/partnership/request', { method: 'POST', body: JSON.stringify(form) });
      setReference(res.reference);
      toast.success('Demande de partenariat envoyée !');
    } catch (err) {
      toast.error(err.message || "Erreur lors de l'envoi");
    } finally {
      setSending(false);
    }
  };

  const copyLink = () => {
    navigator.clipboard.writeText(window.location.href);
    toast.success('Lien copié — partagez-le sur objectifscopoutremer et kdmarche');
  };

  const inputCls = 'w-full h-11 px-4 rounded-xl bg-white/[0.04] border border-white/10 text-sm focus:outline-none focus:border-[#D9B35A]/60';

  return (
    <div className="min-h-screen" data-testid="partnership-page">
      <Header />
      <main className="pt-24 pb-16 max-w-[720px] mx-auto px-5">
        <div className="text-center mb-8">
          <div className="w-14 h-14 mx-auto mb-4 rounded-2xl flex items-center justify-center"
            style={{ background: 'rgba(217,179,90,0.14)', border: '1px solid rgba(217,179,90,0.45)' }}>
            <Handshake className="w-7 h-7 text-[#D9B35A]" />
          </div>
          <h1 className="font-display text-4xl sm:text-5xl lg:text-6xl tracking-tight mb-3">Devenir partenaire</h1>
          <p className="text-white/60 text-base">
            Rejoignez l'écosystème coopératif O'SCOP × KDMARCHÉ : transport LOGI'SCOP, COOPER'S, fournisseurs, relais.
          </p>
          <button onClick={copyLink} data-testid="partnership-share-btn"
            className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-medium border border-white/15 hover:border-[#D9B35A]/50 transition-colors">
            <Link2 className="w-3.5 h-3.5 text-[#D9B35A]" /> Copier le lien de partage
          </button>
        </div>

        {reference ? (
          <div className="glass-panel-soft rounded-[20px] p-8 text-center" data-testid="partnership-success-panel">
            <CheckCircle2 className="w-12 h-12 mx-auto mb-4 text-[#6FA82E]" />
            <h2 className="text-lg font-semibold mb-2">Demande envoyée !</h2>
            <p className="text-white/70 text-sm mb-1">Référence de votre demande :</p>
            <p className="text-[#D9B35A] font-bold text-xl mb-4" data-testid="partnership-reference">{reference}</p>
            <p className="text-white/60 text-sm">Notre équipe étudie votre demande et reviendra vers vous pour établir la convention de partenariat.</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="glass-panel-soft rounded-[20px] p-6 sm:p-8 space-y-5" data-testid="partnership-form">
            <div className="grid sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs uppercase tracking-wider text-white/60 mb-2">Nom de la structure *</label>
                <input required minLength={2} value={form.structure_name} onChange={set('structure_name')} className={inputCls} data-testid="partnership-structure-input" placeholder="SARL TransCaraïbes" />
              </div>
              <div>
                <label className="block text-xs uppercase tracking-wider text-white/60 mb-2">SIRET (optionnel)</label>
                <input value={form.siret} onChange={set('siret')} className={inputCls} data-testid="partnership-siret-input" placeholder="123 456 789 00012" />
              </div>
            </div>
            <div className="grid sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs uppercase tracking-wider text-white/60 mb-2">Type de partenariat *</label>
                <select value={form.partner_type} onChange={set('partner_type')} className={inputCls} data-testid="partnership-type-select">
                  {PARTNER_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs uppercase tracking-wider text-white/60 mb-2">Territoire *</label>
                <select value={form.territory} onChange={set('territory')} className={inputCls} data-testid="partnership-territory-select">
                  {TERRITORIES.map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
            </div>
            <div className="grid sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs uppercase tracking-wider text-white/60 mb-2">Contact *</label>
                <input required minLength={2} value={form.contact_name} onChange={set('contact_name')} className={inputCls} data-testid="partnership-contact-input" placeholder="Nom Prénom" />
              </div>
              <div>
                <label className="block text-xs uppercase tracking-wider text-white/60 mb-2">Email *</label>
                <input required type="email" value={form.contact_email} onChange={set('contact_email')} className={inputCls} data-testid="partnership-email-input" placeholder="vous@structure.fr" />
              </div>
              <div>
                <label className="block text-xs uppercase tracking-wider text-white/60 mb-2">Téléphone</label>
                <input value={form.contact_phone} onChange={set('contact_phone')} className={inputCls} data-testid="partnership-phone-input" placeholder="0690 XX XX XX" />
              </div>
            </div>
            <div>
              <label className="block text-xs uppercase tracking-wider text-white/60 mb-2">Votre projet de partenariat *</label>
              <textarea required minLength={10} rows={5} value={form.message} onChange={set('message')}
                className="w-full px-4 py-3 rounded-xl bg-white/[0.04] border border-white/10 text-sm focus:outline-none focus:border-[#D9B35A]/60 resize-y"
                data-testid="partnership-message-input" placeholder="Décrivez votre activité, vos capacités (flotte, zones desservies…) et le partenariat envisagé." />
            </div>
            <button type="submit" disabled={sending}
              className="btn-gold w-full h-12 rounded-xl inline-flex items-center justify-center gap-2 text-sm font-semibold disabled:opacity-60"
              data-testid="partnership-submit-btn">
              {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              {sending ? 'Envoi en cours…' : 'Envoyer ma demande de partenariat'}
            </button>
          </form>
        )}
      </main>
      <Footer />
    </div>
  );
}
