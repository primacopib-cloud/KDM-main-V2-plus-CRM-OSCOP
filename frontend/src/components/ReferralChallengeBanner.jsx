import React, { useEffect, useState } from 'react';
import { Trophy, Gift } from 'lucide-react';
import { Link } from 'react-router-dom';

export const ReferralChallengeBanner = () => {
  const [data, setData] = useState(null);

  useEffect(() => {
    fetch(`${process.env.REACT_APP_BACKEND_URL}/api/public/referral-challenge`)
      .then((r) => r.json()).then(setData).catch(() => {});
  }, []);

  if (!data || (!data.active && !data.last_winner)) return null;
  return (
    <section className="px-5 pb-10" data-testid="referral-challenge-banner">
      <div className="max-w-[1160px] mx-auto rounded-[18px] p-5 border border-[#D9B35A]/30 flex items-center gap-4 flex-wrap"
        style={{ background: 'linear-gradient(90deg, rgba(217,179,90,0.14), rgba(217,179,90,0.03))' }}>
        <Trophy size={26} className="text-[#D9B35A] flex-shrink-0" />
        <div className="flex-1 min-w-[240px]">
          {data.active && (
            <p className="text-sm text-white font-semibold" data-testid="challenge-active-text">
              Défi parrainage du mois : le meilleur parrain remporte <span className="text-[#E9CF8E]">{data.reward_credits} CREDI'SCOP</span> !
            </p>
          )}
          {data.last_winner && (
            <p className="text-xs text-white/60 mt-0.5" data-testid="challenge-winner-text">
              🏆 Dernier gagnant : <span className="text-[#E9CF8E] font-semibold">{data.last_winner.name}</span> — {data.last_winner.referred} filleul(s) en {data.last_winner.month} (+{data.last_winner.reward} crédits)
            </p>
          )}
        </div>
        <Link to="/adhesion" data-testid="challenge-cta"
          className="h-10 px-4 rounded-lg text-xs font-semibold text-[#1A092D] inline-flex items-center gap-1.5"
          style={{ background: 'linear-gradient(135deg, #D9B35A, #F2D07A)' }}>
          <Gift size={13} /> Rejoindre et parrainer
        </Link>
      </div>
    </section>
  );
};
