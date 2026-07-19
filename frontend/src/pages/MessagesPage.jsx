import { useCallback, useEffect, useState } from 'react';
import { Inbox, Send, Mail, MailOpen, PenSquare, Loader2, X } from 'lucide-react';
import { toast } from 'sonner';
import NavBar from '../components/NavBar';
import { API } from '../services/http';

const fmtDT = (iso) => new Date(iso).toLocaleString('fr-FR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
const opts = { credentials: 'include' };

const ComposeModal = ({ replyTo, onClose, onSent }) => {
  const [directory, setDirectory] = useState([]);
  const [form, setForm] = useState({ to_user_id: replyTo?.from_user_id || '', subject: replyTo ? `Re: ${replyTo.subject}` : '', body: '' });
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetch(`${API}/messages/directory`, opts).then((r) => r.json()).then((d) => setDirectory(d.users || [])).catch(() => {});
  }, []);

  const send = async () => {
    if (!form.to_user_id || !form.subject || !form.body) return toast.error('Destinataire, objet et message requis');
    setBusy(true);
    try {
      const r = await fetch(`${API}/messages`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, ...opts,
        body: JSON.stringify({ ...form, reply_to: replyTo?.id || null }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Erreur');
      toast.success('Message envoyé');
      onSent();
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: 'rgba(15,5,25,0.75)' }} data-testid="compose-modal">
      <div className="w-full max-w-lg rounded-[18px] p-5" style={{ background: '#2A1045', border: '1px solid rgba(217,179,90,0.3)' }}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-bold text-white">Nouveau message</h3>
          <button type="button" onClick={onClose} className="text-white/50 hover:text-white"><X className="w-4 h-4" /></button>
        </div>
        <div className="space-y-3">
          <select value={form.to_user_id} onChange={(e) => setForm({ ...form, to_user_id: e.target.value })}
            data-testid="compose-recipient" className="w-full h-10 rounded-lg px-2.5 text-xs text-white bg-white/[0.05] border border-white/15" style={{ colorScheme: 'dark' }}>
            <option value="" style={{ background: '#2A1045' }}>— Choisir un destinataire —</option>
            {directory.map((u) => <option key={u.id} value={u.id} style={{ background: '#2A1045' }}>{u.label}</option>)}
          </select>
          <input value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} placeholder="Objet"
            data-testid="compose-subject" className="w-full h-10 rounded-lg px-2.5 text-xs text-white bg-white/[0.05] border border-white/15" />
          <textarea rows={6} value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} placeholder="Votre message…"
            data-testid="compose-body" className="w-full rounded-lg px-2.5 py-2 text-xs text-white bg-white/[0.05] border border-white/15" />
          <button type="button" onClick={send} disabled={busy} data-testid="compose-send-btn"
            className="w-full py-2.5 rounded-xl text-xs font-bold inline-flex items-center justify-center gap-2 disabled:opacity-50"
            style={{ background: 'linear-gradient(135deg, #D9B35A 0%, #b8933e 100%)', color: '#1F0A33' }}>
            {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />} Envoyer
          </button>
        </div>
      </div>
    </div>
  );
};

export default function MessagesPage() {
  const [tab, setTab] = useState('inbox');
  const [items, setItems] = useState([]);
  const [selected, setSelected] = useState(null);
  const [compose, setCompose] = useState(null); // null | 'new' | message(reply)
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    fetch(`${API}/messages/${tab}`, opts)
      .then((r) => (r.ok ? r.json() : { items: [] }))
      .then((d) => setItems(d.items || []))
      .finally(() => setLoading(false));
  }, [tab]);

  useEffect(() => { load(); setSelected(null); }, [load]);

  const open = (m) => {
    setSelected(m);
    if (tab === 'inbox' && !m.read) {
      fetch(`${API}/messages/${m.id}/read`, { method: 'POST', ...opts });
      setItems(items.map((x) => (x.id === m.id ? { ...x, read: true } : x)));
    }
  };

  return (
    <div className="min-h-screen" data-testid="messages-page">
      <NavBar />
      <div className="max-w-4xl mx-auto px-4 pt-28 pb-16">
        <div className="flex items-center justify-between mb-5">
          <h1 className="text-2xl font-bold text-white" style={{ fontFamily: '"Playfair Display", serif' }}>
            Messagerie <span className="text-[#D9B35A]">interne</span>
          </h1>
          <button type="button" onClick={() => setCompose('new')} data-testid="messages-compose-btn"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold"
            style={{ background: 'linear-gradient(135deg, #D9B35A 0%, #b8933e 100%)', color: '#1F0A33' }}>
            <PenSquare className="w-3.5 h-3.5" /> Nouveau message
          </button>
        </div>
        <div className="flex gap-2 mb-4">
          {[{ k: 'inbox', label: 'Reçus', icon: Inbox }, { k: 'sent', label: 'Envoyés', icon: Send }].map((tb) => (
            <button key={tb.k} type="button" onClick={() => setTab(tb.k)} data-testid={`messages-tab-${tb.k}`}
              className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-bold transition-colors ${
                tab === tb.k ? 'bg-[#D9B35A] text-[#1F0A33]' : 'bg-white/10 text-white/60'
              }`}>
              <tb.icon className="w-3.5 h-3.5" /> {tb.label}
            </button>
          ))}
        </div>
        <div className="grid md:grid-cols-2 gap-4">
          <div className="glass-panel rounded-[18px] p-3 space-y-1.5 max-h-[520px] overflow-y-auto" data-testid="messages-list">
            {loading ? <Loader2 className="w-5 h-5 animate-spin text-[#D9B35A] mx-auto my-8" />
              : !items.length ? <p className="text-xs text-white/45 text-center py-8">Aucun message.</p>
              : items.map((m) => (
                <button key={m.id} type="button" onClick={() => open(m)} data-testid={`message-row-${m.id}`}
                  className={`w-full text-left p-3 rounded-xl border transition-colors ${
                    selected?.id === m.id ? 'border-[#D9B35A] bg-[#D9B35A]/10' : 'border-white/10 hover:border-white/25'
                  }`}>
                  <div className="flex items-center gap-2">
                    {tab === 'inbox' && !m.read ? <Mail className="w-3.5 h-3.5 text-[#D9B35A] shrink-0" /> : <MailOpen className="w-3.5 h-3.5 text-white/35 shrink-0" />}
                    <span className={`text-xs truncate ${tab === 'inbox' && !m.read ? 'font-bold text-white' : 'text-white/75'}`}>{m.subject}</span>
                  </div>
                  <p className="text-[10.5px] text-white/45 mt-0.5">
                    {tab === 'inbox' ? `De : ${m.from_label}` : `À : ${m.to_label}`} · {fmtDT(m.created_at)}
                  </p>
                </button>
              ))}
          </div>
          <div className="glass-panel rounded-[18px] p-4" data-testid="message-detail">
            {!selected ? <p className="text-xs text-white/40 text-center py-10">Sélectionnez un message.</p> : (
              <>
                <h3 className="text-sm font-bold text-white mb-1">{selected.subject}</h3>
                <p className="text-[10.5px] text-white/45 mb-3">
                  De : {selected.from_label} · À : {selected.to_label} · {fmtDT(selected.created_at)}
                </p>
                <p className="text-xs text-white/80 whitespace-pre-wrap leading-relaxed">{selected.body}</p>
                {tab === 'inbox' && (
                  <button type="button" onClick={() => setCompose(selected)} data-testid="message-reply-btn"
                    className="mt-4 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold bg-white/10 text-[#E9CF8E] hover:bg-white/15">
                    <Send className="w-3 h-3" /> Répondre
                  </button>
                )}
              </>
            )}
          </div>
        </div>
      </div>
      {compose && (
        <ComposeModal replyTo={compose === 'new' ? null : compose} onClose={() => setCompose(null)}
          onSent={() => { setCompose(null); if (tab === 'sent') load(); }} />
      )}
    </div>
  );
}
