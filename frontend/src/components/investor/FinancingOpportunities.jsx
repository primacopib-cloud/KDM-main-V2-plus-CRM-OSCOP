import { useEffect, useState } from 'react';
import { TrendingUp, Package, HandCoins, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { getAuthHeaders, getSessionToken } from '../../services/http';
import { ContextualMessageDialog } from '../ContextualMessageDialog';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const eur = (v) => `${Number(v || 0).toLocaleString('fr-FR')} €`;

const STATUS_FR = {
  DRAFT: 'En préparation', FUNDING: 'Recherche de financement', AUTHORIZED: 'Autorisée',
  SUPPLIER_ORDERED: 'Commande fournisseur', IN_TRANSIT: 'En transit', DELIVERED: 'Livrée',
};

export const FinancingOpportunities = () => {
  const [items, setItems] = useState([]);
  const [notice, setNotice] = useState('');
  const [sending, setSending] = useState(null);
  const [sent, setSent] = useState({});

  const expressInterest = async (op) => {
    if (!getSessionToken()) {
      toast.error('Connectez-vous avec votre compte investisseur pour envoyer votre demande');
      return;
    }
    setSending(op.id);
    try {
      const res = await fetch(`${API}/investor/financing-interest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ operation_id: op.id }),
      });
      const d = await res.json();
      if (!res.ok) throw new Error(d.detail || 'Erreur');
      setSent((s) => ({ ...s, [op.id]: true }));
      toast.success(d.already_sent ? 'Demande déjà transmise aux admins' : "Demande envoyée à l'équipe O'SCOP ✓");
    } catch (e) {
      toast.error(String(e.message || e));
    } finally {
      setSending(null);
    }
  };

  useEffect(() => {
    fetch(`${API}/public/financing-opportunities`)
      .then((r) => r.json())
      .then((d) => { setItems(d.opportunities || []); setNotice(d.notice || ''); })
      .catch(() => {});
  }, []);
  if (items.length === 0) return null;
  return (
    <div className="glass-panel-soft rounded-[22px] p-5 mb-8" data-testid="financing-opportunities">
      <h2 className="text-lg font-bold flex items-center gap-2 mb-1">
        <TrendingUp className="w-5 h-5 text-[#D9B35A]" /> Opérations à financer
      </h2>
      <p className="text-white/60 text-xs mb-4">{notice}</p>
      <div className="grid sm:grid-cols-2 gap-3">
        {items.map((op) => (
          <div key={op.id} className="rounded-[14px] p-4 bg-white/[0.03] border border-white/[0.08]"
            data-testid={`opportunity-${op.reference}`}>
            <div className="flex items-center justify-between gap-2 mb-1.5 flex-wrap">
              <span className="text-sm font-bold text-white">{op.reference}</span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-[#D9B35A]/15 text-[#E9CF8E] border border-[#D9B35A]/30">
                {STATUS_FR[op.status] || op.status}
              </span>
            </div>
            <p className="text-white/85 text-sm flex items-center gap-1.5 mb-1">
              <Package className="w-3.5 h-3.5 text-[#D9B35A]" /> {op.linked_product_name || 'Offre catalogue'}
            </p>
            <div className="text-[12px] text-white/65 space-y-0.5">
              {op.territory_id && <div>Territoire : <b className="text-white/85">{op.territory_id}</b></div>}
              <div>Achat fournisseur HT : <b className="text-white/85">{eur(op.purchase_amount_ex_vat)}</b></div>
              <div>Revente prévue HT : <b className="text-white/85">{eur(op.resale_amount_ex_vat)}</b></div>
            </div>
            <button type="button" onClick={() => expressInterest(op)}
              disabled={sending === op.id || sent[op.id]}
              data-testid={`interest-btn-${op.reference}`}
              className={`mt-3 mr-2 inline-flex items-center gap-2 px-3 py-2 rounded-[10px] text-xs font-bold transition-colors ${
                sent[op.id] ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-400/30 cursor-default'
                : 'on-gold bg-[#D9B35A] hover:bg-[#F2D07A]'
              }`}>
              {sending === op.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <HandCoins className="w-3.5 h-3.5" />}
              {sent[op.id] ? 'Demande transmise ✓' : 'Je souhaite financer'}
            </button>
            {getSessionToken() && <ContextualMessageDialog contextType="operation" contextRef={op.reference} />}
          </div>
        ))}
      </div>
    </div>
  );
};
