import { useEffect, useState } from 'react';
import { UserCheck, Clock } from 'lucide-react';
import { lolodriveAPI } from '../../services/api';

export const PosSessionBanner = () => {
  const [session, setSession] = useState(null);
  useEffect(() => {
    lolodriveAPI.posSessionInfo().then(setSession).catch(() => {});
  }, []);
  if (!session) return null;
  const ts = session.last_login_at
    ? new Date(session.last_login_at).toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
    : null;
  const isOperator = session.role === 'OPERATEUR_POS';
  return (
    <div className="mb-4 rounded-xl border border-emerald-400/30 bg-emerald-400/[0.05] px-4 py-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs"
      data-testid="pos-session-banner">
      <span className="flex items-center gap-1.5 font-bold text-emerald-300">
        <UserCheck className="w-3.5 h-3.5" /> {isOperator ? 'Opérateur en caisse' : 'Session gérant'}
      </span>
      <span className="font-semibold" data-testid="session-operator-name">{session.name}</span>
      {session.point_code && <span className="text-white/40">· Relais {session.point_code}</span>}
      {ts && (
        <span className="ml-auto flex items-center gap-1 font-mono text-white/60" data-testid="session-login-time">
          <Clock className="w-3 h-3" /> Connecté le {ts}
        </span>
      )}
    </div>
  );
};
