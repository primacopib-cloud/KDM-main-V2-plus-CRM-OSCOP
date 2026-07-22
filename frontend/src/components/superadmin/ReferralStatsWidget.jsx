import { useCallback, useEffect, useState } from 'react';
import { Users2, Trophy, Coins, Save } from 'lucide-react';
import { toast } from 'sonner';
import { Switch } from '../ui/switch';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const ReferralStatsWidget = () => {
  const [data, setData] = useState(null);
  const [challenge, setChallenge] = useState(null);
  const [reward, setReward] = useState('');
  const [reward2, setReward2] = useState('');
  const [reward3, setReward3] = useState('');

  const load = useCallback(() => {
    fetch(`${API}/referral/admin/overview`, { credentials: 'include' })
      .then((r) => r.json()).then(setData).catch(() => {});
    fetch(`${API}/admin/referral/challenge`, { credentials: 'include' })
      .then((r) => r.json()).then((d) => {
        setChallenge(d); setReward(String(d.reward_credits));
        setReward2(String(d.reward_2nd ?? 0)); setReward3(String(d.reward_3rd ?? 0));
      }).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const saveChallenge = async (updates) => {
    const r = await fetch(`${API}/admin/referral/challenge`, {
      method: 'PUT', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    });
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    setChallenge((c) => ({ ...c, ...d }));
    toast.success('Défi parrainage mis à jour');
  };

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
        <div className="mb-4" data-testid="referral-top-list">
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
        <p className="text-[11px] text-white/35 italic mb-4">Aucun parrainage enregistré pour le moment.</p>
      )}

      {challenge && (
        <div className="pt-3 border-t border-white/[0.08]" data-testid="referral-challenge-block">
          <div className="flex items-center gap-2 flex-wrap mb-2">
            <p className="text-[11px] text-white/70 font-semibold flex items-center gap-1.5">
              <Trophy size={11} className="text-[#D9B35A]" /> Défi du mois ({challenge.month})
            </p>
            <Switch checked={!!challenge.enabled} onCheckedChange={(v) => saveChallenge({ enabled: v })}
              data-testid="referral-challenge-switch" />
            <span className="text-[10px] text-white/45">{challenge.enabled ? 'Actif' : 'Inactif'}</span>
            <div className="ml-auto flex items-center gap-1.5 flex-wrap">
              <span className="text-[10px] text-white/50">🥇</span>
              <input value={reward} onChange={(e) => setReward(e.target.value.replace(/\D/g, ''))}
                data-testid="referral-challenge-reward"
                className="w-14 h-7 px-2 rounded-lg bg-white/[0.05] border border-white/15 text-xs text-white text-right" />
              <span className="text-[10px] text-white/50">🥈</span>
              <input value={reward2} onChange={(e) => setReward2(e.target.value.replace(/\D/g, ''))}
                data-testid="referral-challenge-reward2"
                className="w-14 h-7 px-2 rounded-lg bg-white/[0.05] border border-white/15 text-xs text-white text-right" />
              <span className="text-[10px] text-white/50">🥉</span>
              <input value={reward3} onChange={(e) => setReward3(e.target.value.replace(/\D/g, ''))}
                data-testid="referral-challenge-reward3"
                className="w-14 h-7 px-2 rounded-lg bg-white/[0.05] border border-white/15 text-xs text-white text-right" />
              <span className="text-[10px] text-white/50">crédits</span>
              <button onClick={() => saveChallenge({
                reward_credits: parseInt(reward || '0', 10),
                reward_2nd: parseInt(reward2 || '0', 10),
                reward_3rd: parseInt(reward3 || '0', 10),
              })}
                className="p-1.5 rounded-lg bg-white/[0.06] border border-white/10 text-[#E9CF8E]" title="Enregistrer">
                <Save size={12} />
              </button>
            </div>
          </div>
          {challenge.enabled && (
            challenge.leaderboard?.length ? (
              <p className="text-[11px] text-white/60">
                🥇 Leader actuel : <span className="text-[#E9CF8E] font-semibold">{challenge.leaderboard[0].sponsor}</span> ({challenge.leaderboard[0].referred} filleul(s)) — récompense de {challenge.reward_credits} CREDI'SCOP versée automatiquement au meilleur parrain en fin de mois
              </p>
            ) : (
              <p className="text-[11px] text-white/40 italic">Aucun parrainage ce mois-ci — le premier filleul prend la tête du classement !</p>
            )
          )}
          {challenge.past_winners?.filter((w) => w.winner).length > 0 && (
            <p className="mt-1.5 text-[10px] text-white/35">
              Derniers gagnants : {challenge.past_winners.filter((w) => w.winner).slice(0, 3).map((w) => `${w.month} — ${w.winner} (+${w.reward})`).join(' · ')}
            </p>
          )}
        </div>
      )}
    </div>
  );
};
