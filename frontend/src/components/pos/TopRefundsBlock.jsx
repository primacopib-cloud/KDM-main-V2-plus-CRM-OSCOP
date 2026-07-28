import { useEffect, useState } from 'react';
import { Undo2 } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;
const REASON_COLORS = { DEFECTIVE: 'text-red-300', ERROR: 'text-amber-300', EXPIRED: 'text-orange-300', OTHER: 'text-white/50' };

// Gérant : articles les plus retournés (30 j) avec répartition par motif
export const TopRefundsBlock = () => {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    fetch(`${API}/api/lolodrive/pos/counter-refunds/stats`, { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null))
      .then(setStats)
      .catch(() => {});
  }, []);
  if (!stats || stats.items.length === 0) return null;

  return (
    <div className="mt-2 rounded-lg bg-[#FF9E7A]/[0.05] border border-[#FF9E7A]/20 px-3 py-2" data-testid="top-refunds-block">
      <p className="text-[10px] font-bold text-[#FF9E7A] flex items-center gap-1 mb-1.5">
        <Undo2 className="w-3 h-3" /> Articles les plus retournés (30 derniers jours — {stats.total_refunds} retour(s))
      </p>
      <div className="space-y-1">
        {stats.items.slice(0, 5).map((it) => (
          <div key={it.sku} className="flex flex-wrap items-center gap-x-2 text-[11px]" data-testid={`top-refund-${it.sku}`}>
            <span className="font-medium truncate">{it.name}</span>
            <span className="font-mono text-[#FF9E7A] font-bold">×{it.qty}</span>
            <span className="text-[10px]">
              {Object.entries(it.reasons).map(([r, n]) => (
                <span key={r} className={`mr-1.5 ${REASON_COLORS[r] || 'text-white/50'}`}>
                  {stats.reason_labels[r] || r} ×{n}
                </span>
              ))}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};
