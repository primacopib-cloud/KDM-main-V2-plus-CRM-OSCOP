import { useEffect, useState } from 'react';
import { ShieldCheck } from 'lucide-react';
import { rarAPI } from '../../services/api.rar';

// Note de fiabilité des transporteurs — affichée au choix du mode de livraison/paiement
export const CarrierScoreBadge = () => {
  const [carriers, setCarriers] = useState([]);

  useEffect(() => {
    rarAPI.carrierScores().then((d) => setCarriers(d.carriers || [])).catch(() => {});
  }, []);

  if (carriers.length === 0) return null;
  return (
    <div className="mt-2 space-y-0.5" data-testid="carrier-scores">
      <p className="text-[10px] text-white/40 flex items-center gap-1">
        <ShieldCheck className="w-3 h-3 text-[#4FD1A5]" /> Fiabilité des transporteurs (livraisons sans réserve)
      </p>
      {carriers.map((c) => (
        <p key={c.carrier} className="text-[10px] text-white/55" data-testid={`carrier-score-${c.carrier}`}>
          {c.carrier} :{' '}
          <span className={`font-mono font-bold ${
            c.score >= 80 ? 'text-emerald-300' : c.score >= 50 ? 'text-amber-300' : 'text-red-300'}`}>
            {c.score.toLocaleString('fr-FR')} %
          </span>
          <span className="text-white/35"> · {c.deliveries} livraison{c.deliveries > 1 ? 's' : ''}</span>
        </p>
      ))}
    </div>
  );
};
