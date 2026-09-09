import { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { BadgeCheck, Copy, Download, Eye, EyeOff, KeyRound } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const frDate = (iso) => { try { return new Date(iso).toLocaleDateString('fr-FR'); } catch { return iso || '—'; } };

export const ApiSubscriptionsPanel = () => {
  const [data, setData] = useState({ items: [], active_count: 0, total_eur: 0, annual_price_eur: 2500 });
  const [revealed, setRevealed] = useState({});

  const load = useCallback(() => {
    fetch(`${API}/admin/api-subscriptions`, { credentials: 'include' })
      .then((r) => r.json())
      .then((d) => setData(d))
      .catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const copyKey = (s) => { navigator.clipboard.writeText(s.api_key); toast.success('Clé API copiée'); };

  const downloadInvoice = async (s) => {
    const r = await fetch(`${API}/admin/api-subscriptions/${s.id}/invoice.pdf`, { credentials: 'include' });
    if (!r.ok) return toast.error('Facture indisponible');
    const blob = await r.blob();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `facture-${s.reference}.pdf`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  return (
    <div className="glass-panel-soft rounded-[18px] p-5" data-testid="api-subscriptions-panel">
      <h3 className="font-display text-lg text-white flex items-center gap-2 mb-1">
        <KeyRound size={16} style={{ color: '#D9B35A' }} /> Abonnements API annuels
        <span className="text-sm font-normal text-white/50">({data.items.length})</span>
      </h3>
      <p className="text-xs text-white/45 mb-4" data-testid="api-subs-summary">
        {data.active_count} abonnement(s) actif(s) · {Number(data.total_eur).toLocaleString('fr-FR')} € encaissés ·
        tarif annuel {Number(data.annual_price_eur).toLocaleString('fr-FR')} €
      </p>
      <div className="space-y-2">
        {data.items.map((s) => (
          <div key={s.id} className="p-3 rounded-xl bg-white/[0.04] border border-white/10" data-testid={`api-sub-row-${s.reference}`}>
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <span className="text-sm text-white font-medium">{s.reference}</span>
              {s.status === 'ACTIVE' ? (
                <span className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-bold">
                  <BadgeCheck size={11} /> ACTIF
                </span>
              ) : (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 font-bold">EN ATTENTE DE PAIEMENT</span>
              )}
              <span className="text-xs text-white/60">{s.email}{s.company ? ` · ${s.company}` : ''}</span>
              <span className="text-xs text-white/40 ml-auto">
                {Number(s.amount_eur).toLocaleString('fr-FR')} € · souscrit le {frDate(s.created_at)}
                {s.paid_at ? ` · payé le ${frDate(s.paid_at)}` : ''}
                {s.valid_until ? ` · valide jusqu'au ${frDate(s.valid_until)}` : ''}
              </span>
            </div>
            {s.api_key && (
              <div className="flex items-center gap-2 mt-2">
                <code className="text-[11px] text-[#B6E27A] bg-black/30 px-2 py-1 rounded-lg flex-1 break-all" data-testid={`api-sub-key-${s.reference}`}>
                  {revealed[s.id] ? s.api_key : `${s.api_key_prefix || ''}${'•'.repeat(20)}`}
                </code>
                <button onClick={() => setRevealed((r) => ({ ...r, [s.id]: !r[s.id] }))}
                  data-testid={`api-sub-key-reveal-${s.reference}`}
                  className="p-1.5 rounded-lg hover:bg-white/10 text-white/70" title={revealed[s.id] ? 'Masquer' : 'Révéler'}>
                  {revealed[s.id] ? <EyeOff size={13} /> : <Eye size={13} />}
                </button>
                <button onClick={() => copyKey(s)} className="p-1.5 rounded-lg hover:bg-white/10 text-white/70" title="Copier"
                  data-testid={`api-sub-key-copy-${s.reference}`}>
                  <Copy size={13} />
                </button>
                <button onClick={() => downloadInvoice(s)} data-testid={`api-sub-invoice-${s.reference}`}
                  className="p-1.5 rounded-lg hover:bg-white/10 text-[#D9B35A]" title="Facture acquittée PDF">
                  <Download size={13} />
                </button>
              </div>
            )}
          </div>
        ))}
        {!data.items.length && (
          <p className="text-sm text-white/40 py-4 text-center">Aucun abonnement API souscrit pour le moment.</p>
        )}
      </div>
    </div>
  );
};
