import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Mail, Send, ExternalLink } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

export const MessagesNavLink = ({ variant = 'dark' }) => {
  const [unread, setUnread] = useState(0);
  const [open, setOpen] = useState(false);
  const [inbox, setInbox] = useState([]);
  const [replyTo, setReplyTo] = useState(null);
  const [reply, setReply] = useState('');
  const ref = useRef(null);
  const light = variant === 'light';

  const loadCount = useCallback(() => {
    fetch(`${API}/api/messages/unread-count`, { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : { unread: 0 }))
      .then((d) => setUnread(d.unread || 0))
      .catch(() => {});
  }, []);

  useEffect(() => {
    loadCount();
    const id = setInterval(loadCount, 60000);
    return () => clearInterval(id);
  }, [loadCount]);

  useEffect(() => {
    const close = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', close);
    return () => document.removeEventListener('mousedown', close);
  }, []);

  const toggle = () => {
    const next = !open;
    setOpen(next);
    if (next) {
      fetch(`${API}/api/messages/inbox`, { credentials: 'include' })
        .then((r) => (r.ok ? r.json() : { items: [] }))
        .then((d) => setInbox((d.items || []).slice(0, 5)))
        .catch(() => {});
    }
  };

  const openMsg = async (m) => {
    setReplyTo(replyTo?.id === m.id ? null : m);
    setReply('');
    if (!m.read) {
      await fetch(`${API}/api/messages/${m.id}/read`, { method: 'POST', credentials: 'include' }).catch(() => {});
      setInbox((list) => list.map((x) => (x.id === m.id ? { ...x, read: true } : x)));
      loadCount();
    }
  };

  const sendReply = async () => {
    if (!reply.trim()) return;
    const r = await fetch(`${API}/api/messages`, {
      method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ to_user_id: replyTo.from_user_id, subject: `Re: ${replyTo.subject}`, body: reply.trim() }),
    });
    if (!r.ok) return toast.error('Envoi impossible');
    toast.success('Réponse envoyée');
    setReply('');
    setReplyTo(null);
  };

  return (
    <div className="relative" ref={ref}>
      <button type="button" onClick={toggle} title="Messagerie interne"
        className={`relative p-2 rounded-lg transition-colors ${light ? 'hover:bg-gray-100' : 'hover:bg-white/[0.06]'}`}
        data-testid="messages-nav-link">
        <Mail className={`w-4 h-4 ${light ? 'text-gray-500' : 'text-white/70'}`} />
        {unread > 0 && (
          <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-[#D9B35A] text-[#1F0A33] rounded-full text-[10px] font-bold flex items-center justify-center"
            data-testid="messages-unread-badge">
            {unread > 9 ? '9+' : unread}
          </span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 top-full mt-2 w-[340px] rounded-2xl z-50 overflow-hidden shadow-2xl"
          style={{ background: '#2A1045', border: '1px solid rgba(217,179,90,0.35)' }} data-testid="messages-popover">
          <div className="flex items-center justify-between px-4 py-2.5 border-b border-white/10">
            <p className="text-xs font-bold text-white">Messages récents</p>
            <Link to="/messages" onClick={() => setOpen(false)} className="text-[10px] text-[#E9CF8E] hover:underline inline-flex items-center gap-1" data-testid="messages-popover-open-full">
              Ouvrir la messagerie <ExternalLink className="w-3 h-3" />
            </Link>
          </div>
          <div className="max-h-[320px] overflow-y-auto">
            {!inbox.length && <p className="text-xs text-white/40 px-4 py-6 text-center">Aucun message reçu.</p>}
            {inbox.map((m) => (
              <div key={m.id} className="border-b border-white/5 last:border-0">
                <button type="button" onClick={() => openMsg(m)} className="w-full text-left px-4 py-2.5 hover:bg-white/[0.04]" data-testid={`popover-msg-${m.id}`}>
                  <div className="flex items-center gap-2">
                    {!m.read && <span className="w-1.5 h-1.5 rounded-full bg-[#D9B35A] shrink-0" />}
                    <span className={`text-xs flex-1 truncate ${m.read ? 'text-white/60' : 'text-white font-semibold'}`}>{m.subject}</span>
                    <span className="text-[9px] text-white/35 shrink-0">{String(m.created_at).slice(5, 16).replace('T', ' ')}</span>
                  </div>
                  <p className="text-[10px] text-white/40 truncate mt-0.5">{m.from_label} — {m.body}</p>
                </button>
                {replyTo?.id === m.id && (
                  <div className="px-4 pb-3 space-y-1.5">
                    <p className="text-[10px] text-white/55 whitespace-pre-wrap max-h-24 overflow-y-auto">{m.body}</p>
                    <div className="flex gap-1.5">
                      <input className="flex-1 h-8 rounded-lg px-2.5 text-xs text-white bg-white/[0.06] border border-white/15"
                        placeholder="Répondre…" value={reply} onChange={(e) => setReply(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && sendReply()} data-testid="popover-reply-input" />
                      <button type="button" onClick={sendReply} className="px-2.5 rounded-lg" style={{ background: '#D9B35A' }} data-testid="popover-reply-send">
                        <Send className="w-3.5 h-3.5 text-[#1F0A33]" />
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
