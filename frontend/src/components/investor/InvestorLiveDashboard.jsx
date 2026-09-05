import { useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';
import { API, getAuthHeaders, getSessionToken } from '../../services/http';
import { Badge } from '../ui/badge';

const eur = (v) => `${Number(v || 0).toLocaleString('fr-FR', { minimumFractionDigits: 2 })} €`;

export const InvestorLiveDashboard = () => {
  const [d, setD] = useState(null);
  const [state, setState] = useState('loading');

  useEffect(() => {
    if (!getSessionToken()) { setState('anonymous'); return; }
    fetch(`${API}/investor/dashboard`, { headers: getAuthHeaders() })
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((data) => { setD(data); setState('ok'); })
      .catch(() => setState('anonymous'));
  }, []);

  if (state === 'anonymous') return null;
  if (state === 'loading') return <div className="py-6"><Loader2 className="w-5 h-5 animate-spin text-[#D9B35A]" /></div>;

  return (
    <div className="glass-panel-soft rounded-[22px] p-5 mb-8" data-testid="investor-live-dashboard">
      <h2 className="text-lg font-bold mb-3">Mon tableau de bord — {d.email}</h2>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        {[['Engagé', d.totals.committed], ['Décaissé', d.totals.disbursed],
          ['Remboursé', d.totals.repaid], ['Encours', d.totals.outstanding]].map(([k, v]) => (
          <div key={k} className="p-3 rounded-[14px] bg-white/5 text-center">
            <p className="text-[10px] text-white/50 uppercase tracking-wide">{k}</p>
            <p className="text-[#D9B35A] font-bold" data-testid={`investor-total-${k}`}>{eur(v)}</p>
          </div>
        ))}
      </div>
      <div className="grid md:grid-cols-2 gap-4">
        <div>
          <p className="text-xs font-semibold text-white/70 uppercase mb-1.5">Mes engagements (Bons d'Engagement)</p>
          {d.commitments.length === 0 && <p className="text-white/40 text-xs">Aucun engagement.</p>}
          {d.commitments.map((c, i) => (
            <div key={i} className="p-2 rounded bg-white/5 mb-1.5 text-[11px]">
              <div className="flex justify-between text-white/85">
                <span>{c.operation_reference} · {c.financing_tranche}</span>
                <span>{eur(c.approved_amount)}</span>
              </div>
              <div className="flex justify-between text-white/50">
                <span>{c.legal_instrument} · <Badge className="bg-white/10 text-white/60 border-0 text-[8px]">{c.operation_status}</Badge></span>
                <span>décaissé {eur(c.disbursed_amount)} · restant {eur(c.remaining_amount)}</span>
              </div>
            </div>
          ))}
          <p className="text-xs font-semibold text-white/70 uppercase mt-3 mb-1.5">Remboursements reçus</p>
          {d.repayments.length === 0 && <p className="text-white/40 text-xs">Aucun remboursement.</p>}
          {d.repayments.map((r, i) => (
            <p key={i} className="text-[11px] text-white/60">
              {r.created_at?.slice(0, 10)} — marchandises {eur(r.goods_principal)} · logistique {eur(r.logistics_principal)} · rémunération {eur(r.remuneration)}
            </p>
          ))}
        </div>
        <div>
          <p className="text-xs font-semibold text-white/70 uppercase mb-1.5">Compteur CREDI'SCOP-INVEST</p>
          {!d.service_credits.account ? <p className="text-white/40 text-xs">Aucun compteur d'unités de services.</p> : (
            <>
              <p className="text-sm text-[#D9B35A] font-bold" data-testid="investor-credits">
                {d.service_credits.account.available_units} u. disponibles · {d.service_credits.account.reserved_units} réservées · {d.service_credits.account.expired_units} expirées
              </p>
              {d.service_credits.ledger.map((l) => (
                <p key={l.id} className="text-[11px] text-white/55">
                  {l.created_at?.slice(0, 10)} — {l.entry_type} {l.units} u.{l.service_label ? ` · ${l.service_label}` : ''}
                </p>
              ))}
            </>
          )}
          <p className="text-xs font-semibold text-white/70 uppercase mt-3 mb-1.5">Suivi logistique des opérations financées</p>
          {(!d.shipments || d.shipments.length === 0) && <p className="text-white/40 text-xs">Aucune expédition en cours.</p>}
          {(d.shipments || []).map((s) => (
            <div key={s.id} className="p-2 rounded bg-sky-500/10 border border-sky-400/15 mb-1.5 text-[11px]" data-testid={`investor-shipment-${s.shipment_number}`}>
              <div className="flex justify-between text-white/85">
                <span>{s.operation_reference} · {s.shipment_number}</span>
                <Badge className="bg-sky-500/20 text-sky-300 border-0 text-[8px]">{s.status}</Badge>
              </div>
              <p className="text-white/50">{s.origin} → {s.destination} · {s.transport_mode}</p>
              {s.milestones.map((m, i) => (
                <p key={i} className="text-white/45">• {m.milestone} — {m.created_at?.slice(0, 16).replace('T', ' ')}</p>
              ))}
            </div>
          ))}
          <p className="text-amber-200/80 text-[10px] mt-3 p-2 rounded bg-amber-500/10 border border-amber-400/20">{d.disclaimer}</p>
        </div>
      </div>
    </div>
  );
};
