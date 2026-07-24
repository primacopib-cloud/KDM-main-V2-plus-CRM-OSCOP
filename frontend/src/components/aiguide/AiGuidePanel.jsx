import { useEffect, useRef, useState } from 'react';
import { Send, Sparkles, Loader2 } from 'lucide-react';
import { API, getAuthHeaders } from '../../services/http';

export const AiGuidePanel = ({ welcome, space, onClose }) => {
  const [messages, setMessages] = useState([{ role: 'assistant', content: welcome.greeting }]);
  const [suggestions, setSuggestions] = useState(welcome.suggestions || []);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [sessionId, setSessionId] = useState(sessionStorage.getItem(`guidia_session_${space}`) || null);
  const endRef = useRef(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, busy]);

  const send = async (text) => {
    const message = (text || input).trim();
    if (!message || busy) return;
    setInput('');
    setSuggestions([]);
    setMessages((m) => [...m, { role: 'user', content: message }]);
    setBusy(true);
    try {
      const r = await fetch(`${API}/ai-guide/chat`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ message, session_id: sessionId, space }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Réponse indisponible');
      setSessionId(d.session_id);
      sessionStorage.setItem(`guidia_session_${space}`, d.session_id);
      setMessages((m) => [...m, { role: 'assistant', content: d.answer.replace(/\*\*/g, '') }]);
      setSuggestions(d.suggestions || []);
    } catch (e) {
      setMessages((m) => [...m, { role: 'assistant', content: `⚠ ${e.message}` }]);
    }
    setBusy(false);
  };

  return (
    <div className="fixed bottom-24 right-6 z-[70] w-[370px] max-w-[calc(100vw-2rem)] rounded-2xl overflow-hidden flex flex-col"
      data-testid="ai-guide-panel"
      style={{
        height: 'min(540px, calc(100vh - 8rem))',
        background: 'linear-gradient(180deg, rgba(42,16,69,0.96) 0%, rgba(30,12,52,0.98) 100%)',
        border: '1px solid rgba(217,179,90,0.4)',
        boxShadow: '0 24px 60px rgba(0,0,0,0.55), 0 0 30px rgba(217,179,90,0.12)',
        backdropFilter: 'blur(18px)',
      }}>
      <div className="px-4 py-3 flex items-center gap-2.5"
        style={{ background: 'linear-gradient(90deg, rgba(69,31,107,0.9), rgba(184,134,11,0.25))', borderBottom: '1px solid rgba(217,179,90,0.3)' }}>
        <span className="w-8 h-8 rounded-full flex items-center justify-center"
          style={{ background: 'rgba(217,179,90,0.18)', border: '1px solid rgba(217,179,90,0.5)' }}>
          <Sparkles size={15} className="text-[#E9CF8E]" />
        </span>
        <span>
          <p className="text-[13px] font-bold text-[#E9CF8E] leading-tight">GUID'IA</p>
          <p className="text-[9.5px] text-white/45 leading-tight">Votre copilote Communityplace — gratuit</p>
        </span>
        <button type="button" onClick={onClose} data-testid="ai-guide-close"
          className="ml-auto text-white/40 hover:text-white text-lg leading-none px-1">×</button>
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-2.5" data-testid="ai-guide-messages">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] rounded-2xl px-3 py-2 text-[12px] leading-relaxed whitespace-pre-wrap ${
              m.role === 'user'
                ? 'bg-[#D9B35A]/20 text-[#F3EDE4] border border-[#D9B35A]/30 rounded-br-sm'
                : 'bg-white/[0.06] text-white/85 border border-white/10 rounded-bl-sm'}`}>
              {m.content}
            </div>
          </div>
        ))}
        {busy && (
          <div className="flex items-center gap-2 text-white/40 text-[11px] pl-1">
            <Loader2 size={12} className="animate-spin text-[#E9CF8E]" /> GUID'IA réfléchit…
          </div>
        )}
        {!busy && suggestions.length > 0 && (
          <div className="flex flex-wrap gap-1.5 pt-1" data-testid="ai-guide-suggestions">
            {suggestions.map((s, i) => (
              <button key={i} type="button" onClick={() => send(s)} data-testid={`ai-guide-suggestion-${i}`}
                className="px-2.5 py-1.5 rounded-full text-[10.5px] text-left text-[#E9CF8E] bg-[#D9B35A]/10 border border-[#D9B35A]/30 hover:bg-[#D9B35A]/25 transition-colors">
                {s}
              </button>
            ))}
          </div>
        )}
        <div ref={endRef} />
      </div>

      <div className="p-2.5 flex items-center gap-2" style={{ borderTop: '1px solid rgba(217,179,90,0.25)' }}>
        <input value={input} onChange={(e) => setInput(e.target.value)} data-testid="ai-guide-input"
          onKeyDown={(e) => e.key === 'Enter' && send()}
          placeholder="Posez votre question…" maxLength={800}
          className="flex-1 h-9 px-3 rounded-xl bg-white/[0.06] border border-white/15 text-[12px] text-white placeholder:text-white/30 outline-none focus:border-[#D9B35A]/50" />
        <button type="button" onClick={() => send()} disabled={busy || !input.trim()} data-testid="ai-guide-send"
          className="w-9 h-9 rounded-xl flex items-center justify-center bg-[#D9B35A]/20 border border-[#D9B35A]/40 text-[#E9CF8E] hover:bg-[#D9B35A]/35 disabled:opacity-40 transition-colors">
          <Send size={14} />
        </button>
      </div>
    </div>
  );
};
