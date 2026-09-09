import { useEffect, useState } from 'react';
import { Handshake } from 'lucide-react';
import { getAuthHeaders } from '../../services/http';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Superadmin : historique des acceptations d'offres (email ou directement depuis la CommunityPlace)
export const BoardAcceptancesPanel = () => {
  const [data, setData] = useState(null);

  useEffect(() => {
    fetch(`${API_URL}/api/admin/purchase-needs/acceptances`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => d && setData(d))
      .catch(() => {});
  }, []);

  if (!data || !data.needs.length) return null;
  return (
    <div className="rounded-2xl p-5 mt-6 bg-white/[0.03] border border-white/[0.08]" data-testid="board-acceptances-panel">
      <div className="flex items-center gap-2 mb-3">
        <Handshake className="w-4 h-4 text-[#8CC63E]" />
        <h3 className="text-sm font-bold text-[#E9CF8E] m-0">
          Acceptations d'offres CommunityPlace ({data.total_acceptances})
        </h3>
      </div>
      <div className="space-y-2 max-h-72 overflow-y-auto">
        {data.needs.map((n) => (
          <div key={n.reference} className="rounded-xl px-3 py-2.5 bg-white/[0.02] border border-white/[0.06] text-[11px] text-white/70"
            data-testid={`acceptance-row-${n.reference}`}>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-white font-semibold">{n.reference} · {n.product}</span>
              {n.vendor_price_eur != null && (
                <span className="font-mono text-[#8CC63E] font-bold">{Number(n.vendor_price_eur).toLocaleString('fr-FR')} €</span>
              )}
              {n.responder && (
                <span className="text-white/40">
                  offre {n.responder_role === 'COOPER' ? "COOPER'S" : 'vendeur'} : {n.responder}
                </span>
              )}
            </div>
            <div className="mt-1 flex flex-wrap gap-x-4 gap-y-0.5">
              {n.acceptances.map((a, i) => (
                <span key={`${a.email}-${i}`} className="text-white/60" data-testid={`acceptance-entry-${n.reference}-${i}`}>
                  ✔ <b className="text-white/85">{a.email}</b> ({a.role}) le {String(a.accepted_at || '').slice(0, 10)}
                  <span className={`ml-1 px-1.5 py-0.5 rounded-full text-[9px] font-bold uppercase border ${
                    a.via === 'board'
                      ? 'text-[#8CC63E] bg-[#8CC63E]/10 border-[#8CC63E]/40'
                      : 'text-sky-300 bg-sky-500/10 border-sky-400/40'}`}>
                    {a.via === 'board' ? 'CommunityPlace' : 'Email'}
                  </span>
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
