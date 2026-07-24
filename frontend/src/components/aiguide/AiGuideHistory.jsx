import { useEffect, useState } from 'react';
import { MessageSquare, Loader2 } from 'lucide-react';
import { API, getAuthHeaders } from '../../services/http';

export const AiGuideHistory = ({ onResume }) => {
  const [sessions, setSessions] = useState(null);
  const [loadingId, setLoadingId] = useState(null);

  useEffect(() => {
    fetch(`${API}/ai-guide/sessions`, { credentials: 'include', headers: getAuthHeaders() })
      .then((r) => (r.ok ? r.json() : { sessions: [] }))
      .then((d) => setSessions(d.sessions || [])).catch(() => setSessions([]));
  }, []);

  const openSession = async (s) => {
    setLoadingId(s.id);
    try {
      const r = await fetch(`${API}/ai-guide/sessions/${s.id}/messages`,
        { credentials: 'include', headers: getAuthHeaders() });
      const d = await r.json();
      if (r.ok) onResume(s, d.messages || []);
    } catch { /* silencieux */ }
    setLoadingId(null);
  };

  return (
    <div className="flex-1 overflow-y-auto px-3 py-3 space-y-1.5" data-testid="ai-guide-history">
      <p className="text-[10px] font-bold text-white/45 uppercase tracking-wider pb-1">Conversations passées</p>
      {sessions === null && (
        <p className="text-[11px] text-white/40 flex items-center gap-2"><Loader2 size={12} className="animate-spin" /> Chargement…</p>
      )}
      {sessions?.length === 0 && <p className="text-[11px] text-white/40">Aucune conversation enregistrée pour l'instant.</p>}
      {sessions?.map((s) => (
        <button key={s.id} type="button" onClick={() => openSession(s)} data-testid={`ai-guide-session-${s.id}`}
          className="w-full text-left rounded-xl px-3 py-2 bg-white/[0.05] border border-white/10 hover:border-[#D9B35A]/40 hover:bg-white/[0.08] transition-colors">
          <p className="text-[11.5px] text-white/85 font-semibold flex items-center gap-1.5 truncate">
            {loadingId === s.id ? <Loader2 size={11} className="animate-spin text-[#E9CF8E]" /> : <MessageSquare size={11} className="text-[#E9CF8E] shrink-0" />}
            {s.title || 'Conversation'}
          </p>
          <p className="text-[9.5px] text-white/35 mt-0.5">
            {(s.last_message_at || '').slice(0, 16).replace('T', ' à ')} · {s.messages || 0} message(s) · espace {s.space}
          </p>
        </button>
      ))}
    </div>
  );
};
