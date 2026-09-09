import { useEffect, useState, useCallback } from 'react';
import { toast } from 'sonner';
import { Banknote, Package, Loader2, BadgeCheck, Download } from 'lucide-react';
import { getAuthHeaders, getSessionToken } from '../../services/http';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const eur = (v) => `${Number(v || 0).toLocaleString('fr-FR', { minimumFractionDigits: 2 })} €`;

// Espace investisseur : produits inscrits au financement par le superadmin — paiement Stripe direct
export const ProductFinancingBoard = () => {
  const [items, setItems] = useState(null);
  const [paying, setPaying] = useState(null);

  const load = useCallback(() => {
    if (!getSessionToken()) return;
    fetch(`${API_URL}/api/investor/financing-products`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => d && setItems(d.products || []))
      .catch(() => {});
  }, []);

  useEffect(() => {
    load();
    const params = new URLSearchParams(window.location.search);
    const sid = params.get('finprod_session_id');
    if (!sid || !getSessionToken()) return;
    window.history.replaceState({}, '', '/espace-investisseur');
    let attempts = 0;
    const poll = async () => {
      attempts += 1;
      try {
        const r = await fetch(`${API_URL}/api/investor/financing-products/checkout-status/${sid}`,
          { headers: getAuthHeaders(), credentials: 'include' });
        const d = await r.json();
        if (d.status === 'PAID') {
          toast.success(`Paiement confirmé — ${d.name} vendu et facturé par O'SCOP ✓`, {
            description: 'Votre facture acquittée vous a été envoyée par email.',
          });
          load();
          return;
        }
        if (attempts < 6) setTimeout(poll, 2000);
      } catch { /* ignore */ }
    };
    poll();
  }, [load]);

  const pay = async (fp) => {
    setPaying(fp.id);
    try {
      const res = await fetch(`${API_URL}/api/investor/financing-products/${fp.id}/pay`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      });
      const d = await res.json();
      if (!res.ok) throw new Error(d.detail || 'Erreur');
      window.location.href = d.checkout_url;
    } catch (e) { toast.error(e.message); setPaying(null); }
  };

  const downloadInvoice = async (fp) => {
    try {
      const r = await fetch(`${API_URL}/api/investor/financing-products/${fp.id}/invoice.pdf`,
        { headers: getAuthHeaders(), credentials: 'include' });
      if (!r.ok) throw new Error('Téléchargement impossible');
      const blob = await r.blob();
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `facture-${fp.reference}.pdf`;
      a.click();
      URL.revokeObjectURL(a.href);
      toast.success(`Facture ${fp.reference} téléchargée`);
    } catch (e) { toast.error(e.message); }
  };

  if (!items || items.length === 0) return null;
  const mine = items.filter((fp) => fp.status === 'PAID' && fp.is_mine);
  return (
    <div className="glass-panel-soft rounded-[22px] p-5 mb-8" data-testid="product-financing-board">
      <h2 className="text-lg font-bold flex items-center gap-2 mb-1">
        <Banknote className="w-5 h-5 text-[#D9B35A]" /> Produits à financer
      </h2>
      <p className="text-white/60 text-xs mb-4">
        Produits inscrits au financement par la Centrale O'SCOP — réglez directement par carte bancaire.
        Une fois payé, le produit est vendu et facturé par O'SCOP (facture acquittée par email).
      </p>
      <div className="grid sm:grid-cols-2 gap-3">
        {items.map((fp) => (
          <div key={fp.id} className="rounded-[14px] p-4 bg-white/[0.03] border border-white/[0.08]"
            data-testid={`fin-product-${fp.reference}`}>
            <div className="flex items-center justify-between gap-2 mb-1.5 flex-wrap">
              <span className="text-sm font-bold text-white">{fp.reference}</span>
              {fp.status === 'PAID' ? (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-[#8CC63E]/15 text-[#8CC63E] border border-[#8CC63E]/50"
                  data-testid={`fin-sold-badge-${fp.reference}`}>
                  <BadgeCheck className="w-3 h-3" /> Vendu et facturé par O'SCOP
                </span>
              ) : (
                <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-[#D9B35A]/15 text-[#E9CF8E] border border-[#D9B35A]/30">
                  {fp.status === 'PENDING_PAYMENT' ? 'Paiement en cours' : 'À financer'}
                </span>
              )}
            </div>
            <p className="text-white/85 text-sm flex items-center gap-1.5 mb-1">
              <Package className="w-3.5 h-3.5 text-[#D9B35A]" /> {fp.name}
            </p>
            <div className="text-[12px] text-white/65 space-y-0.5">
              <div>Prix de base HT : <b className="text-white/85">{eur(fp.base_price_eur)}</b></div>
              <div>Marge O'SCOP : <b className="text-white/85">{fp.margin_percent} %</b></div>
              <div>Total à régler : <b className="text-[#E9CF8E]" data-testid={`fin-total-${fp.reference}`}>{eur(fp.total_price_eur)}</b></div>
              {fp.status === 'PAID' && fp.is_mine && (
                <div className="text-[#8CC63E]">Payé par vous le {String(fp.paid_at || '').slice(0, 10)} ✓</div>
              )}
            </div>
            {fp.status === 'PAID' && fp.is_mine && (
              <button type="button" onClick={() => downloadInvoice(fp)}
                data-testid={`fin-invoice-btn-${fp.reference}`}
                className="mt-3 inline-flex items-center gap-2 px-3 py-2 rounded-[10px] text-xs font-bold text-[#E9CF8E] bg-[#D9B35A]/15 border border-[#D9B35A]/40 hover:bg-[#D9B35A]/25 transition-colors">
                <Download className="w-3.5 h-3.5" /> Re-télécharger ma facture
              </button>
            )}
            {fp.status !== 'PAID' && (
              <button type="button" onClick={() => pay(fp)} disabled={paying === fp.id}
                data-testid={`fin-pay-btn-${fp.reference}`}
                className="mt-3 inline-flex items-center gap-2 px-3 py-2 rounded-[10px] text-xs font-bold on-gold bg-[#D9B35A] hover:bg-[#F2D07A] disabled:opacity-60 transition-colors">
                {paying === fp.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Banknote className="w-3.5 h-3.5" />}
                Payer {eur(fp.total_price_eur)}
              </button>
            )}
          </div>
        ))}
      </div>
      {mine.length > 0 && (
        <div className="mt-4 pt-3 border-t border-white/10" data-testid="my-financed-products">
          <h3 className="text-sm font-bold text-white flex items-center gap-2 mb-2">
            <BadgeCheck className="w-4 h-4 text-[#8CC63E]" /> Mes produits financés ({mine.length})
            <span className="text-[11px] font-semibold text-[#8CC63E]">
              — total {eur(mine.reduce((s, fp) => s + Number(fp.total_price_eur || 0), 0))}
            </span>
          </h3>
          <div className="space-y-1.5">
            {mine.map((fp) => (
              <div key={fp.id} className="flex items-center gap-2 flex-wrap rounded-[10px] px-3 py-2 bg-white/[0.02] border border-white/[0.06] text-[12px] text-white/70"
                data-testid={`my-financed-${fp.reference}`}>
                <span className="font-semibold text-white">{fp.reference} · {fp.name}</span>
                <span className="text-white/45">payé le {String(fp.paid_at || '').slice(0, 10)}</span>
                <span className="font-mono text-[#8CC63E] font-bold">{eur(fp.total_price_eur)}</span>
                <button type="button" onClick={() => downloadInvoice(fp)}
                  data-testid={`my-financed-invoice-${fp.reference}`}
                  className="ml-auto inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-[8px] text-[11px] font-bold text-[#E9CF8E] bg-[#D9B35A]/15 border border-[#D9B35A]/40 hover:bg-[#D9B35A]/25 transition-colors">
                  <Download className="w-3 h-3" /> Facture PDF
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
