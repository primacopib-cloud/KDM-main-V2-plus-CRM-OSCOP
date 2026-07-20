import { useEffect, useState } from 'react';
import { Gift, Trophy } from 'lucide-react';
import { API, getAuthHeaders } from '../../services/http';

export const ReferralAdminPanel = () => {
  const [data, setData] = useState(null);

  useEffect(() => {
    fetch(`${API}/referral/admin/overview`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null)).then(setData).catch(() => {});
  }, []);

  if (!data) return null;
  return (
    <div className="glass-panel-soft rounded-[14px] p-4" data-testid="referral-admin-panel">
      <h3 className="text-xs font-bold text-white/70 uppercase mb-3 flex items-center gap-1.5">
        <Gift className="w-3.5 h-3.5" /> Programme de parrainage
      </h3>
      <div className="flex flex-wrap gap-4 mb-3 text-xs">
        <span className="text-white/60">Parrainages : <b className="text-white">{data.total_links}</b></span>
        <span className="text-white/60">Bonus versés : <b className="text-emerald-400">{data.total_bonus_paid}</b></span>
        <span className="text-white/60">Total crédité : <b className="text-[#E9CF8E]">{data.total_credited} CREDI'SCOP</b></span>
      </div>
      {data.top_ambassadors?.length > 0 && (
        <div className="mb-3">
          <p className="text-[10px] text-white/50 uppercase font-bold mb-1 flex items-center gap-1"><Trophy className="w-3 h-3 text-[#D9B35A]" /> Meilleurs ambassadeurs</p>
          {data.top_ambassadors.map((a, i) => (
            <div key={a.sponsor} className="flex items-center gap-2 text-[11px] py-1 border-b border-white/5 last:border-0" data-testid={`referral-top-${i}`}>
              <span className="w-5 text-white/40 font-bold">#{i + 1}</span>
              <span className="flex-1 text-white/80">{a.sponsor}</span>
              <span className="text-white/50">{a.referred} filleul(s)</span>
              <span className="font-bold text-[#E9CF8E]">+{a.credited} CREDI'SCOP</span>
            </div>
          ))}
        </div>
      )}
      {data.links?.length > 0 && (
        <div>
          <p className="text-[10px] text-white/50 uppercase font-bold mb-1">Derniers parrainages</p>
          {data.links.slice(0, 15).map((l, i) => (
            <div key={i} className="flex items-center gap-2 text-[11px] py-1 border-b border-white/5 last:border-0">
              <span className="flex-1 text-white/75 truncate">{l.sponsor} → {l.filleul}</span>
              {l.bonus_paid
                ? <span className="text-emerald-400 font-bold">+{l.bonus_amount} versé</span>
                : <span className="text-white/40">en attente 1ère inscription</span>}
              <span className="text-white/35">{String(l.created_at || '').slice(0, 10)}</span>
            </div>
          ))}
        </div>
      )}
      {!data.total_links && <p className="text-xs text-white/40">Aucun parrainage pour l'instant.</p>}
    </div>
  );
};
