import { useEffect, useState } from 'react';
import { Loader2, PiggyBank } from 'lucide-react';
import { API, getAuthHeaders } from '../../services/http';

const eur = (c) => ((c || 0) / 100).toLocaleString('fr-FR', { minimumFractionDigits: 2 }) + ' €';
const fdate = (d) => (d ? new Date(d).toLocaleDateString('fr-FR') : '—');

export const AttestationRcrLedger = ({ attId }) => {
  const [ledger, setLedger] = useState(undefined);

  useEffect(() => {
    fetch(`${API}/attestations/${attId}/rcr-ledger`, { credentials: 'include', headers: getAuthHeaders() })
      .then((r) => (r.ok ? r.json() : null)).then(setLedger).catch(() => setLedger(null));
  }, [attId]);

  if (ledger === undefined) return <p className="text-[11px] text-white/40 py-2"><Loader2 size={11} className="inline animate-spin mr-1" /> Chargement du suivi RCR…</p>;
  if (!ledger) return <p className="text-[11px] text-red-400 py-2">Suivi RCR indisponible</p>;

  const pct = ledger.plafond_cible_cents > 0 ? Math.min(100, (ledger.solde_cents / ledger.plafond_cible_cents) * 100) : 0;

  return (
    <div className="mt-2 rounded-lg p-3 bg-white/[0.03] border border-white/[0.08]" data-testid={`rcr-ledger-${attId}`}>
      <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
        <span className="inline-flex items-center gap-1.5 text-[11px] font-bold text-[#E9CF8E]">
          <PiggyBank size={12} /> Solde RCR constitué : {eur(ledger.solde_cents)} / {eur(ledger.plafond_cible_cents)}
          {ledger.plafond_atteint && <span className="text-red-400"> · plafond atteint</span>}
        </span>
        <span className="text-[10px] text-white/50" data-testid={`rcr-reimbursement-${attId}`}>
          Remboursement prévu : <b className="text-white/80">{fdate(ledger.remboursement_prevu)}</b>
          {' '}(expiration + {ledger.reimbursement_days} j)
        </span>
      </div>
      <div className="h-1.5 rounded-full bg-white/[0.08] mb-2 overflow-hidden">
        <div className="h-full rounded-full" style={{ width: `${pct}%`, background: ledger.plafond_atteint ? '#F87171' : '#D9B35A' }} />
      </div>
      {ledger.fractions.length === 0 ? (
        <p className="text-[11px] text-white/45">Aucune facture éligible pour l'instant — les fractions RCR se constitueront au fil des commandes de ce produit.</p>
      ) : (
        <table className="w-full text-[11px]">
          <thead>
            <tr className="text-left text-white/40 border-b border-white/[0.08]">
              <th className="py-1 pr-2">Facture / commande</th><th className="py-1 pr-2">Date</th>
              <th className="py-1 pr-2">Base HT</th><th className="py-1 pr-2">Fraction RCR ({ledger.rcr_rate}%)</th>
              <th className="py-1">Cumul</th>
            </tr>
          </thead>
          <tbody>
            {ledger.fractions.map((f) => (
              <tr key={f.order_id} className="border-b border-white/[0.04] text-white/75" data-testid={`rcr-fraction-${f.order_id}`}>
                <td className="py-1 pr-2 font-semibold text-white/85">{f.order_ref}</td>
                <td className="py-1 pr-2">{fdate(f.date)}</td>
                <td className="py-1 pr-2">{eur(f.base_ht_cents)}</td>
                <td className="py-1 pr-2 text-[#E9CF8E]">{eur(f.fraction_cents)}{f.capped ? ' (plafonnée)' : ''}</td>
                <td className="py-1 font-bold">{eur(f.cumul_cents)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};
