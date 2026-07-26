import { useEffect, useState } from 'react';
import { Trophy, Medal, MessageCircle, Linkedin, Copy } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;
const MEDALS = ['🥇', '🥈', '🥉'];

const MedalShare = ({ rank, referralCode, month }) => {
  const shareUrl = `${window.location.origin}/api/share/challenge?rank=${rank}&code=${referralCode}&month=${month}`;
  const shareText = `${MEDALS[rank - 1]} Je suis #${rank} du défi parrainage KDMARCHÉ × O'SCOP ce mois-ci ! Rejoignez la coopérative avec mon code parrain ${referralCode} : ${shareUrl}`;
  const copy = () => {
    navigator.clipboard.writeText(shareText);
    toast.success('Lien de partage de votre médaille copié');
  };
  return (
    <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-white/10" data-testid="medal-share">
      <span className="text-[11px] text-white/60 font-semibold">{MEDALS[rank - 1]} Partagez votre médaille :</span>
      <a href={`https://wa.me/?text=${encodeURIComponent(shareText)}`} target="_blank" rel="noreferrer" data-testid="medal-share-whatsapp"
        className="px-2.5 py-1 rounded-lg text-[10.5px] font-bold inline-flex items-center gap-1 transition-all hover:brightness-110"
        style={{ background: '#25D366', color: '#0b3d22' }}>
        <MessageCircle className="w-3 h-3" /> WhatsApp
      </a>
      <a href={`https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(shareUrl)}`} target="_blank" rel="noreferrer" data-testid="medal-share-linkedin"
        className="px-2.5 py-1 rounded-lg text-[10.5px] font-bold inline-flex items-center gap-1 transition-all hover:brightness-110"
        style={{ background: '#0A66C2', color: '#fff' }}>
        <Linkedin className="w-3 h-3" /> LinkedIn
      </a>
      <button type="button" onClick={copy} data-testid="medal-share-copy"
        className="px-2.5 py-1 rounded-lg text-[10.5px] font-bold bg-white/10 text-white/70 hover:text-white inline-flex items-center gap-1 transition-colors">
        <Copy className="w-3 h-3" /> Copier
      </button>
    </div>
  );
};

export const ChallengePodium = ({ referralCode }) => {
  const [data, setData] = useState(null);

  useEffect(() => {
    fetch(`${API}/api/public/referral-challenge/standing`, { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null)).then(setData).catch(() => {});
  }, []);

  if (!data || !data.enabled) return null;

  return (
    <div className="rounded-xl p-4 bg-gradient-to-br from-[#D9B35A]/10 to-transparent border border-[#D9B35A]/20 space-y-3" data-testid="challenge-podium">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h4 className="text-sm font-bold text-white flex items-center gap-2">
          <Trophy className="w-4 h-4 text-[#D9B35A]" /> Défi parrainage {data.month}
        </h4>
        <span className="text-[11px] font-bold text-[#E9CF8E]" data-testid="challenge-reward">
          {data.tier_rewards && (data.tier_rewards[1] > 0 || data.tier_rewards[2] > 0)
            ? <>🥇 +{data.tier_rewards[0]}{data.tier_rewards[1] > 0 && <> · 🥈 +{data.tier_rewards[1]}</>}{data.tier_rewards[2] > 0 && <> · 🥉 +{data.tier_rewards[2]}</>} CREDI'SCOP</>
            : <>🏆 +{data.reward_credits} CREDI'SCOP pour le meilleur parrain</>}
        </span>
      </div>
      {data.top?.length > 0 ? (
        <>
        <div className="grid grid-cols-3 gap-2" data-testid="challenge-top3">
          {data.top.slice(0, 3).map((r, i) => (
            <div key={i} data-testid={`challenge-podium-rank-${i + 1}`}
              className={`rounded-lg px-2 py-2.5 text-center border ${r.me
                ? 'bg-[#D9B35A]/15 border-[#D9B35A]/50'
                : 'bg-white/[0.04] border-white/10'}`}>
              <div className="text-lg leading-none">{MEDALS[i]}</div>
              <p className={`text-[11px] font-semibold truncate mt-1 ${r.me ? 'text-[#E9CF8E]' : 'text-white/70'}`}>
                {r.me ? 'Vous' : r.name}
              </p>
              <p className="text-[10px] text-white/45">{r.referred} filleul(s)</p>
            </div>
          ))}
        </div>
        {data.top.length > 3 && (
          <div className="space-y-1" data-testid="challenge-runners-up">
            {data.top.slice(3).map((r, i) => (
              <div key={i} className={`flex items-center gap-2 text-[11px] px-2 py-1 rounded-md ${r.me ? 'bg-[#D9B35A]/12 text-[#E9CF8E]' : 'text-white/60'}`}>
                <span className="font-bold w-6">#{i + 4}</span>
                <span className="flex-1 truncate">{r.me ? 'Vous' : r.name}</span>
                <span className="text-white/40">{r.referred} filleul(s)</span>
              </div>
            ))}
          </div>
        )}
        </>
      ) : (
        <p className="text-xs text-white/50" data-testid="challenge-empty">
          Aucun parrainage ce mois-ci — soyez le premier à prendre la tête du podium !
        </p>
      )}
      <p className="text-xs text-white/60 flex items-center gap-1.5" data-testid="challenge-my-rank">
        <Medal className="w-3.5 h-3.5 text-[#D9B35A]" />
        {data.my_rank
          ? <>Votre position : <b className="text-[#E9CF8E]">#{data.my_rank}</b> sur {data.participants} participant(s) — {data.my_count} filleul(s) ce mois-ci</>
          : <>Vous n'êtes pas encore classé ce mois-ci — parrainez un membre pour entrer au classement !</>}
      </p>
      {data.my_rank >= 1 && data.my_rank <= 3 && referralCode && (
        <MedalShare rank={data.my_rank} referralCode={referralCode} month={data.month} />
      )}
    </div>
  );
};
