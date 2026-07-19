import { useEffect, useRef, useState } from 'react';
import { Sparkles, Send, Coins, Plus, Loader2, MessageSquare } from 'lucide-react';
import { toast } from 'sonner';
import NavBar from '../components/NavBar';
import { API, getAuthHeaders } from '../services/http';

const uuid = () => (crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`);

export default function AiChatPage() {
  const [settings, setSettings] = useState(null);
  const [balance, setBalance] = useState(0);
  const [sessions, setSessions] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const bottomRef = useRef(null);

  const opts = { headers: getAuthHeaders(), credentials: 'include' };

  useEffect(() => {
    fetch(`${API}/ai-chat/settings`, opts)
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((d) => { setSettings(d); setBalance(d.balance_uc); })
      .catch(() => toast.error('Connectez-vous pour utiliser l\'assistant IA'));
    fetch(`${API}/ai-chat/sessions`, opts)
      .then((r) => (r.ok ? r.json() : { sessions: [] }))
      .then((d) => setSessions(d.sessions || []));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  const cost = (() => {
    if (!settings || !input.trim()) return 0;
    const blocks = Math.ceil(input.trim().length / Math.max(1, settings.block_size_chars));
    return Math.max(settings.min_cost_uc, blocks * settings.credits_per_block);
  })();

  const loadSession = async (sid) => {
    const r = await fetch(`${API}/ai-chat/messages/${sid}`, opts);
    if (!r.ok) return;
    const d = await r.json();
    setSessionId(sid);
    setMessages(d.messages.map((m) => ({ role: m.role, content: m.content, cost: m.cost_uc })));
  };

  const newConversation = () => { setSessionId(null); setMessages([]); };

  const send = async () => {
    const question = input.trim();
    if (!question || streaming) return;
    if (balance < cost) {
      toast.error(`Crédits insuffisants : ${cost} UC requis, solde ${balance} UC`);
      return;
    }
    setInput('');
    setStreaming(true);
    setMessages((m) => [...m, { role: 'user', content: question, cost }, { role: 'assistant', content: '' }]);
    try {
      const r = await fetch(`${API}/ai-chat/ask`, {
        method: 'POST', ...opts,
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, session_id: sessionId }),
      });
      if (!r.ok) {
        const d = await r.json().catch(() => ({}));
        throw new Error(d.detail || 'Erreur assistant');
      }
      const reader = r.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split('\n\n');
        buffer = parts.pop();
        for (const part of parts) {
          if (!part.startsWith('data: ')) continue;
          const ev = JSON.parse(part.slice(6));
          if (ev.type === 'delta') {
            setMessages((m) => {
              const copy = [...m];
              copy[copy.length - 1] = { ...copy[copy.length - 1], content: copy[copy.length - 1].content + ev.content };
              return copy;
            });
          } else if (ev.type === 'done') {
            setBalance(ev.balance_uc);
            if (!sessionId) setSessionId(ev.session_id);
            fetch(`${API}/ai-chat/sessions`, opts).then((x) => x.json()).then((d) => setSessions(d.sessions || []));
          } else if (ev.type === 'error') {
            setBalance(ev.balance_uc);
            toast.error(ev.detail);
            setMessages((m) => m.slice(0, -2));
          }
        }
      }
    } catch (e) {
      toast.error(e.message);
      setMessages((m) => m.slice(0, -2));
    } finally {
      setStreaming(false);
    }
  };

  const name = settings?.assistant_name || 'Assistant IA';

  return (
    <div className="min-h-screen" data-testid="ai-chat-page">
      <NavBar />
      <div className="max-w-6xl mx-auto px-4 pt-28 pb-10 grid grid-cols-1 lg:grid-cols-[260px_1fr] gap-5">
        <aside className="glass-panel-soft rounded-2xl p-4 h-fit lg:sticky lg:top-24">
          <button
            type="button"
            onClick={newConversation}
            data-testid="ai-chat-new-conversation-btn"
            className="w-full mb-4 inline-flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl text-sm font-bold"
            style={{ background: 'linear-gradient(135deg, #D9B35A 0%, #b8933e 100%)', color: '#1F0A33' }}
          >
            <Plus className="w-4 h-4" /> Nouvelle conversation
          </button>
          <p className="text-[11px] uppercase tracking-wider text-white/45 mb-2">Mes conversations</p>
          <div className="space-y-1 max-h-80 overflow-y-auto" data-testid="ai-chat-sessions-list">
            {sessions.length === 0 && <p className="text-xs text-white/40">Aucune conversation.</p>}
            {sessions.map((s) => (
              <button
                key={s.id} type="button" onClick={() => loadSession(s.id)}
                className={`w-full text-left px-2.5 py-2 rounded-lg text-xs transition-colors ${
                  s.id === sessionId ? 'bg-[#D9B35A]/15 text-[#E9CF8E]' : 'text-white/70 hover:bg-white/5'
                }`}
              >
                <span className="flex items-center gap-1.5">
                  <MessageSquare className="w-3 h-3 shrink-0" />
                  <span className="truncate">{s.title || 'Conversation'}</span>
                </span>
              </button>
            ))}
          </div>
        </aside>

        <main className="glass-panel rounded-[26px] flex flex-col" style={{ minHeight: '70vh' }}>
          <div className="flex items-center justify-between px-5 py-4 border-b border-white/10">
            <div className="flex items-center gap-2.5">
              <span className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: 'rgba(217,179,90,0.15)' }}>
                <Sparkles className="w-4.5 h-4.5 text-[#D9B35A]" style={{ width: 18, height: 18 }} />
              </span>
              <div>
                <h1 className="text-base font-bold text-white leading-tight">{name}</h1>
                <p className="text-[11px] text-white/50">
                  {settings ? `${settings.credits_per_block} crédit(s) par tranche de ${settings.block_size_chars} caractères` : '…'}
                </p>
              </div>
            </div>
            <span
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold"
              style={{ background: 'rgba(217,179,90,0.14)', color: '#E9CF8E', border: '1px solid rgba(217,179,90,0.4)' }}
              data-testid="ai-chat-balance"
            >
              <Coins className="w-3.5 h-3.5" /> {balance} UC
            </span>
          </div>

          <div className="flex-1 overflow-y-auto px-5 py-5 space-y-4" data-testid="ai-chat-messages">
            {messages.length === 0 && (
              <div className="text-center py-14">
                <Sparkles className="w-10 h-10 mx-auto text-[#D9B35A]/50 mb-3" />
                <p className="text-white/70 text-sm">Posez votre question sur la centrale, les adhésions, la logistique…</p>
                <p className="text-white/40 text-xs mt-1.5">Chaque question est débitée de votre CREDI'SCOP selon sa longueur.</p>
              </div>
            )}
            {messages.map((m, i) => (
              <div key={`${i}-${m.role}`} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div
                  className={`max-w-[80%] px-4 py-2.5 rounded-2xl text-sm whitespace-pre-wrap leading-relaxed ${
                    m.role === 'user' ? 'text-[#1F0A33] font-medium' : 'text-white/90'
                  }`}
                  style={m.role === 'user'
                    ? { background: 'linear-gradient(135deg, #E9CF8E 0%, #D9B35A 100%)' }
                    : { background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(217,179,90,0.2)' }}
                >
                  {m.content || (streaming && i === messages.length - 1 ? <Loader2 className="w-4 h-4 animate-spin text-[#D9B35A]" /> : '')}
                  {m.role === 'user' && m.cost > 0 && (
                    <span className="block text-right text-[10px] mt-1 opacity-70">−{m.cost} UC</span>
                  )}
                </div>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>

          <div className="px-5 py-4 border-t border-white/10">
            {settings && !settings.enabled && (
              <p className="text-xs text-amber-300/90 mb-2">L'assistant est momentanément désactivé par l'administration.</p>
            )}
            <div className="flex items-end gap-2">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }}
                maxLength={settings?.max_question_chars || 1000}
                rows={2}
                placeholder="Votre question…"
                data-testid="ai-chat-input"
                className="flex-1 resize-none rounded-xl px-3.5 py-2.5 text-sm text-white placeholder-white/35 focus:outline-none focus:ring-1 focus:ring-[#D9B35A]/60"
                style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(217,179,90,0.25)' }}
                disabled={streaming || (settings && !settings.enabled)}
              />
              <button
                type="button"
                onClick={send}
                disabled={streaming || !input.trim() || (settings && !settings.enabled)}
                data-testid="ai-chat-send-btn"
                className="h-11 px-4 rounded-xl inline-flex items-center gap-2 text-sm font-bold disabled:opacity-40"
                style={{ background: 'linear-gradient(135deg, #D9B35A 0%, #b8933e 100%)', color: '#1F0A33' }}
              >
                {streaming ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              </button>
            </div>
            <p className="text-[11px] mt-1.5" data-testid="ai-chat-cost-preview" style={{ color: cost > balance ? '#FCA5A5' : 'rgba(255,255,255,0.5)' }}>
              {input.trim()
                ? `${input.trim().length} caractères — coût : ${cost} UC ${cost > balance ? '(solde insuffisant)' : ''}`
                : 'Le coût est calculé selon la longueur de votre question.'}
            </p>
          </div>
        </main>
      </div>
    </div>
  );
}
