import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { UserCheck, Clock, Coffee, Play } from 'lucide-react';
import { lolodriveAPI } from '../../services/api';
import { PosPointInfoCard } from './PosPointInfoCard';

export const PosSessionBanner = () => {
  const [session, setSession] = useState(null);
  const [brk, setBrk] = useState(null);
  const [busy, setBusy] = useState(false);

  const loadBreak = () => lolodriveAPI.posBreakStatus().then(setBrk).catch(() => {});
  useEffect(() => {
    lolodriveAPI.posSessionInfo().then(setSession).catch(() => {});
    loadBreak();
  }, []);
  if (!session) return null;

  const ts = session.last_login_at
    ? new Date(session.last_login_at).toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
    : null;
  const isOperator = session.role === 'OPERATEUR_POS';
  const onBreak = brk?.on_break;

  const toggleBreak = async () => {
    setBusy(true);
    try {
      if (onBreak) {
        const r = await lolodriveAPI.posBreakEnd();
        toast.success(`Reprise de la caisse — pause de ${r.duration_min} min enregistrée ✓`);
      } else {
        await lolodriveAPI.posBreakStart();
        toast.success('Pause commencée — bonne pause ☕');
      }
      loadBreak();
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };

  return (
    <>
    <div className={`mb-4 rounded-xl border px-4 py-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs ${
      onBreak ? 'border-amber-400/40 bg-amber-400/[0.07]' : 'border-emerald-400/30 bg-emerald-400/[0.05]'}`}
      data-testid="pos-session-banner">
      <span className={`flex items-center gap-1.5 font-bold ${onBreak ? 'text-amber-300' : 'text-emerald-300'}`}>
        {onBreak ? <Coffee className="w-3.5 h-3.5" /> : <UserCheck className="w-3.5 h-3.5" />}
        {onBreak ? 'En pause' : isOperator ? 'Opérateur en caisse' : 'Session gérant'}
      </span>
      <span className="font-semibold" data-testid="session-operator-name">{session.name}</span>
      {session.point_code && <span className="text-white/40">· Relais {session.point_code}</span>}
      {onBreak && brk?.current?.started_at && (
        <span className="text-amber-200 font-mono" data-testid="break-since">
          depuis {new Date(brk.current.started_at).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}
        </span>
      )}
      {brk?.today_count > 0 && (
        <span className="text-white/40" data-testid="break-today-total">
          · Pauses du jour : {brk.today_count} ({brk.today_total_min} min)
        </span>
      )}
      <span className="ml-auto flex items-center gap-2 shrink-0">
        {ts && (
          <span className="flex items-center gap-1 font-mono text-white/60" data-testid="session-login-time">
            <Clock className="w-3 h-3" /> Connecté le {ts}
          </span>
        )}
        <button type="button" onClick={toggleBreak} disabled={busy} data-testid="break-toggle-btn"
          className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-[10px] font-bold border disabled:opacity-50 ${
            onBreak ? 'text-emerald-300 bg-emerald-400/10 border-emerald-400/40 hover:bg-emerald-400/20'
              : 'text-amber-300 bg-amber-400/10 border-amber-400/40 hover:bg-amber-400/20'}`}>
          {onBreak ? <><Play className="w-3 h-3" /> Reprendre la caisse</> : <><Coffee className="w-3 h-3" /> Pause</>}
        </button>
      </span>
    </div>
    <PosPointInfoCard point={session.point} />
    </>
  );
};
