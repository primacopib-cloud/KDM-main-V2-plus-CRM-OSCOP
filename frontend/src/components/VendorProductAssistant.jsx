import { useEffect, useRef, useState } from 'react';
import { Sparkles, Send, X, Loader2 } from 'lucide-react';
import { API, getAuthHeaders } from '../services/http';

export const VendorProductAssistant = () => {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const bottomRef = useRef(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, open]);

  const send = async (text) => {
    const question = (text || input).trim();
    if (!question || busy) return;
    setInput('');
    setBusy(true);
    setMessages((m) => [...m, { role: 'user', content: question }]);
    try {
      const r = await fetch(`${API}/vendor-onboarding/assistant`, {
        method: 'POST', credentials: 'include',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, session_id: sessionId }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Assistant indisponible');
      setSessionId(d.session_id);
      setMessages((m) => [...m, { role: 'assistant', content: d.answer }]);
    } catch (e) {
      setMessages((m) => [...m, { role: 'assistant', content: `⚠ ${e.message}` }]);
    } finally { setBusy(false); }
  };

  return (
    <>
      <button type="button" onClick={() => setOpen(!open)} data-testid="product-assistant-fab"
        className="fixed bottom-5 right-5 z-40 inline-flex items-center gap-2 px-4 py-3 rounded-full text-sm font-bold shadow-2xl hover:brightness-110 transition-all"
        style={{ background: 'linear-gradient(135deg, #D9B35A 0%, #b8933e 100%)', color: '#1F0A33' }}>
        <Sparkles className="w-4 h-4" /> Assistant produits <span className="text-[10px] font-black px-1.5 py-0.5 rounded-full bg-[#1F0A33]/15">GRATUIT</span>
      </button>
      {open && (
        <div className="fixed bottom-20 right-5 z-40 w-[360px] max-w-[92vw] rounded-2xl overflow-hidden shadow-2xl border border-[#D9B35A]/35 flex flex-col"
          style={{ background: 'linear-gradient(180deg, #2A1045, #1F0A33)', height: 460 }} data-testid="product-assistant-panel">
          <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
            <span className="flex items-center gap-2 text-sm font-bold text-white"><Sparkles className="w-4 h-4 text-[#D9B35A]" /> COOP'IA — Soumettre vos produits</span>
            <button type="button" onClick={() => setOpen(false)} className="text-white/50 hover:text-white" data-testid="product-assistant-close"><X className="w-4 h-4" /></button>
          </div>
          <div className="flex-1 overflow-y-auto px-3.5 py-3 space-y-2.5">
            {messages.length === 0 && (
              <div className="space-y-2">
                <p className="text-xs text-white/60">Je vous guide gratuitement, pas à pas, pour proposer vos produits. Essayez :</p>
                {['Comment soumettre mon premier produit ?', 'Quelles infos préparer pour un produit frais ?', 'Comment suivre la validation de mes produits ?'].map((q) => (
                  <button key={q} type="button" onClick={() => send(q)}
                    className="block w-full text-left px-3 py-2 rounded-lg text-xs text-[#E9CF8E] border border-[#D9B35A]/30 hover:bg-[#D9B35A]/10">{q}</button>
                ))}
              </div>
            )}
            {messages.map((m, i) => (
              <div key={`${i}-${m.role}`} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[85%] px-3 py-2 rounded-xl text-xs whitespace-pre-wrap leading-relaxed ${m.role === 'user' ? 'text-[#1F0A33] font-medium' : 'text-white/90'}`}
                  style={m.role === 'user' ? { background: '#E9CF8E' } : { background: 'rgba(255,255,255,0.07)' }}>
                  {m.content}
                </div>
              </div>
            ))}
            {busy && <Loader2 className="w-4 h-4 animate-spin text-[#D9B35A]" />}
            <div ref={bottomRef} />
          </div>
          <div className="p-2.5 border-t border-white/10 flex gap-2">
            <input value={input} onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && send()}
              placeholder="Votre question…" data-testid="product-assistant-input"
              className="flex-1 h-10 rounded-lg px-3 text-xs text-white placeholder-white/35 bg-white/[0.06] border border-[#D9B35A]/25 focus:outline-none" />
            <button type="button" onClick={() => send()} disabled={busy} data-testid="product-assistant-send"
              className="h-10 w-10 rounded-lg inline-flex items-center justify-center disabled:opacity-40"
              style={{ background: '#D4AF37', color: '#1F0A33' }}><Send className="w-4 h-4" /></button>
          </div>
        </div>
      )}
    </>
  );
};
