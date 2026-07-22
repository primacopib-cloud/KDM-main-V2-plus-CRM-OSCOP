import { useEffect, useState } from 'react';
import { Users2, Trophy, Coins } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const ReferralStatsWidget = () => {
  const [data, setData] = useState(null);

  useEffect(() => {
    fetch(`${API}/referral/admin/overview`, { credentials: 'include' })
      .then((r) => r.json()).then(setData).catch(() => {});
  }, []);

  if (!data) return null;
  return (
    <div className="mb-8 p-5 rounded-2xl bg-white/[0.02] border border-white/[0.08]" data-testid="referral-stats-widget">
      <h3 className="text-sm font-semibold text-white flex items-center gap-2 mb-4">
        <Users2 className="w-4 h-4 text-[#D9B35A]" /> Parrainage
      </h3>
      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]" data-testid="referral-total-links">
          <p className="text-lg font-bold text-white">{data.total_links}</p>
          <p className="text-[10px] text-white/50">Membres venus par parrainage</p>
        </div>
        <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
          <p className="text-lg font-bold text-emerald-300">{data.total_bonus_paid}</p>
          <p className="text-[10px] text-white/50">Bonus versés</p>
        </div>
        <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
          <p className="text-lg font-bold text-[#E9CF8E] flex items-center gap-1"><Coins size={14} /> {data.total_credited}</p>
          <p className="text-[10px] text-white/50">Crédits distribués</p>
        </div>
      </div>
      {data.top_ambassadors?.length ? (
        <div data-testid="referral-top-list">
          <p className="text-[11px] text-white/55 font-semibold mb-2 flex items-center gap-1.5">
            <Trophy size={11} className="text-[#D9B35A]" /> Meilleurs parrains
          </p>
          <div className="space-y-1.5">
            {data.top_ambassadors.slice(0, 5).map((a, i) => (
              <div key={a.sponsor} className="flex items-center gap-2 text-xs p-2 rounded-lg bg-white/[0.03] border border-white/[0.05]">
                <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold ${i === 0 ? 'bg-[#D9B35A]/25 text-[#E9CF8E]' : 'bg-white/10 text-white/60'}`}>{i + 1}</span>
                <span className="text-white/85 truncate">{a.sponsor}</span>
                <span className="ml-auto text-white/50">{a.referred} filleul(s) · {a.credited} crédits</span>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <p className="text-[11px] text-white/35 italic">Aucun parrainage enregistré pour le moment.</p>
      )}
    </div>
  );
};
