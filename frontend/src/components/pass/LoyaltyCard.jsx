import { useEffect, useState } from 'react';
import { Gift } from 'lucide-react';
import { lolodriveAPI } from '../../services/api';

// Jauge de fidélité : progression « X/10 achats » vers le prochain bonus UC, par relais
export const LoyaltyCard = () => {
  const [data, setData] = useState(null);
  useEffect(() => {
    lolodriveAPI.loyaltyMe().then(setData).catch(() => {});
  }, []);
  if (!data) return null;

  return (
    <div className="rounded-2xl bg-white/[0.025] border border-[#D9B35A]/25 p-4 mb-6" data-testid="loyalty-card">
      <div className="flex items-center gap-2 mb-2">
        <Gift className="w-4 h-4 text-[#D9B35A]" />
        <span className="font-semibold text-sm">Fidélité comptoir</span>
        <span className="ml-auto text-[10px] px-2 py-0.5 rounded-full font-bold text-[#D9B35A] bg-[#D9B35A]/10 border border-[#D9B35A]/35">
          +{data.bonus_uc} UC tous les {data.threshold} achats
        </span>
      </div>
      {data.relays.length === 0 ? (
        <p className="text-xs text-white/45" data-testid="loyalty-empty">
          Faites vos achats au comptoir de votre relais : tous les {data.threshold} achats,
          <b className="text-[#D9B35A]"> +{data.bonus_uc} UC offerts</b> sur votre CREDI'SCOP !
        </p>
      ) : (
        <div className="space-y-3">
          {data.relays.map((r) => (
            <div key={r.point_id} data-testid={`loyalty-relay-${r.point_code}`}>
              <div className="flex items-baseline justify-between text-xs mb-1">
                <span className="font-medium">{r.point_name}</span>
                <span className="font-mono text-[#D9B35A]" data-testid={`loyalty-progress-${r.point_code}`}>
                  {r.progress}/{data.threshold} achats
                </span>
              </div>
              <div className="h-2 rounded-full bg-white/[0.06] overflow-hidden">
                <div className="h-full rounded-full transition-all"
                  style={{ width: `${Math.round((r.progress / data.threshold) * 100)}%`,
                           background: 'linear-gradient(90deg, #D9B35A, #7c3aed)' }} />
              </div>
              <div className="flex justify-between text-[10px] text-white/40 mt-1">
                <span>
                  {r.remaining === data.threshold && r.progress === 0 && r.bonuses_earned > 0
                    ? '🎁 Bonus tout juste gagné — nouveau cycle !'
                    : `Plus que ${r.remaining} achat${r.remaining > 1 ? 's' : ''} avant +${data.bonus_uc} UC`}
                </span>
                {r.bonuses_earned > 0 && <span>🏆 {r.bonuses_earned} bonus déjà gagné{r.bonuses_earned > 1 ? 's' : ''}</span>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
