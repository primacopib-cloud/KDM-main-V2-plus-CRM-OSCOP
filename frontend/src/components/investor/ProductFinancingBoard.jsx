import { useEffect, useState, useCallback } from 'react';
import { toast } from 'sonner';
import { Banknote, Package, Loader2, BadgeCheck, Download, Truck } from 'lucide-react';
import { getAuthHeaders, getSessionToken } from '../../services/http';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const eur = (v) => `${Number(v || 0).toLocaleString('fr-FR', { minimumFractionDigits: 2 })} €`;
const frDate = (iso) => { try { return new Date(iso).toLocaleDateString('fr-FR'); } catch { return iso; } };
const TRACK_STEPS = [['CONFIRMEE', 'Confirmée'], ['PREPARATION', 'Préparation'], ['EXPEDITION', 'Expédiée'], ['TRANSIT', 'En transit'], ['LIVREE', 'Livrée']];

const TrackingStepper = ({ fp }) => {
  const idx = TRACK_STEPS.findIndex(([k]) => k === fp.tracking_status);
  return (
    <div className="mt-3" data-testid={`fin-tracking-${fp.reference}`}>
      <div className="text-[10px] uppercase tracking-wide text-white/45 mb-1.5">Suivi logistique</div>
      <div className="flex items-center">
        {TRACK_STEPS.map(([key, label], i) => (
          <div key={key} className="flex-1 flex flex-col items-center relative">
            {i > 0 && (
              <span className={`absolute top-[7px] right-1/2 w-full h-0.5 ${i <= idx ? 'bg-[#8CC63E]' : 'bg-white/15'}`} />
            )}
            <span className={`relative z-10 w-3.5 h-3.5 rounded-full border-2 ${
              i < idx ? 'bg-[#8CC63E] border-[#8CC63E]'
                : i === idx ? 'bg-[#8CC63E] border-[#8CC63E] ring-2 ring-[#8CC63E]/30'
                : 'bg-[#241243] border-white/25'}`} />
            <span className={`mt-1 text-[9px] text-center leading-tight ${i <= idx ? 'text-[#8CC63E] font-bold' : 'text-white/40'}`}>{label}</span>
          </div>
        ))}
      </div>
      {idx < 0 && <p className="text-[10px] text-white/35 m-0 mt-1">En attente de prise en charge par la Centrale.</p>}
      {fp.eta_delivery && (
        <p className="text-[10px] text-[#E9CF8E] font-semibold m-0 mt-1" data-testid={`fin-eta-${fp.reference}`}>
          📅 Livraison estimée : {frDate(fp.eta_delivery)}
        </p>
      )}
      {fp.delivery_proof && (
        <a href={fp.delivery_proof.startsWith('http') ? fp.delivery_proof : `${API_URL}${fp.delivery_proof}`}
          target="_blank" rel="noreferrer" data-testid={`fin-proof-link-${fp.reference}`}
          className="inline-flex items-center gap-1 mt-1 text-[10px] font-bold text-sky-300 hover:text-sky-200 underline underline-offset-2">
          📎 Voir la preuve de livraison
        </a>
      )}
      {fp.tracking_status === 'LIVREE' && <p className="text-[10px] text-[#8CC63E] font-bold m-0 mt-1" data-testid={`fin-delivered-${fp.reference}`}>🎉 Livraison effectuée</p>}
    </div>
  );
};

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
        <Banknote className="w-5 h-5 text-[#D9B35A]" /> Produits & logistique à financer
      </h2>
      <p className="text-white/60 text-xs mb-4">
        Produits et prestations logistiques inscrits au financement par la Centrale O'SCOP — réglez directement par carte bancaire.
        Une fois payé, le financement est vendu et facturé par O'SCOP (facture acquittée par email).
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
              {fp.kind === 'LOGISTIQUE'
                ? <Truck className="w-3.5 h-3.5 text-sky-300" />
                : <Package className="w-3.5 h-3.5 text-[#D9B35A]" />} {fp.name}
              {fp.kind === 'LOGISTIQUE' && (
                <span className="px-1.5 py-0.5 rounded-full text-[9px] font-bold uppercase text-sky-300 bg-sky-500/10 border border-sky-400/40"
                  data-testid={`fin-logistics-badge-${fp.reference}`}>Logistique</span>
              )}
            </p>
            <div className="text-[12px] text-white/65 space-y-0.5">
              <div>Prix de base HT : <b className="text-white/85">{eur(fp.base_price_eur)}</b></div>
              <div>Marge O'SCOP : <b className="text-white/85">{fp.margin_percent} %</b></div>
              <div>Total à régler : <b className="text-[#E9CF8E]" data-testid={`fin-total-${fp.reference}`}>{eur(fp.total_price_eur)}</b></div>
              {fp.status === 'PAID' && fp.is_mine && (
                <div className="text-[#8CC63E]">Payé par vous le {String(fp.paid_at || '').slice(0, 10)} ✓</div>
              )}
            </div>
            {fp.status === 'PAID' && fp.is_mine && <TrackingStepper fp={fp} />}
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
