import { useEffect, useState, useCallback } from 'react';
import { MailPlus, Send, RotateCcw, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../services/http';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Textarea } from './ui/textarea';

const frDate = (iso) => new Date(iso || Date.now()).toLocaleDateString('fr-FR', {
  weekday: 'long', day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit',
});

export const ContextualMessageDialog = ({ contextType = 'operation', contextRef, defaultEmail = 'contact@objectifscopoutremer.com' }) => {
  const [open, setOpen] = useState(false);
  const [toEmail, setToEmail] = useState(defaultEmail);
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [busy, setBusy] = useState(false);
  const [history, setHistory] = useState([]);
  const label = contextType === 'operation' ? 'Opération' : 'Commande';

  const loadHistory = useCallback(() => {
    fetch(`${API}/messages/contextual?context_ref=${encodeURIComponent(contextRef)}`, { headers: getAuthHeaders() })
      .then((r) => (r.ok ? r.json() : { messages: [] }))
      .then((d) => setHistory(d.messages || []))
      .catch(() => {});
  }, [contextRef]);

  useEffect(() => {
    if (open) {
      setSubject((s) => s || `[${label} ${contextRef}] — `);
      loadHistory();
    }
  }, [open, contextRef, label, loadHistory]);

  const sendMsg = async () => {
    setBusy(true);
    try {
      const res = await fetch(`${API}/messages/contextual`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ to_email: toEmail, subject, body, context_type: contextType, context_ref: contextRef }),
      });
      const d = await res.json();
      if (!res.ok) throw new Error(d.detail || 'Erreur');
      toast.success('Message envoyé ✓');
      setBody('');
      loadHistory();
    } catch (e) {
      toast.error(String(e.message || e));
    } finally {
      setBusy(false);
    }
  };

  const resend = async (m) => {
    setBusy(true);
    try {
      const res = await fetch(`${API}/messages/contextual/${m.id}/resend`, { method: 'POST', headers: getAuthHeaders() });
      if (!res.ok) throw new Error('Renvoi impossible');
      toast.success('Message renvoyé ✓');
      loadHistory();
    } catch (e) {
      toast.error(String(e.message || e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <button type="button" data-testid={`ctx-msg-btn-${contextRef}`}
          className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] font-semibold border border-white/15 text-white/70 hover:text-white hover:bg-white/10 transition-colors">
          <MailPlus className="w-3.5 h-3.5" /> Message
        </button>
      </DialogTrigger>
      <DialogContent className="max-w-lg bg-[#2A1045] border border-white/15 text-white max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-white">Message — {label} {contextRef}</DialogTitle>
        </DialogHeader>
        <p className="text-[11px] text-white/55 m-0" data-testid="ctx-msg-date">
          Jour et date d'envoi : {frDate()}
        </p>
        <div className="space-y-3">
          <div>
            <label className="text-[11px] text-white/60 block mb-1">Adresse email du destinataire</label>
            <Input value={toEmail} onChange={(e) => setToEmail(e.target.value)} data-testid="ctx-msg-email"
              className="bg-white/[0.06] border-white/15 text-white" />
          </div>
          <div>
            <label className="text-[11px] text-white/60 block mb-1">Objet</label>
            <Input value={subject} onChange={(e) => setSubject(e.target.value)} data-testid="ctx-msg-subject"
              className="bg-white/[0.06] border-white/15 text-white" />
          </div>
          <div>
            <label className="text-[11px] text-white/60 block mb-1">Message</label>
            <Textarea value={body} onChange={(e) => setBody(e.target.value)} rows={4} data-testid="ctx-msg-body"
              className="bg-white/[0.06] border-white/15 text-white" />
          </div>
          <Button onClick={sendMsg} disabled={busy || !body.trim()} data-testid="ctx-msg-send"
            className="on-gold w-full bg-[#D9B35A] hover:bg-[#F2D07A] font-semibold">
            {busy ? <Loader2 className="w-4 h-4 mr-1 animate-spin" /> : <Send className="w-4 h-4 mr-1" />} Envoyer
          </Button>
        </div>
        {history.length > 0 && (
          <div className="mt-2">
            <p className="text-[11px] font-semibold text-white/60 uppercase mb-2">Messages envoyés</p>
            <div className="space-y-2">
              {history.map((m) => (
                <div key={m.id} className="flex items-center justify-between gap-2 p-2.5 rounded-xl bg-white/[0.04] border border-white/[0.08]">
                  <div className="text-[11px] min-w-0">
                    <p className="text-white/85 font-semibold truncate m-0">{m.subject}</p>
                    <p className="text-white/50 m-0">
                      À {m.to_email} · {frDate(m.last_sent_at)}
                      {m.resend_count > 0 && <> · renvoyé ×{m.resend_count}</>}
                    </p>
                  </div>
                  <Button size="sm" variant="outline" disabled={busy} onClick={() => resend(m)}
                    data-testid={`ctx-msg-resend-${m.id}`}
                    className="h-7 text-[10px] border-white/20 text-white/80 hover:bg-white/10 shrink-0">
                    <RotateCcw className="w-3 h-3 mr-1" /> Renvoyer
                  </Button>
                </div>
              ))}
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};
