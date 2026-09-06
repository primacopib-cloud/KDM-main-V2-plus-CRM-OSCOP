import { useState } from 'react';
import { toast } from 'sonner';
import { X, Send } from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const TERRITORIES = ['Guadeloupe', 'Martinique', 'Guyane', 'La Réunion', 'Mayotte', 'Saint-Martin', 'Autre'];
const inputCls = 'h-10 px-3 rounded-xl bg-white/[0.06] border border-white/15 text-white text-sm w-full placeholder:text-white/35';

// Formulaire visiteur : dépôt d'un besoin d'achat complet (traité par le superadmin)
export const PurchaseNeedForm = ({ onClose }) => {
  const [f, setF] = useState({ company: '', contact_name: '', email: '', phone: '', territory: 'Guadeloupe', product: '', quantity: '', budget_eur: '', deadline: '', description: '' });
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [ref, setRef] = useState('');
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const res = await fetch(`${API_URL}/api/public/purchase-needs`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...f, budget_eur: f.budget_eur ? Number(f.budget_eur) : null, deadline: f.deadline || null, description: f.description || null }),
      });
      if (!res.ok) throw new Error((await res.json()).detail?.[0]?.msg || 'Envoi impossible — vérifiez les champs');
      const d = await res.json();
      setRef(d.reference || '');
      setSent(true);
    } catch (err) { toast.error(typeof err.message === 'string' ? err.message : 'Erreur'); }
    finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 z-[90] flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm" data-testid="purchase-need-modal">
      <div className="w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-3xl p-6 bg-[#241243] border border-[#D9B35A]/30">
        <div className="flex items-center gap-2 mb-1">
          <h3 className="text-lg font-bold text-[#E9CF8E] m-0">Déposer un besoin d'achat</h3>
          <button type="button" onClick={onClose} data-testid="purchase-need-close"
            className="ml-auto p-1.5 rounded-lg text-white/60 hover:bg-white/[0.08] transition-colors"><X className="w-4 h-4" /></button>
        </div>
        {sent ? (
          <div className="py-8 text-center" data-testid="purchase-need-success">
            <p className="text-[#8CC63E] font-bold text-base m-0">✅ Besoin d'achat envoyé !</p>
            {ref && <p className="text-white font-mono text-lg mt-2 mb-0" data-testid="need-tracking-ref">N° de suivi : {ref}</p>}
            <p className="text-white/60 text-sm mt-2">Un email de confirmation avec votre numéro de suivi vient de vous être envoyé. La Centrale O'SCOP vous recontacte après étude de votre demande.</p>
          </div>
        ) : (
          <form onSubmit={submit}>
            <p className="text-xs text-white/55 m-0 mb-4">Décrivez votre besoin produit : la Centrale l'étudie, l'assigne à un vendeur référencé ou le publie sur la CommunityPlace.</p>
            <div className="grid gap-2.5 sm:grid-cols-2">
              <input required value={f.company} onChange={set('company')} placeholder="Société / Raison sociale *" className={inputCls} data-testid="need-company" />
              <input required value={f.contact_name} onChange={set('contact_name')} placeholder="Nom du contact *" className={inputCls} data-testid="need-contact" />
              <input required type="email" value={f.email} onChange={set('email')} placeholder="Email *" className={inputCls} data-testid="need-email" />
              <input required value={f.phone} onChange={set('phone')} placeholder="Téléphone *" className={inputCls} data-testid="need-phone" />
              <select value={f.territory} onChange={set('territory')} className={`${inputCls} bg-[#2B1548]`} data-testid="need-territory">
                {TERRITORIES.map((t) => <option key={t}>{t}</option>)}
              </select>
              <input required value={f.product} onChange={set('product')} placeholder="Produit recherché *" className={inputCls} data-testid="need-product" />
              <input required value={f.quantity} onChange={set('quantity')} placeholder="Quantité (ex. 2 palettes, 500 unités) *" className={inputCls} data-testid="need-quantity" />
              <input type="number" min="0" value={f.budget_eur} onChange={set('budget_eur')} placeholder="Budget estimé € (optionnel)" className={inputCls} data-testid="need-budget" />
              <input type="date" value={f.deadline} onChange={set('deadline')} className={inputCls} data-testid="need-deadline" title="Date limite souhaitée" />
            </div>
            <textarea value={f.description} onChange={set('description')} rows={3} data-testid="need-description"
              placeholder="Précisions : marque, conditionnement, normes, livraison souhaitée…"
              className="mt-2.5 w-full px-3 py-2 rounded-xl bg-white/[0.06] border border-white/15 text-white text-sm placeholder:text-white/35" />
            <button type="submit" disabled={busy} data-testid="purchase-need-submit"
              className="mt-4 w-full h-11 rounded-xl font-bold text-sm text-[#1F0A33] disabled:opacity-60 transition-opacity"
              style={{ background: 'linear-gradient(135deg, #D9B35A 0%, #b8933e 100%)' }}>
              <Send className="w-4 h-4 inline mr-2" /> {busy ? 'Envoi…' : "Envoyer mon besoin d'achat"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
};
