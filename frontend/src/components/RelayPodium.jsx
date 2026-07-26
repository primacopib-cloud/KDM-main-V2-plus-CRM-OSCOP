import { useEffect, useState } from 'react';
import { Trophy, Star } from 'lucide-react';
import { lolodriveAPI } from '../services/api';

const MEDALS = [
  { ring: '#FFD700', bg: 'rgba(255,215,0,0.12)', label: '1er' },
  { ring: '#C0C0C0', bg: 'rgba(192,192,192,0.10)', label: '2e' },
  { ring: '#CD7F32', bg: 'rgba(205,127,50,0.10)', label: '3e' },
];

export const RelayPodium = ({ onView }) => {
  const [podium, setPodium] = useState([]);

  useEffect(() => {
    lolodriveAPI.relayPodium()
      .then((d) => setPodium(d.podium || []))
      .catch(() => {});
  }, []);

  if (!podium.length) return null;
  return (
    <div className="mt-6" data-testid="relay-podium">
      <p className="text-[11px] uppercase tracking-[0.2em] text-[#D9B35A] font-bold mb-3 flex items-center gap-2">
        <Trophy className="w-4 h-4" /> Podium du mois — relais les mieux notés
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {podium.map((p, i) => {
          const m = MEDALS[i] || MEDALS[2];
          return (
            <button key={p.code} type="button" data-testid={`podium-${i + 1}`}
              onClick={() => onView?.(p.code)}
              className={`flex items-center gap-3 rounded-2xl p-3.5 border text-left w-full transition-transform ${onView ? 'cursor-pointer hover:scale-[1.02]' : 'cursor-default'}`}
              style={{ borderColor: m.ring, background: m.bg }}>
              <span className="w-9 h-9 rounded-full flex items-center justify-center font-black text-sm text-black shrink-0"
                style={{ background: m.ring }}>
                {m.label}
              </span>
              <div className="min-w-0">
                <p className="text-sm font-bold text-white truncate">{p.name}</p>
                <p className="text-[11px] text-white/50 truncate">{p.city}{p.territory ? ` · ${p.territory}` : ''}</p>
                <p className="text-xs font-semibold text-[#E9CF8E] flex items-center gap-1">
                  <Star className="w-3.5 h-3.5 fill-[#D9B35A] text-[#D9B35A]" /> {p.avg}
                  <span className="text-white/40 font-normal">({p.count} avis ce mois-ci)</span>
                </p>
                {onView && (
                  <p className="text-[10px] font-semibold text-[#D9B35A] mt-0.5">Voir les avis →</p>
                )}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};
