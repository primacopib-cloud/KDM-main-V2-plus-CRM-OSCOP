import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Target, Pencil, Check, Trophy } from 'lucide-react';
import { lolodriveAPI } from '../../services/api';

export const SalesGoalBar = ({ refreshKey }) => {
  const [goal, setGoal] = useState(null);
  const [isManager, setIsManager] = useState(false);
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState('');

  useEffect(() => {
    lolodriveAPI.posSessionInfo().then((s) => setIsManager(s.role !== 'OPERATEUR_POS')).catch(() => {});
  }, []);
  useEffect(() => {
    lolodriveAPI.posSalesGoal().then(setGoal).catch(() => {});
  }, [refreshKey]);
  if (!goal) return null;
  if (goal.goal_cents === 0 && !isManager) return null;

  const save = async () => {
    const eur = parseFloat(String(value).replace(',', '.'));
    if (Number.isNaN(eur) || eur < 0) return toast.error('Montant invalide');
    try {
      await lolodriveAPI.managerSetSalesGoal(Math.round(eur * 100));
      toast.success(`Objectif mensuel fixé à ${eur.toFixed(2)} € ✓`);
      setEditing(false);
      lolodriveAPI.posSalesGoal().then(setGoal).catch(() => {});
    } catch (e) { toast.error(e.message); }
  };

  const pct = goal.percent ?? 0;
  const reached = goal.percent !== null && goal.percent >= 100;
  const monthLabel = new Date(`${goal.month}-01`).toLocaleDateString('fr-FR', { month: 'long' });

  return (
    <div className="mb-3 rounded-xl border border-white/[0.08] bg-white/[0.02] px-4 py-2.5" data-testid="sales-goal-bar">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs mb-1.5">
        <span className={`flex items-center gap-1.5 font-bold ${reached ? 'text-emerald-300' : 'text-[#D9B35A]'}`}>
          {reached ? <Trophy className="w-3.5 h-3.5" /> : <Target className="w-3.5 h-3.5" />}
          Objectif caisse {monthLabel}
        </span>
        {goal.goal_cents > 0 ? (
          <span className="font-mono" data-testid="goal-progress-text">
            <b>{(goal.month_total_cents / 100).toFixed(2)} €</b>
            <span className="text-white/40"> / {(goal.goal_cents / 100).toFixed(2)} €</span>
            <b className={`ml-2 ${reached ? 'text-emerald-300' : 'text-[#D9B35A]'}`}>{goal.percent}%</b>
            {reached && <span className="ml-2 text-emerald-300">🎉 Objectif atteint !</span>}
          </span>
        ) : (
          <span className="text-white/40" data-testid="goal-not-set">Aucun objectif fixé pour ce mois.</span>
        )}
        {isManager && (
          <span className="ml-auto shrink-0">
            {editing ? (
              <span className="flex items-center gap-1">
                <input type="number" min="0" step="10" autoFocus value={value} data-testid="goal-input"
                  onChange={(e) => setValue(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') save(); if (e.key === 'Escape') setEditing(false); }}
                  placeholder="€"
                  className="w-24 px-2 py-0.5 rounded bg-white/10 border border-[#D9B35A]/50 text-white text-xs font-mono" />
                <button type="button" onClick={save} data-testid="goal-save-btn"
                  className="px-2 py-0.5 rounded text-[10px] font-bold text-black bg-[#D9B35A] hover:bg-[#c9a34a]">
                  <Check className="w-3 h-3" />
                </button>
              </span>
            ) : (
              <button type="button" data-testid="goal-edit-btn"
                onClick={() => { setValue(goal.goal_cents ? String(goal.goal_cents / 100) : ''); setEditing(true); }}
                className="flex items-center gap-1 px-2 py-0.5 rounded-lg text-[10px] font-bold text-[#D9B35A] bg-[#D9B35A]/10 border border-[#D9B35A]/35 hover:bg-[#D9B35A]/20">
                <Pencil className="w-3 h-3" /> {goal.goal_cents > 0 ? 'Modifier' : 'Fixer un objectif'}
              </button>
            )}
          </span>
        )}
      </div>
      {goal.goal_cents > 0 && (
        <div className="h-2 rounded-full bg-white/[0.06] overflow-hidden" data-testid="goal-progress-track">
          <div className={`h-full rounded-full transition-all ${reached ? 'bg-emerald-400' : 'bg-[#D9B35A]'}`}
            style={{ width: `${Math.min(100, pct)}%` }} />
        </div>
      )}
    </div>
  );
};
