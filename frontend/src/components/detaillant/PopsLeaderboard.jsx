import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Trophy, BadgeCheck } from 'lucide-react';
import { Flag } from '../Flag';
import { detaillantAPI } from '../../services/api.detaillant';

// Mini palmarès des POP'S les mieux notés (vitrine publique /detaillant)
export const PopsLeaderboard = ({ t }) => {
  const [shops, setShops] = useState([]);
  useEffect(() => { detaillantAPI.shopsPublic().then((d) => setShops((d.shops || []).filter((s) => s.rating_avg))).catch(() => {}); }, []);
  if (shops.length === 0) return null;
  return (
    <div className="mt-14" data-testid="pops-leaderboard">
      <h2 className="text-base md:text-lg font-bold text-[#E9CF8E] flex items-center gap-2">
        <Trophy className="w-4 h-4" /> {t.topShops}
      </h2>
      <p className="text-xs text-white/50 mt-1">{t.topShopsSub}</p>
      <Link to="/pops" data-testid="pops-leaderboard-full"
        className="inline-block text-[11px] font-bold text-emerald-300 hover:text-emerald-200 mt-2 underline underline-offset-2">
        Voir le palmarès complet →
      </Link>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3 mt-4">
        {shops.slice(0, 6).map((s, i) => (
          <Link key={s.user_id} to={`/pops/${s.user_id}`} className="block rounded-xl border border-white/10 bg-white/[0.03] p-3 hover:border-emerald-400/40 transition-colors"
            data-testid={`pops-rank-${i + 1}`}>
            <div className="flex items-center gap-2">
              <span className="text-lg font-black text-[#D9B35A] w-6">{['🥇', '🥈', '🥉'][i] || `#${i + 1}`}</span>
              <div className="min-w-0">
                <p className="text-xs font-bold truncate flex items-center gap-1.5">
                  <Flag code={s.country_code} /> {s.company_name}
                </p>
                <p className="text-[10px] text-white/45 truncate">{s.locality}</p>
              </div>
              <span className="ml-auto text-xs font-bold text-amber-300 shrink-0">
                ★ {Number(s.rating_avg).toFixed(1)} <span className="text-white/40 font-normal">({s.rating_count})</span>
              </span>
            </div>
            {(s.reviews || []).slice(0, 1).map((r) => (
              <div key={r.created_at} className="mt-2 pt-2 border-t border-white/[0.06]">
                <p className="text-[10px] text-white/55 italic">« {r.comment || '★'.repeat(r.rating)} »</p>
                {r.reply && (
                  <p className="text-[10px] text-emerald-300/80 mt-1 flex items-start gap-1">
                    <BadgeCheck className="w-3 h-3 shrink-0 mt-px" /> {t.replyLabel} {r.reply}
                  </p>
                )}
              </div>
            ))}
          </Link>
        ))}
      </div>
    </div>
  );
};
