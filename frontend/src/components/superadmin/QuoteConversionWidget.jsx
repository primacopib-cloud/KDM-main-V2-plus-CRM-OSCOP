import { useEffect, useState } from 'react';
import { TrendingUp, Target, Pencil, Check, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';

export const QuoteConversionWidget = () => {
  const [stats, setStats] = useState(null);
  const [editing, setEditing] = useState(false);
  const [targetInput, setTargetInput] = useState('');
  const [saving, setSaving] = useState(false);

  const load = () => {
    fetch(`${API}/admin/quotes/stats`, { credentials: 'include', headers: getAuthHeaders() })
      .then((r) => (r.ok ? r.json() : null)).then(setStats).catch(() => {});
  };
  useEffect(load, []);

  const saveTarget = async () => {
    setSaving(true);
    try {
      const r = await fetch(`${API}/admin/quotes/target`, {
        method: 'PUT', credentials: 'include',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ target: Number(targetInput) || 0 }),
      });
      if (!r.ok) throw new Error();
      toast.success('Objectif mensuel enregistré');
      setEditing(false);
      load();
    } catch { toast.error('Objectif non enregistré'); }
    setSaving(false);
  };

  if (!stats || !stats.total) return null;
  const target = stats.monthly_target || 0;
  const done = stats.converted_this_month || 0;
  const pct = target > 0 ? Math.min(100, Math.round((done / target) * 100)) : 0;
  const reached = target > 0 && done >= target;

  return (
    <div className="glass-panel-soft rounded-[18px] p-4" data-testid="quote-conversion-widget">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[#D9B35A]/15 border border-[#D9B35A]/30 flex items-center justify-center">
            <TrendingUp size={18} className="text-[#E9CF8E]" />
          </div>
          <div>
            <p className="text-xs text-white/50">Conversion des devis</p>
            <p className="text-xl font-bold text-white" data-testid="quote-conversion-rate">
              {stats.conversion_rate}%
              <span className="text-xs font-normal text-white/45"> · {stats.converted} converti(s) sur {stats.total} reçu(s)</span>
            </p>
          </div>
        </div>
        <div className="flex gap-2 flex-wrap text-[10px] font-bold">
          <span className="px-2 py-1 rounded-full" style={{ color: '#60A5FA', background: '#60A5FA1a' }}>{stats.pending} Nouveau</span>
          <span className="px-2 py-1 rounded-full" style={{ color: '#FBBF24', background: '#FBBF241a' }}>{stats.contacted} Contacté</span>
          <span className="px-2 py-1 rounded-full" style={{ color: '#7BC94E', background: '#7BC94E1a' }}>{stats.converted} Converti</span>
          <span className="px-2 py-1 rounded-full" style={{ color: '#F87171', background: '#F871711a' }}>{stats.lost} Perdu</span>
        </div>
      </div>
      <div className="mt-3 h-2 rounded-full bg-white/[0.06] overflow-hidden flex">
        <div style={{ width: `${(stats.converted / stats.total) * 100}%`, background: '#7BC94E' }} />
        <div style={{ width: `${(stats.contacted / stats.total) * 100}%`, background: '#FBBF24' }} />
        <div style={{ width: `${(stats.pending / stats.total) * 100}%`, background: '#60A5FA' }} />
        <div style={{ width: `${(stats.lost / stats.total) * 100}%`, background: '#F87171' }} />
      </div>

      <div className="mt-4 pt-3 border-t border-white/[0.08]" data-testid="quote-monthly-target-block">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <p className="text-xs text-white/55 flex items-center gap-1.5">
            <Target size={13} className="text-[#D9B35A]" /> Objectif du mois
            {target > 0 ? (
              <span className={`font-bold ${reached ? 'text-[#7BC94E]' : 'text-[#E9CF8E]'}`} data-testid="quote-target-progress">
                {done} / {target} converti(s){reached && ' — objectif atteint 🎯'}
              </span>
            ) : (
              <span className="text-white/35 italic">non défini</span>
            )}
          </p>
          {editing ? (
            <span className="inline-flex items-center gap-1.5">
              <input type="number" min="0" autoFocus value={targetInput} data-testid="quote-target-input"
                onChange={(e) => setTargetInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && saveTarget()}
                className="w-20 h-7 px-2 rounded-md text-xs text-white bg-white/[0.06] border border-[#D9B35A]/40 focus:outline-none" />
              <button onClick={saveTarget} disabled={saving} data-testid="quote-target-save"
                className="h-7 px-2 rounded-md text-[10px] font-bold bg-[#D9B35A] text-[#1F0A33] inline-flex items-center gap-1 disabled:opacity-50">
                {saving ? <Loader2 size={10} className="animate-spin" /> : <Check size={10} />} OK
              </button>
              <button onClick={() => setEditing(false)} className="h-7 px-1.5 rounded-md text-[10px] text-white/50 border border-white/15">✕</button>
            </span>
          ) : (
            <button onClick={() => { setTargetInput(target || ''); setEditing(true); }} data-testid="quote-target-edit"
              className="inline-flex items-center gap-1 text-[10px] font-bold text-white/50 hover:text-[#E9CF8E] transition-colors">
              <Pencil size={10} /> {target > 0 ? 'Modifier' : 'Définir un objectif'}
            </button>
          )}
        </div>
        {target > 0 && (
          <div className="mt-2 h-2 rounded-full bg-white/[0.06] overflow-hidden">
            <div className="h-full rounded-full transition-all"
              style={{ width: `${pct}%`, background: reached ? '#7BC94E' : '#D4AF37' }} />
          </div>
        )}
      </div>
    </div>
  );
};
