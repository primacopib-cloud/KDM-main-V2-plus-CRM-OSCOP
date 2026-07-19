import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Ticket, Download, RefreshCw, ShoppingCart, Lock, FileText } from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent } from '../ui/card';
import { Button } from '../ui/button';
import { CpcSubscriptionPanel } from './CpcSubscriptionPanel';
import { CpcRechargePanel } from './CpcRechargePanel';

const API = process.env.REACT_APP_BACKEND_URL;
const eur = (c) => `${((c || 0) / 100).toFixed(2).replace('.', ',')} €`;
const TYPE_LABELS = {
  PACK_PURCHASE: 'Achat de pack', PROMO_GRANT: 'Attribution promo/solidaire',
  CONSULTATION_ENTRY: 'Inscription consultation', REPORT_PURCHASE: "Rapport d'analyse",
  REFUND_CANCELLATION: 'Recrédit (annulation)', REFUND_INCIDENT: 'Recrédit (incident)',
  EXPIRY: 'Expiration', ADMIN_CORRECTION: 'Correction administrative', STRIPE_REVERSAL: 'Annulation Stripe',
  SUBSCRIPTION_GRANT: 'CPC inclus (abonnement)',
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
          toast.success(`${d.credits} CPC crédités — solde : ${d.balance}`);
          params.delete('cpc_session'); setParams(params, { replace: true });
          load();
        } else if (tries > 30) {
          clearInterval(poll);
          setPending(false);
          toast.info('Paiement en cours de confirmation — vos CPC seront crédités dès validation par Stripe.');
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
      <Card>
        <CardContent className="p-5 flex flex-wrap items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-purple-100 flex items-center justify-center">
            <Ticket className="w-6 h-6 text-purple-600" />
          </div>
          <div className="flex-1 min-w-[220px]">
            <p className="text-sm text-gray-500">Mes Crédits de Participation aux Consultations</p>
            <p className="text-3xl font-bold text-gray-900" data-testid="cpc-balance">{me?.balance ?? '—'} <span className="text-base font-semibold text-gray-400">CPC</span></p>
            {me?.status === 'GELE' && (
              <p className="text-xs text-red-600 flex items-center gap-1 mt-1" data-testid="cpc-frozen-notice">
                <Lock className="w-3 h-3" /> Compte gelé — contactez l'administrateur
              </p>
            )}
          </div>
          {pending && (
            <div className="flex items-center gap-2 text-sm text-amber-600" data-testid="cpc-pending-notice">
              <RefreshCw className="w-4 h-4 animate-spin" /> Confirmation du paiement en cours…
            </div>
          )}
          <p className="w-full text-[11px] text-gray-400">
            Les CPC sont des unités d'accès aux services numériques de consultation O'SCOP — nominatifs, non transférables,
            non convertibles en euros, inutilisables pour payer des marchandises, la RCR ou FOGEDOM-SCIC.
          </p>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {packs.map((p) => (
          <Card key={p.id} className="hover:shadow-md transition-shadow" data-testid={`cpc-pack-${p.id}`}>
            <CardContent className="p-5 text-center space-y-2">
              <p className="text-sm font-semibold text-gray-500">{p.label}</p>
              <p className="text-3xl font-bold text-purple-600">{p.credits} <span className="text-sm text-gray-400">CPC</span></p>
              <p className="text-lg font-bold text-gray-900">{eur(p.price_ht_cents)} <span className="text-xs text-gray-400">HT</span></p>
              <p className="text-[11px] text-gray-400">Validité {p.validity_months} mois · TVA selon votre territoire</p>
              <Button onClick={() => buy(p)} className="w-full bg-purple-600 hover:bg-purple-700" data-testid={`cpc-buy-${p.id}`}>
                <ShoppingCart className="w-4 h-4 mr-2" /> Acheter
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>

      <a href={`${API}/api/cpc/reglement.pdf`} target="_blank" rel="noreferrer"
        className="inline-flex items-center gap-1.5 text-xs text-purple-600 hover:underline font-semibold" data-testid="cpc-reglement-link">
        <FileText className="w-3.5 h-3.5" /> Règlement autonome des Consultations Compétitives et des CPC (V1.0 — PDF)
      </a>

      <CpcSubscriptionPanel onChanged={load} />

      <CpcRechargePanel packs={packs} />

      <Card>
        <CardContent className="p-5">
          <h3 className="font-semibold text-gray-900 mb-3">Historique des mouvements</h3>
          {!ledger.length && <p className="text-sm text-gray-400">Aucun mouvement pour l'instant.</p>}
          <div className="space-y-1.5">
            {ledger.map((m) => (
              <div key={m.id} className="flex items-center gap-3 text-sm py-1.5 border-b border-gray-100 last:border-0" data-testid={`cpc-ledger-${m.id}`}>
                <span className={`font-bold w-14 text-right ${m.qty > 0 ? 'text-emerald-600' : 'text-red-500'}`}>{m.qty > 0 ? '+' : ''}{m.qty}</span>
                <span className="flex-1 text-gray-700">{TYPE_LABELS[m.type] || m.type}{m.reason ? ` — ${m.reason}` : ''}</span>
                <span className="text-xs text-gray-400">solde {m.balance_after}</span>
                <span className="text-xs text-gray-400">{String(m.created_at).slice(0, 16).replace('T', ' ')}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {invoices.length > 0 && (
        <Card>
          <CardContent className="p-5">
            <h3 className="font-semibold text-gray-900 mb-3">Factures de service O'SCOP (packs CPC)</h3>
            <div className="space-y-1.5">
              {invoices.map((inv) => (
                <div key={inv.number} className="flex items-center gap-3 text-sm py-1.5 border-b border-gray-100 last:border-0">
                  <span className="font-semibold text-gray-900">{inv.number}</span>
                  <span className="flex-1 text-gray-500">{inv.label}</span>
                  <span className="font-bold">{eur(inv.ttc_cents)} TTC</span>
                  <Button variant="outline" size="sm" onClick={() => downloadInvoice(inv.number)} data-testid={`cpc-invoice-dl-${inv.number}`}>
                    <Download className="w-3.5 h-3.5" />
                  </Button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};
