import { useEffect, useState } from 'react';
import { Users } from 'lucide-react';
import { detaillantAPI } from '../../services/api.detaillant';

// Communauté du POP'S : followers + évolution mensuelle
export const DetaillantFollowersCard = () => {
  const [stats, setStats] = useState(null);
  useEffect(() => { detaillantAPI.followersStats().then(setStats).catch(() => {}); }, []);
  if (!stats) return null;
  const max = Math.max(1, ...(stats.monthly || []).map((m) => m.new));
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4" data-testid="dt-followers-card">
      <h3 className="text-sm font-bold text-[#E9CF8E] mb-2 flex items-center gap-2">
        <Users className="w-4 h-4" /> Ma communauté
      </h3>
      <p className="text-2xl font-black" data-testid="dt-followers-total">{stats.total}</p>
      <p className="text-[10px] text-white/45">membre{stats.total > 1 ? 's' : ''} suivent votre POP'S — chacun reçoit cloche + email à chaque nouveau lot validé</p>
      {(stats.monthly || []).length > 0 && (
        <div className="flex items-end gap-1.5 mt-3 h-14" data-testid="dt-followers-chart">
          {stats.monthly.map((m) => (
            <div key={m.month} className="flex flex-col items-center gap-0.5" title={`${m.month} : +${m.new}`}>
              <span className="text-[8px] text-emerald-300 font-bold">+{m.new}</span>
              <div className="w-6 rounded-t bg-emerald-500/60" style={{ height: `${Math.max(6, (m.new / max) * 36)}px` }} />
              <span className="text-[7px] text-white/35">{m.month.slice(5)}/{m.month.slice(2, 4)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
