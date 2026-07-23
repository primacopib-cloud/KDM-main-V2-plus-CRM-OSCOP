import { useCallback, useEffect, useState } from 'react';
import { Landmark, ChevronDown, ChevronUp } from 'lucide-react';
import { API, getAuthHeaders } from '../../services/http';

const eur = (c) => ((c || 0) / 100).toLocaleString('fr-FR', { minimumFractionDigits: 2 }) + ' €';

export const RcrTreasuryPanel = () => {
  const [data, setData] = useState(null);
  const [openMonth, setOpenMonth] = useState(null);

  const load = useCallback(() => {
    fetch(`${API}/convention/admin/rcr-treasury`, { credentials: 'include', headers: getAuthHeaders() })
      .then((r) => (r.ok ? r.json() : null)).then(setData).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  if (!data) return null;

  return (
    <div className="rounded-xl p-4" style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)' }}
      data-testid="rcr-treasury-panel">
      <p className="flex items-center gap-2 text-sm font-semibold text-white/85 mb-3">
        <Landmark className="w-4 h-4 text-[#E9CF8E]" /> Trésorerie RCR détenue par le FOGEDOM-SCIC
      </p>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-4">
        {[['Encours RCR (trésorerie)', data.treasury_cents, '#E9CF8E'],
          ['Constitué (cumul)', data.constitue_cents, '#A5E27E'],
          ['Remboursé (cumul)', data.rembourse_cents, '#93C5FD'],
          ['Remboursements à venir', data.projected_total_cents, '#F0ABFC']].map(([label, cents, color]) => (
          <div key={label} className="rounded-lg p-3 bg-white/[0.04] border border-white/[0.08]">
            <p className="text-[10px] uppercase tracking-wide text-white/40">{label}</p>
            <p className="text-lg font-bold" style={{ color }} data-testid={`treasury-${label.split(' ')[0].toLowerCase()}`}>{eur(cents)}</p>
          </div>
        ))}
      </div>

      <p className="text-[11px] font-bold text-white/60 mb-1">Encours par fournisseur</p>
      {data.vendors.length === 0 ? (
        <p className="text-[11px] text-white/45 mb-3">Aucune fraction RCR constituée pour le moment.</p>
      ) : (
        <table className="w-full text-[11px] mb-4">
          <thead><tr className="text-left text-white/40 border-b border-white/[0.08]">
            <th className="py-1 pr-3">Fournisseur</th><th className="py-1 pr-3">Constitué</th>
            <th className="py-1 pr-3">Extourné</th><th className="py-1 pr-3">Remboursé</th><th className="py-1">Encours</th></tr></thead>
          <tbody>
            {data.vendors.map((v) => (
              <tr key={v.vendor_id} className="border-b border-white/[0.04] text-white/75" data-testid={`treasury-vendor-${v.vendor_id}`}>
                <td className="py-1 pr-3 font-semibold">{v.vendor_name || v.vendor_id}</td>
                <td className="py-1 pr-3 text-[#A5E27E]">{eur(v.constitue)}</td>
                <td className="py-1 pr-3 text-red-300">{eur(v.extourne)}</td>
                <td className="py-1 pr-3 text-[#93C5FD]">{eur(v.rembourse)}</td>
                <td className="py-1 font-bold text-[#E9CF8E]">{eur(v.solde_cents)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <p className="text-[11px] font-bold text-white/60 mb-1">
        Échéancier des remboursements à venir <span className="font-normal text-white/40">(expiration + {data.reimbursement_days} j)</span>
      </p>
      {data.projections.length === 0 ? (
        <p className="text-[11px] text-white/45">Aucun remboursement programmé.</p>
      ) : (
        <div className="space-y-1" data-testid="treasury-projections">
          {data.projections.map((m) => (
            <div key={m.month} className="rounded-lg bg-white/[0.04] border border-white/[0.08]">
              <button type="button" onClick={() => setOpenMonth(openMonth === m.month ? null : m.month)}
                data-testid={`treasury-month-${m.month}`}
                className="w-full flex items-center justify-between px-3 py-2 text-[11px] text-white/75">
                <span className="font-bold">{m.month}</span>
                <span className="inline-flex items-center gap-2">
                  <b className="text-[#F0ABFC]">{eur(m.amount_cents)}</b>
                  {openMonth === m.month ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                </span>
              </button>
              {openMonth === m.month && (
                <div className="px-3 pb-2 space-y-0.5">
                  {m.items.map((it) => (
                    <p key={it.attestation_ref} className="text-[10px] text-white/50">
                      {it.due_date} · {it.attestation_ref} — {it.vendor_name} ({(it.product_name || '').slice(0, 35)}) :{' '}
                      <b className="text-white/75">{eur(it.amount_cents)}</b>
                    </p>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
