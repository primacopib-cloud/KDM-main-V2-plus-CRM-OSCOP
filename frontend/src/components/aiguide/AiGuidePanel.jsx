import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Send, Sparkles, Loader2, Mic, Volume2, VolumeX, History, ArrowRight, ArrowLeft, Compass, AudioLines } from 'lucide-react';
import { API, getAuthHeaders } from '../../services/http';
import { AiGuideHistory } from './AiGuideHistory';

const SR = typeof window !== 'undefined' && (window.SpeechRecognition || window.webkitSpeechRecognition);

export const AiGuidePanel = ({ welcome, space, lang = 'fr', bootTip = null,
  tourAvailable = false, onStartTour, onClose }) => {
  const navigate = useNavigate();
  const [messages, setMessages] = useState([{ role: 'assistant', content: welcome.greeting }]);
  const [suggestions, setSuggestions] = useState(welcome.suggestions || []);
  const [actions, setActions] = useState([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [listening, setListening] = useState(false);
  const [speak, setSpeak] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [sessionId, setSessionId] = useState(sessionStorage.getItem(`guidia_session_${space}`) || null);
  const [voice, setVoice] = useState(null);
  const [voices, setVoices] = useState([]);
  const [showVoices, setShowVoices] = useState(false);

  useEffect(() => {
    fetch(`${API}/ai-guide/voice`, { credentials: 'include', headers: getAuthHeaders() })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => { if (d) { setVoice(d.voice); setVoices(d.voices || []); } }).catch(() => {});
  }, []);

  const saveVoice = async (v) => {
    setVoice(v);
    setShowVoices(false);
    try {
      await fetch(`${API}/ai-guide/voice`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ voice: v }),
      });
      readAloud(`Bonjour, je suis la voix ${v}.`);
    } catch { /* silencieux */ }
  };
  const endRef = useRef(null);
  const recRef = useRef(null);
  const lastTipAt = useRef(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, busy]);
  useEffect(() => () => { window.speechSynthesis?.cancel(); audioRef.current?.pause(); }, []);

  useEffect(() => {
    if (!bootTip?.tip || bootTip.at === lastTipAt.current) return;
    lastTipAt.current = bootTip.at;
    setMessages((m) => [...m, { role: 'assistant', content: bootTip.tip }]);
    if (bootTip.suggestions?.length) setSuggestions(bootTip.suggestions);
    if (speak) readAloud(bootTip.tip);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bootTip?.at]);

  const audioRef = useRef(null);

  const readAloud = async (text) => {
    try {
      audioRef.current?.pause();
      const r = await fetch(`${API}/ai-guide/tts`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ text: text.slice(0, 900) }),
      });
      if (!r.ok) throw new Error('tts');
      const url = URL.createObjectURL(await r.blob());
      const audio = new Audio(url);
      audioRef.current = audio;
      audio.onended = () => URL.revokeObjectURL(url);
      await audio.play();
    } catch {
      if (!window.speechSynthesis) return;
      window.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(text);
      u.lang = 'fr-FR';
      u.rate = 1.05;
      window.speechSynthesis.speak(u);
    }
  };

  const dictate = () => {
    if (!SR) return;
    if (listening) { recRef.current?.stop(); return; }
    const rec = new SR();
    recRef.current = rec;
    rec.lang = 'fr-FR';
    rec.interimResults = false;
    rec.onresult = (e) => {
      const text = e.results[0][0].transcript;
      setInput(text);
      setListening(false);
      send(text);
    };
    rec.onend = () => setListening(false);
    rec.onerror = () => setListening(false);
    setListening(true);
    rec.start();
  };

  const send = async (text) => {
    const message = (text || input).trim();
    if (!message || busy) return;
    setInput('');
    setSuggestions([]);
    setActions([]);
    setMessages((m) => [...m, { role: 'user', content: message }]);
    setBusy(true);
    try {
      const r = await fetch(`${API}/ai-guide/chat`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ message, session_id: sessionId, space, lang }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Réponse indisponible');
      setSessionId(d.session_id);
      sessionStorage.setItem(`guidia_session_${space}`, d.session_id);
      const answer = d.answer.replace(/\*\*/g, '');
      setMessages((m) => [...m, { role: 'assistant', content: answer }]);
      setSuggestions(d.suggestions || []);
      setActions(d.actions || []);
      if (speak) readAloud(answer);
    } catch (e) {
      setMessages((m) => [...m, { role: 'assistant', content: `⚠ ${e.message}` }]);
    }
    setBusy(false);
  };

  const resumeSession = (session, msgs) => {
    setSessionId(session.id);
    sessionStorage.setItem(`guidia_session_${space}`, session.id);
    setMessages(msgs.map((m) => ({ role: m.role, content: m.content })));
    setSuggestions([]);
    setActions([]);
    setShowHistory(false);
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
          <p className="text-[13px] font-bold text-[#E9CF8E] leading-tight">Oracle</p>
          <p className="text-[9.5px] text-white/45 leading-tight">Votre copilote Communityplace — gratuit</p>
        </span>
        <span className="ml-auto flex items-center gap-1">
          <button type="button" data-testid="ai-guide-history-btn" title="Conversations passées"
            onClick={() => setShowHistory(!showHistory)}
            className={`p-1.5 rounded-lg transition-colors ${showHistory ? 'text-[#E9CF8E] bg-[#D9B35A]/15' : 'text-white/40 hover:text-white'}`}>
            {showHistory ? <ArrowLeft size={14} /> : <History size={14} />}
          </button>
          <button type="button" data-testid="ai-guide-tts-toggle" title={speak ? 'Couper la lecture audio' : 'Lire les réponses à voix haute'}
            onClick={() => { setSpeak(!speak); if (speak) { window.speechSynthesis?.cancel(); audioRef.current?.pause(); } }}
            className={`p-1.5 rounded-lg transition-colors ${speak ? 'text-[#E9CF8E] bg-[#D9B35A]/15' : 'text-white/40 hover:text-white'}`}>
            {speak ? <Volume2 size={14} /> : <VolumeX size={14} />}
          </button>
          {voices.length > 0 && (
            <span className="relative">
              <button type="button" data-testid="ai-guide-voice-btn" title="Choisir ma voix Oracle"
                onClick={() => setShowVoices(!showVoices)}
                className={`p-1.5 rounded-lg transition-colors ${showVoices ? 'text-[#E9CF8E] bg-[#D9B35A]/15' : 'text-white/40 hover:text-white'}`}>
                <AudioLines size={14} />
              </button>
              {showVoices && (
                <span className="absolute right-0 top-8 z-10 w-32 rounded-xl p-1.5 flex flex-col gap-0.5"
                  data-testid="ai-guide-voice-menu"
                  style={{ background: 'rgba(30,12,52,0.98)', border: '1px solid rgba(217,179,90,0.4)' }}>
                  {voices.map((v) => (
                    <button key={v} type="button" onClick={() => saveVoice(v)} data-testid={`voice-${v}`}
                      className={`px-2 py-1 rounded-lg text-left text-[11px] capitalize transition-colors ${
                        v === voice ? 'bg-[#D9B35A]/25 text-[#E9CF8E] font-bold' : 'text-white/60 hover:text-white hover:bg-white/[0.06]'}`}>
                      {v}
                    </button>
                  ))}
                </span>
              )}
            </span>
          )}
          <button type="button" onClick={onClose} data-testid="ai-guide-close"
            className="text-white/40 hover:text-white text-lg leading-none px-1">×</button>
        </span>
      </div>

      {showHistory ? (
        <AiGuideHistory onResume={resumeSession} />
      ) : (
        <>
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
                <Loader2 size={12} className="animate-spin text-[#E9CF8E]" /> Oracle réfléchit…
              </div>
            )}
            {!busy && tourAvailable && (
              <button type="button" onClick={onStartTour} data-testid="ai-guide-start-tour"
                className="w-full rounded-xl px-3 py-2.5 text-left text-[12px] font-bold text-[#2A1045] flex items-center gap-2 transition-transform hover:scale-[1.01]"
                style={{ background: 'linear-gradient(90deg, #E9CF8E, #D9B35A)' }}>
                <Compass size={15} /> Nouveau ici ? Lancez la visite guidée de votre espace
              </button>
            )}
            {!busy && actions.length > 0 && (
              <div className="flex flex-wrap gap-1.5 pt-0.5" data-testid="ai-guide-actions">
                {actions.map((a) => (
                  <button key={a.id} type="button" data-testid={`ai-guide-action-${a.id}`}
                    onClick={() => navigate(`${a.path}${a.path.includes('?') ? '&' : '?'}t=${Date.now()}`)}
                    className="px-3 py-1.5 rounded-full text-[10.5px] font-bold inline-flex items-center gap-1.5 text-[#2A1045] transition-transform hover:scale-[1.03]"
                    style={{ background: 'linear-gradient(90deg, #E9CF8E, #D9B35A)' }}>
                    {a.label} <ArrowRight size={11} />
                  </button>
                ))}
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

          <div className="p-2.5 flex items-center gap-1.5" style={{ borderTop: '1px solid rgba(217,179,90,0.25)' }}>
            {SR && (
              <button type="button" onClick={dictate} data-testid="ai-guide-mic" title="Dicter ma question"
                className={`w-9 h-9 rounded-xl flex items-center justify-center border transition-colors ${
                  listening
                    ? 'bg-red-500/25 border-red-400/60 text-red-300 animate-pulse'
                    : 'bg-white/[0.06] border-white/15 text-white/50 hover:text-[#E9CF8E]'}`}>
                <Mic size={14} />
              </button>
            )}
            <input value={input} onChange={(e) => setInput(e.target.value)} data-testid="ai-guide-input"
              onKeyDown={(e) => e.key === 'Enter' && send()}
              placeholder={listening ? 'Je vous écoute…' : 'Posez votre question…'} maxLength={800}
              className="flex-1 h-9 px-3 rounded-xl bg-white/[0.06] border border-white/15 text-[12px] text-white placeholder:text-white/30 outline-none focus:border-[#D9B35A]/50" />
            <button type="button" onClick={() => send()} disabled={busy || !input.trim()} data-testid="ai-guide-send"
              className="w-9 h-9 rounded-xl flex items-center justify-center bg-[#D9B35A]/20 border border-[#D9B35A]/40 text-[#E9CF8E] hover:bg-[#D9B35A]/35 disabled:opacity-40 transition-colors">
              <Send size={14} />
            </button>
          </div>
        </>
      )}
    </div>
  );
};
