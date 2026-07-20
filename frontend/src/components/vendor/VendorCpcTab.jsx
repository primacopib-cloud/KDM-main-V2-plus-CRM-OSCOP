import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Ticket, Download, RefreshCw, ShoppingCart, Lock, FileText } from 'lucide-react';
import { toast } from 'sonner';
import { CpcSubscriptionPanel } from './CpcSubscriptionPanel';
import { CpcRechargePanel } from './CpcRechargePanel';

const API = process.env.REACT_APP_BACKEND_URL;
const eur = (c) => `${((c || 0) / 100).toFixed(2).replace('.', ',')} €`;
const panel = 'bg-white/[0.04] border border-white/[0.08] rounded-2xl';
const TYPE_LABELS = {
  PACK_PURCHASE: 'Achat de pack', PROMO_GRANT: 'Attribution promo/solidaire',
  CONSULTATION_ENTRY: 'Inscription consultation', REPORT_PURCHASE: "Rapport d'analyse / benchmark",
  REFUND_CANCELLATION: 'Recrédit (annulation)', REFUND_INCIDENT: 'Recrédit (incident)',
  EXPIRY: 'Expiration', ADMIN_CORRECTION: 'Correction administrative', STRIPE_REVERSAL: 'Annulation Stripe',
  SUBSCRIPTION_GRANT: 'Crédits inclus (abonnement)',
};

export const VendorCpcTab = () => {
  const [me, setMe] = useState(null);
  const [packs, setPacks] = useState([]);
  const [ledger, setLedger] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [pending, setPending] = useState(false);
  const [params, setParams] = useSearchParams();

  const load = useCallback(() => {
    fetch(`${API}/api/cpc/me`, { credentials: 'include' }).then((r) => r.json()).then(setMe).catch(() => {});
    fetch(`${API}/api/cpc/packs`, { credentials: 'include' }).then((r) => r.json()).then((d) => setPacks(d.items || [])).catch(() => {});
    fetch(`${API}/api/cpc/me/ledger`, { credentials: 'include' }).then((r) => r.json()).then((d) => setLedger(d.items || [])).catch(() => {});
    fetch(`${API}/api/cpc/me/invoices`, { credentials: 'include' }).then((r) => r.json()).then((d) => setInvoices(d.items || [])).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const sid = params.get('cpc_session');
    if (!sid) return;
    setPending(true);
    let tries = 0;
    const poll = setInterval(async () => {
      tries += 1;
      try {
        const r = await fetch(`${API}/api/cpc/purchase-status/${sid}`, { credentials: 'include' });
        const d = await r.json();
        if (d.status === 'SETTLED') {
          clearInterval(poll);
          setPending(false);
          toast.success(`${d.credits} CREDI'SCOP crédités — solde : ${d.balance}`);
          params.delete('cpc_session'); setParams(params, { replace: true });
          load();
        } else if (tries > 30) {
          clearInterval(poll);
          setPending(false);
          toast.info('Paiement en cours de confirmation — vos crédits seront ajoutés dès validation par Stripe.');
        }
      } catch { /* retry */ }
    }, 2000);
    return () => clearInterval(poll);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const buy = async (pack) => {
    const r = await fetch(`${API}/api/cpc/checkout`, {
      method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pack_id: pack.id, origin_url: window.location.origin }),
    });
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    window.location.href = d.checkout_url;
  };

  const downloadInvoice = async (number) => {
    const r = await fetch(`${API}/api/cpc/me/invoices/${number}/pdf`, { credentials: 'include' });
    if (!r.ok) return toast.error('Téléchargement impossible');
    const url = URL.createObjectURL(await r.blob());
    const a = document.createElement('a');
    a.href = url; a.download = `${number}.pdf`; a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6" data-testid="vendor-cpc-tab">
      <div className={`${panel} p-5 flex flex-wrap items-center gap-4`}>
        <div className="w-12 h-12 rounded-xl bg-[#D9B35A]/15 flex items-center justify-center">
          <Ticket className="w-6 h-6 text-[#D9B35A]" />
        </div>
        <div className="flex-1 min-w-[220px]">
          <p className="text-sm text-white/55">Mon CREDI'SCOP consultations</p>
          <p className="text-3xl font-bold text-white" data-testid="cpc-balance">{me?.balance ?? '—'} <span className="text-base font-semibold text-[#E9CF8E]">CREDI'SCOP</span></p>
          {me?.status === 'GELE' && (
            <p className="text-xs text-red-400 flex items-center gap-1 mt-1" data-testid="cpc-frozen-notice">
              <Lock className="w-3 h-3" /> Compte gelé — contactez l'administrateur
            </p>
          )}
        </div>
        {pending && (
          <div className="flex items-center gap-2 text-sm text-[#E9CF8E]" data-testid="cpc-pending-notice">
            <RefreshCw className="w-4 h-4 animate-spin" /> Confirmation du paiement en cours…
          </div>
        )}
        <p className="w-full text-[11px] text-white/40">
          Les unités CREDI'SCOP consultations (Crédits de Participation aux Consultations) sont des droits d'usage des
          services numériques O'SCOP — nominatifs, non transférables, non convertibles en euros, inutilisables pour
          payer des marchandises, la RCR ou FOGEDOM-SCIC.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {packs.map((p) => (
          <div key={p.id} className={`${panel} p-5 text-center space-y-2 hover:border-[#D9B35A]/40 transition-colors`} data-testid={`cpc-pack-${p.id}`}>
            <p className="text-sm font-semibold text-white/55">{p.label}</p>
            <p className="text-3xl font-bold text-[#E9CF8E]">{p.credits} <span className="text-xs text-white/40">CREDI'SCOP</span></p>
            <p className="text-lg font-bold text-white">{eur(p.price_ht_cents)} <span className="text-xs text-white/40">HT</span></p>
            <p className="text-[11px] text-white/40">Validité {p.validity_months} mois · TVA selon votre territoire</p>
            <button type="button" onClick={() => buy(p)} data-testid={`cpc-buy-${p.id}`}
              className="w-full py-2.5 rounded-xl text-xs font-bold inline-flex items-center justify-center gap-1.5 hover:brightness-110 transition-all"
              style={{ background: 'linear-gradient(135deg, #D9B35A, #b8933e)', color: '#1F0A33' }}>
              <ShoppingCart className="w-4 h-4" /> Acheter
            </button>
          </div>
        ))}
      </div>

      <a href={`${API}/api/cpc/reglement.pdf`} target="_blank" rel="noreferrer"
        className="inline-flex items-center gap-1.5 text-xs text-[#E9CF8E] hover:underline font-semibold" data-testid="cpc-reglement-link">
        <FileText className="w-3.5 h-3.5" /> Règlement autonome des Consultations Compétitives et des crédits CREDI'SCOP (V1.0 — PDF)
      </a>

      <CpcSubscriptionPanel onChanged={load} />

      <CpcRechargePanel packs={packs} />

      <div className={`${panel} p-5`}>
        <h3 className="font-semibold text-white mb-3">Historique des mouvements</h3>
        {!ledger.length && <p className="text-sm text-white/40">Aucun mouvement pour l'instant.</p>}
        <div className="space-y-1.5">
          {ledger.map((m) => (
            <div key={m.id} className="flex items-center gap-3 text-sm py-1.5 border-b border-white/5 last:border-0" data-testid={`cpc-ledger-${m.id}`}>
              <span className={`font-bold w-14 text-right ${m.qty > 0 ? 'text-emerald-400' : 'text-red-400'}`}>{m.qty > 0 ? '+' : ''}{m.qty}</span>
              <span className="flex-1 text-white/75">{TYPE_LABELS[m.type] || m.type}{m.reason ? ` — ${m.reason}` : ''}</span>
              <span className="text-xs text-white/40">solde {m.balance_after}</span>
              <span className="text-xs text-white/40">{String(m.created_at).slice(0, 16).replace('T', ' ')}</span>
            </div>
          ))}
        </div>
      </div>

      {invoices.length > 0 && (
        <div className={`${panel} p-5`}>
          <h3 className="font-semibold text-white mb-3">Factures de service O'SCOP (packs CREDI'SCOP)</h3>
          <div className="space-y-1.5">
            {invoices.map((inv) => (
              <div key={inv.number} className="flex items-center gap-3 text-sm py-1.5 border-b border-white/5 last:border-0">
                <span className="font-semibold text-white">{inv.number}</span>
                <span className="flex-1 text-white/55">{inv.label}</span>
                <span className="font-bold text-[#E9CF8E]">{eur(inv.ttc_cents)} TTC</span>
                <button type="button" onClick={() => downloadInvoice(inv.number)} data-testid={`cpc-invoice-dl-${inv.number}`}
                  className="p-1.5 rounded-lg bg-white/10 text-white/70 hover:text-white transition-colors">
                  <Download className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
