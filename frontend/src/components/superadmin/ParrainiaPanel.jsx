import { useCallback, useEffect, useState } from 'react';
import { Megaphone, Rocket, Flame, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const KIND_LABELS = { kickoff: ['🚀 Coup d\'envoi', 'text-emerald-300'], boost: ['🔥 Relance classement', 'text-amber-300'] };

export const ParrainiaPanel = () => {
  const [log, setLog] = useState(null);
  const [running, setRunning] = useState('');

  const load = useCallback(() => {
    fetch(`${API}/admin/parrainia/log`, { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null)).then((d) => setLog(d?.items || [])).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const animate = async (kind) => {
    const label = kind === 'kickoff' ? 'le coup d\'envoi du défi du mois' : 'la relance de classement';
    if (!window.confirm(`PARRAIN'IA va rédiger et envoyer ${label} par email à tous les parrains. Continuer ?`)) return;
    setRunning(kind);
    const r = await fetch(`${API}/admin/parrainia/animate`, {
      method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ kind }),
    });
    const d = await r.json();
    setRunning('');
    if (!r.ok) return toast.error(d.detail || 'Campagne échouée');
    toast.success(`PARRAIN'IA : ${d.sent} email(s) envoyés${d.launched_challenge ? ' — défi du mois activé automatiquement' : ''}`);
    load();
  };

  return (
    <div className="glass-panel-soft rounded-[18px] p-5 space-y-4" data-testid="parrainia-panel">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h3 className="font-display text-base text-white flex items-center gap-2">
          <Megaphone size={15} style={{ color: '#D9B35A' }} /> PARRAIN'IA — animation du programme de parrainage
        </h3>
        <div className="flex gap-2">
          <button onClick={() => animate('kickoff')} disabled={!!running} data-testid="parrainia-kickoff-btn"
            className="px-3 py-2 rounded-lg text-xs font-bold inline-flex items-center gap-1.5 disabled:opacity-60"
            style={{ background: '#D9B35A', color: '#1F0A33' }}>
            {running === 'kickoff' ? <Loader2 size={12} className="animate-spin" /> : <Rocket size={12} />} Lancer le défi du mois
          </button>
          <button onClick={() => animate('boost')} disabled={!!running} data-testid="parrainia-boost-btn"
            className="px-3 py-2 rounded-lg text-xs font-bold inline-flex items-center gap-1.5 bg-white/[0.06] border border-white/15 text-white/80 disabled:opacity-60">
            {running === 'boost' ? <Loader2 size={12} className="animate-spin" /> : <Flame size={12} />} Animer le classement
          </button>
        </div>
      </div>
      <p className="text-xs text-white/50">
        En automatique : coup d'envoi en début de mois (active le défi si besoin) et relance de mi-mois avec le
        classement personnalisé de chaque parrain. Vous pouvez aussi déclencher une animation manuellement.
      </p>
      <div className="space-y-1.5" data-testid="parrainia-log">
        {log === null ? null : log.length === 0 ? (
          <p className="text-xs text-white/40 italic">Aucune animation envoyée pour le moment.</p>
        ) : log.map((l) => {
          const [label, cls] = KIND_LABELS[l.kind] || [l.kind, 'text-white/60'];
          return (
            <div key={l.id} className="flex items-center gap-2 text-xs p-2 rounded-lg bg-white/[0.03] border border-white/[0.06]">
              <span className={`font-bold ${cls}`}>{label}</span>
              <span className="text-white/70 truncate flex-1">« {l.subject} »</span>
              <span className="text-white/45">{l.sent} envoyé(s)</span>
              <span className="text-white/35">{new Date(l.at).toLocaleDateString('fr-FR')}</span>
              {l.triggered_by === 'parrainia-auto' && <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-white/10 text-white/50">AUTO</span>}
            </div>
          );
        })}
      </div>
    </div>
  );
};
