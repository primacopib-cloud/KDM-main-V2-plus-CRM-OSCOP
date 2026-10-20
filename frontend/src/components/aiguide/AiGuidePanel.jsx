import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Send, Sparkles, Loader2, Mic, Volume2, VolumeX, History, ArrowRight, ArrowLeft, Compass, AudioLines, Play, Paperclip, Copy, Pencil, RotateCcw, FileText, Image as ImageIcon, Table, Download, Brain, FolderArchive } from 'lucide-react';
import { API, getAuthHeaders } from '../../services/http';
import { AiGuideHistory } from './AiGuideHistory';
import { OracleMemoryMenu } from './OracleMemoryMenu';
import { OracleBulkProposals } from './OracleBulkProposals';

const SR = typeof window !== 'undefined' && (window.SpeechRecognition || window.webkitSpeechRecognition);

const VOICE_PREVIEW = {
  gcf: (v) => `Bonjou ! Sé mwen Oracle. Sé vwa « ${v} » ou ka tann la — sé li ki ké li akèy a'w an kréyòl.`,
  fr: (v) => `Bonjour ! Je suis Oracle. Voici la voix « ${v} », celle qui lira votre accueil et mes réponses.`,
  en: (v) => `Hello! I'm Oracle. This is the "${v}" voice, the one that will read your welcome and my answers.`,
  es: (v) => `¡Hola! Soy Oracle. Esta es la voz « ${v} », la que leerá su bienvenida y mis respuestas.`,
};
const VOICE_MENU_TITLE = {
  gcf: 'Vwa ki ké li akèy-la', fr: "Voix de lecture & d'accueil",
  en: 'Reading & welcome voice', es: 'Voz de lectura y bienvenida',
};
const WEEKLY_BTN = {
  fr: 'Écouter le résumé de la semaine', en: 'Listen to the weekly summary',
  es: 'Escuchar el resumen de la semana', gcf: 'Kouté rézimé a simenn-lan',
};

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
  const [proposal, setProposal] = useState(null);
  const [proposals, setProposals] = useState([]);
  const [showMemory, setShowMemory] = useState(false);
  const [contractTaskId, setContractTaskId] = useState(null);
  const [voice, setVoice] = useState(null);
  const [voices, setVoices] = useState([]);
  const [showVoices, setShowVoices] = useState(false);
  const [previewing, setPreviewing] = useState(null);
  const [weeklyBusy, setWeeklyBusy] = useState(false);

  const playWeekly = async () => {
    setWeeklyBusy(true);
    try {
      const r = await fetch(`${API}/ai-guide/weekly-summary?lang=${lang}`, { credentials: 'include', headers: getAuthHeaders() });
      if (!r.ok) throw new Error('summary');
      const d = await r.json();
      setMessages((m) => [...m, { role: 'assistant', content: d.text }]);
      readAloud(d.text);
    } catch { /* silencieux */ } finally { setWeeklyBusy(false); }
  };

  useEffect(() => {
    fetch(`${API}/ai-guide/voice`, { credentials: 'include', headers: getAuthHeaders() })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => { if (d) { setVoice(d.voice); setVoices(d.voices || []); } }).catch(() => {});
  }, []);

  const previewVoice = async (v) => {
    setPreviewing(v);
    try {
      audioRef.current?.pause();
      const r = await fetch(`${API}/ai-guide/tts`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ text: (VOICE_PREVIEW[lang] || VOICE_PREVIEW.fr)(v), voice: v }),
      });
      if (!r.ok) throw new Error('tts');
      const url = URL.createObjectURL(await r.blob());
      const audio = new Audio(url);
      audioRef.current = audio;
      audio.onended = () => { URL.revokeObjectURL(url); setPreviewing(null); };
      await audio.play();
    } catch { setPreviewing(null); }
  };

  const saveVoice = async (v) => {
    setVoice(v);
    try {
      await fetch(`${API}/ai-guide/voice`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ voice: v }),
      });
      previewVoice(v);
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
  const fileRef = useRef(null);
  const [attachOpen, setAttachOpen] = useState(false);
  const [accept, setAccept] = useState('.pdf,.docx,.txt,.png,.jpg,.jpeg,.webp,.csv,.xlsx');
  const [attachments, setAttachments] = useState([]);

  const loadAttachments = (sid) => {
    const s = sid || sessionId;
    if (!s) { setAttachments([]); return; }
    fetch(`${API}/ai-guide/attachments?session_id=${encodeURIComponent(s)}`, {
      credentials: 'include', headers: getAuthHeaders(),
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => setAttachments(d?.attachments || []))
      .catch(() => {});
  };
  const deleteAttachment = async (id) => {
    try {
      await fetch(`${API}/ai-guide/attachments/${id}`, {
        method: 'DELETE', credentials: 'include', headers: getAuthHeaders(),
      });
      setAttachments((a) => a.filter((x) => x.id !== id));
    } catch { /* noop */ }
  };

  const pickFile = (kindAccept) => {
    setAccept(kindAccept);
    setAttachOpen(false);
    setTimeout(() => fileRef.current?.click(), 60);
  };
  const [copiedIdx, setCopiedIdx] = useState(null);
  const [editingIdx, setEditingIdx] = useState(null);

  const copyMsg = async (i, content) => {
    try {
      await navigator.clipboard.writeText(content);
    } catch {
      const ta = document.createElement('textarea');
      ta.value = content;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      ta.remove();
    }
    setCopiedIdx(i);
    setTimeout(() => setCopiedIdx(null), 1500);
  };
  const editMsg = (i, content) => {
    setEditingIdx(i);
    setInput(content);
    document.querySelector('[data-testid="ai-guide-input"]')?.focus();
  };
  const cancelEdit = () => { setEditingIdx(null); setInput(''); };
  const retryMsg = (content) => { if (!busy) send(content); };

  const uploadFile = async (file) => {
    if (busy) return;
    const isPdf = file.name.toLowerCase().endsWith('.pdf');
    const question = input.trim();
    if (space === 'admin' && isPdf && !question) { uploadContract(file); return; }
    setProposal(null);
    setProposals([]);
    setContractTaskId(null);
    setSuggestions([]);
    setActions([]);
    setInput('');
    setMessages((m) => [...m, { role: 'user', content: `📎 ${file.name}${question ? ` — ${question}` : ''}` }]);
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      fd.append('question', question);
      fd.append('space', space);
      fd.append('lang', lang);
      if (sessionId) fd.append('session_id', sessionId);
      const r = await fetch(`${API}/ai-guide/analyze-file`, {
        method: 'POST', credentials: 'include', headers: getAuthHeaders(), body: fd,
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Analyse impossible');
      setSessionId(d.session_id);
      sessionStorage.setItem(`guidia_session_${space}`, d.session_id);
      setMessages((m) => [...m, { role: 'assistant', content: d.answer }]);
      if (speak) readAloud(d.answer);
    } catch (e) {
      setMessages((m) => [...m, { role: 'assistant', content: `⚠ ${e.message}` }]);
    }
    setBusy(false);
  };

  const uploadContract = async (file) => {
    if (busy) return;
    setProposal(null);
    setContractTaskId(null);
    setSuggestions([]);
    setActions([]);
    setMessages((m) => [...m, { role: 'user', content: `📄 Analyse du contrat : ${file.name}` }]);
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      if (sessionId) fd.append('session_id', sessionId);
      fd.append('lang', lang);
      const r = await fetch(`${API}/oracle-admin/analyze-contract`, {
        method: 'POST', credentials: 'include', headers: getAuthHeaders(), body: fd,
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Analyse impossible');
      setSessionId(d.session_id);
      sessionStorage.setItem(`guidia_session_${space}`, d.session_id);
      setMessages((m) => [...m, { role: 'assistant', content: d.answer }]);
      const final = await pollTask(d.task.id);
      setMessages((m) => [...m, { role: 'assistant', content: final }]);
      if (speak) readAloud(final);
    } catch (e) {
      setMessages((m) => [...m, { role: 'assistant', content: `⚠ ${e.message}` }]);
    }
    setBusy(false);
  };

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
      u.rate = 0.95;
      u.pitch = 0.95;
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
    const correctedFrom = editingIdx !== null ? messages[editingIdx]?.content : null;
    if (proposal && space === 'admin') {
      const low = message.toLowerCase();
      if (/^(ex[eé]cute|confirme|oui|vas[- ]y|go\b|valide)/.test(low)) {
        setInput('');
        setMessages((m) => [...m, { role: 'user', content: message }]);
        executeProposal();
        return;
      }
      if (/^(annule|non\b|stop\b|abandonne)/.test(low)) {
        setInput('');
        setMessages((m) => [...m, { role: 'user', content: message }]);
        cancelProposal();
        return;
      }
    }
    setInput('');
    setEditingIdx(null);
    setSuggestions([]);
    setActions([]);
    setProposal(null);
    setProposals([]);
    setContractTaskId(null);
    setMessages((m) => [...m, { role: 'user', content: message }]);
    setBusy(true);
    try {
      const endpoint = space === 'admin' ? 'oracle-admin/command' : 'ai-guide/chat';
      const r = await fetch(`${API}/${endpoint}`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({
          message, session_id: sessionId, space, lang,
          ...(correctedFrom && correctedFrom !== message ? { corrected_from: correctedFrom } : {}),
        }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Réponse indisponible');
      setSessionId(d.session_id);
      sessionStorage.setItem(`guidia_session_${space}`, d.session_id);
      const answer = d.answer.replace(/\*\*/g, '');
      setMessages((m) => [...m, { role: 'assistant', content: answer }]);
      setSuggestions(d.suggestions || []);
      setActions(d.actions || []);
      if (d.proposal) {
        setProposal(d.proposal);
        readAloud(`${d.proposal.summary} Dites « exécuter » pour confirmer, ou « annuler ».`);
      } else if (d.proposals?.length) {
        setProposals(d.proposals);
        readAloud(`${d.proposals.length} ajustements proposés depuis le tableau — confirmez chaque ligne.`);
      } else if (d.task) {
        const final = await pollTask(d.task.id);
        setMessages((m) => [...m, { role: 'assistant', content: final }]);
        if (d.task.kind === 'contract') setContractTaskId(d.task.id);
        if (speak) readAloud(final);
      } else if (speak) {
        readAloud(answer);
      }
    } catch (e) {
      setMessages((m) => [...m, { role: 'assistant', content: `⚠ ${e.message}` }]);
    }
    setBusy(false);
  };

  const downloadContractPdf = async () => {
    if (!contractTaskId) return;
    try {
      const r = await fetch(`${API}/oracle-admin/contract-pdf/${contractTaskId}`, {
        credentials: 'include', headers: getAuthHeaders(),
      });
      if (!r.ok) throw new Error('export');
      const url = URL.createObjectURL(await r.blob());
      const a = document.createElement('a');
      a.href = url;
      a.download = 'contrat-oscop-oracle.pdf';
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setMessages((m) => [...m, { role: 'assistant', content: '⚠ Export PDF impossible — réessayez.' }]);
    }
  };

  const pollTask = async (taskId) => {
    for (let i = 0; i < 70; i += 1) {
      await new Promise((res) => setTimeout(res, 3000));
      const r = await fetch(`${API}/oracle-admin/task/${taskId}`, {
        credentials: 'include', headers: getAuthHeaders(),
      });
      if (!r.ok) throw new Error('Suivi de la tâche impossible');
      const t = await r.json();
      if (t.status === 'DONE') return t.answer;
      if (t.status === 'FAILED') throw new Error(t.error || 'Analyse échouée — réessayez');
    }
    throw new Error('Analyse trop longue — réessayez');
  };

  const executeProposal = async () => {
    if (!proposal || busy) return;
    setBusy(true);
    try {
      const r = await fetch(`${API}/oracle-admin/execute`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ proposal_id: proposal.id }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Exécution impossible');
      setMessages((m) => [...m, { role: 'assistant', content: `✅ ${d.message}` }]);
      readAloud(d.message);
    } catch (e) {
      setMessages((m) => [...m, { role: 'assistant', content: `⚠ ${e.message}` }]);
    }
    setProposal(null);
    setBusy(false);
  };

  const cancelProposal = () => {
    if (!proposal) return;
    fetch(`${API}/oracle-admin/cancel`, {
      method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify({ proposal_id: proposal.id }),
    }).catch(() => {});
    setMessages((m) => [...m, { role: 'assistant', content: 'Action annulée — rien n\'a été exécuté.' }]);
    readAloud('Action annulée.');
    setProposal(null);
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
    <div className="fixed bottom-24 right-6 z-[70] w-[370px] max-w-[calc(100vw-2rem)] rounded-2xl overflow-hidden flex flex-col transition-opacity duration-300 opacity-60 hover:opacity-100 focus-within:opacity-100"
      data-testid="ai-guide-panel"
      onKeyDown={(e) => { if (e.key === 'Escape') onClose?.(); }}
      style={{
        height: 'min(540px, calc(100vh - 8rem))',
        background: 'linear-gradient(180deg, rgba(42,16,69,0.82) 0%, rgba(30,12,52,0.88) 100%)',
        border: '1px solid rgba(217,179,90,0.4)',
        boxShadow: '0 24px 60px rgba(0,0,0,0.45), 0 0 30px rgba(217,179,90,0.1)',
        backdropFilter: 'blur(5px)',
      }}>
      <div className="px-4 py-3 flex items-center gap-2.5"
        style={{ background: 'linear-gradient(90deg, rgba(69,31,107,0.9), rgba(184,134,11,0.25))', borderBottom: '1px solid rgba(217,179,90,0.3)' }}>
        <span className="w-8 h-8 rounded-full flex items-center justify-center"
          style={{ background: 'rgba(217,179,90,0.18)', border: '1px solid rgba(217,179,90,0.5)' }}>
          <Sparkles size={15} className="text-[#E9CF8E]" />
        </span>
        <span>
          <p className="text-[13px] font-bold text-[#E9CF8E] leading-tight">Oracle{space === 'admin' ? ' Admin' : ''}</p>
          <p className="text-[9.5px] text-white/45 leading-tight">
            {space === 'admin' ? 'Copilote exécutif — dictez vos commandes d\'administration' : 'Votre copilote Communityplace — gratuit'}
          </p>
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
          <span className="relative">
            <button type="button" data-testid="oracle-memory-btn" title="Mémoire d'Oracle — ce qu'il a appris de vous"
              onClick={() => setShowMemory(!showMemory)}
              className={`p-1.5 rounded-lg transition-colors ${showMemory ? 'text-[#E9CF8E] bg-[#D9B35A]/15' : 'text-white/40 hover:text-white'}`}>
              <Brain size={14} />
            </button>
            {showMemory && <OracleMemoryMenu />}
          </span>
          {voices.length > 0 && (
            <span className="relative">
              <button type="button" data-testid="ai-guide-voice-btn" title="Choisir ma voix Oracle"
                onClick={() => setShowVoices(!showVoices)}
                className={`p-1.5 rounded-lg transition-colors ${showVoices ? 'text-[#E9CF8E] bg-[#D9B35A]/15' : 'text-white/40 hover:text-white'}`}>
                <AudioLines size={14} />
              </button>
              {showVoices && (
                <span className="absolute right-0 top-8 z-10 w-48 rounded-xl p-1.5 flex flex-col gap-0.5"
                  data-testid="ai-guide-voice-menu"
                  style={{ background: 'rgba(30,12,52,0.98)', border: '1px solid rgba(217,179,90,0.4)' }}>
                  <span className="px-2 py-1 text-[9.5px] uppercase tracking-wider text-[#E9CF8E]/70 font-bold">
                    {VOICE_MENU_TITLE[lang] || VOICE_MENU_TITLE.fr}
                  </span>
                  {voices.map((v) => (
                    <span key={v} className="flex items-center gap-1">
                      <button type="button" onClick={() => saveVoice(v)} data-testid={`voice-${v}`}
                        className={`flex-1 px-2 py-1 rounded-lg text-left text-[11px] capitalize transition-colors ${
                          v === voice ? 'bg-[#D9B35A]/25 text-[#E9CF8E] font-bold' : 'text-white/60 hover:text-white hover:bg-white/[0.06]'}`}>
                        {v}
                      </button>
                      <button type="button" onClick={() => previewVoice(v)} data-testid={`voice-preview-${v}`}
                        title="Écouter cette voix"
                        className={`p-1 rounded-lg transition-colors ${previewing === v ? 'text-[#E9CF8E] bg-[#D9B35A]/20' : 'text-white/35 hover:text-[#E9CF8E]'}`}>
                        {previewing === v ? <Loader2 size={12} className="animate-spin" /> : <Play size={12} />}
                      </button>
                    </span>
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
                  <div className={`mt-1.5 pt-1 flex items-center gap-2.5 border-t ${m.role === 'user' ? 'border-[#D9B35A]/20 justify-end' : 'border-white/10'}`}>
                    <button type="button" data-testid={`oracle-msg-copy-${i}`} title="Copier le texte dans le presse-papiers"
                      onClick={() => copyMsg(i, m.content)}
                      className="flex items-center gap-1 text-[9px] font-semibold text-white/40 hover:text-[#E9CF8E] transition-colors">
                      <Copy size={10} /> {copiedIdx === i ? 'Copié !' : 'Copier'}
                    </button>
                    {m.role === 'user' && !m.content.startsWith('📄') && !m.content.startsWith('📎') && (
                      <>
                        <button type="button" data-testid={`oracle-msg-edit-${i}`} title="Corriger ce message dans la zone de texte, puis le renvoyer manuellement"
                          onClick={() => editMsg(i, m.content)}
                          className="flex items-center gap-1 text-[9px] font-semibold text-white/40 hover:text-[#E9CF8E] transition-colors">
                          <Pencil size={10} /> Modifier
                        </button>
                        <button type="button" data-testid={`oracle-msg-retry-${i}`} title="Relancer la réponse d'Oracle — historique conservé, aucune action confirmée n'est rejouée"
                          onClick={() => retryMsg(m.content)} disabled={busy}
                          className="flex items-center gap-1 text-[9px] font-semibold text-white/40 hover:text-[#E9CF8E] disabled:opacity-40 transition-colors">
                          <RotateCcw size={10} /> Relancer
                        </button>
                      </>
                    )}
                  </div>
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
                className="on-light gold-chip w-full rounded-xl px-3 py-2.5 text-left text-[12px] font-bold text-[#2A1045] flex items-center gap-2 transition-transform hover:scale-[1.01]"
                style={{ background: 'linear-gradient(90deg, #E9CF8E, #D9B35A)' }}>
                <Compass size={15} /> Nouveau ici ? Lancez la visite guidée de votre espace
              </button>
            )}
            {!busy && space === 'admin' && (
              <button type="button" onClick={playWeekly} disabled={weeklyBusy} data-testid="ai-guide-weekly-summary"
                className="on-light gold-chip w-full rounded-xl px-3 py-2.5 text-left text-[12px] font-bold text-[#2A1045] flex items-center gap-2 transition-transform hover:scale-[1.01] disabled:opacity-60"
                style={{ background: 'linear-gradient(90deg, #E9CF8E, #D9B35A)' }}>
                {weeklyBusy ? <Loader2 size={15} className="animate-spin" /> : <AudioLines size={15} />}
                {WEEKLY_BTN[lang] || WEEKLY_BTN.fr}
              </button>
            )}
            {!busy && contractTaskId && (
              <button type="button" onClick={downloadContractPdf} data-testid="oracle-contract-pdf-btn"
                className="gold-chip w-full rounded-xl px-3 py-2 text-[11.5px] font-bold text-[#2A1045] transition-transform hover:scale-[1.01]"
                style={{ background: 'linear-gradient(90deg, #E9CF8E, #D9B35A)' }}>
                Télécharger le contrat en PDF (en-tête O'SCOP)
              </button>
            )}
            {!busy && proposal && (
              <div className="rounded-xl p-3 space-y-2" data-testid="oracle-admin-proposal"
                style={{ background: 'rgba(217,179,90,0.1)', border: '1.5px solid rgba(217,179,90,0.55)' }}>
                <p className="text-[10px] font-bold uppercase tracking-wider text-[#E9CF8E]">
                  {proposal.destructive ? '⚠ Action sensible — confirmation requise' : 'Confirmation requise'}
                </p>
                <p className="text-[12px] text-white/85 leading-relaxed">{proposal.summary}</p>
                <p className="text-[9px] text-white/40">Mains libres : dites « exécuter » ou « annuler » au micro.</p>
                <div className="flex gap-2 pt-1">
                  <button type="button" onClick={executeProposal} data-testid="oracle-admin-execute"
                    className="on-light gold-chip flex-1 h-8 rounded-full text-[11px] font-bold text-[#2A1045] transition-transform hover:scale-[1.02]"
                    style={{ background: 'linear-gradient(90deg, #E9CF8E, #D9B35A)' }}>
                    Exécuter
                  </button>
                  <button type="button" onClick={cancelProposal} data-testid="oracle-admin-cancel"
                    className="flex-1 h-8 rounded-full text-[11px] font-bold text-white/70 border border-white/25 hover:bg-white/10 transition-colors">
                    Annuler
                  </button>
                </div>
              </div>
            )}
            {!busy && proposals.length > 0 && (
              <OracleBulkProposals proposals={proposals}
                onRemove={(id) => setProposals((ps) => ps.filter((p) => p.id !== id))}
                onResult={(msg) => setMessages((m) => [...m, { role: 'assistant', content: msg }])} />
            )}
            {!busy && actions.length > 0 && (
              <div className="flex flex-wrap gap-1.5 pt-0.5" data-testid="ai-guide-actions">
                {actions.map((a) => (
                  <button key={a.id} type="button" data-testid={`ai-guide-action-${a.id}`}
                    onClick={() => navigate(`${a.path}${a.path.includes('?') ? '&' : '?'}t=${Date.now()}`)}
                    className="on-light gold-chip px-3 py-1.5 rounded-full text-[10.5px] font-bold inline-flex items-center gap-1.5 text-[#2A1045] transition-transform hover:scale-[1.03]"
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

          {editingIdx !== null && (
            <div className="px-3 py-1.5 flex items-center justify-between text-[10px] text-[#E9CF8E] bg-[#D9B35A]/10 border-t border-[#D9B35A]/25"
              data-testid="oracle-editing-banner">
              <span>Modification en cours — corrigez le texte puis renvoyez (l'historique est conservé)</span>
              <button type="button" onClick={cancelEdit} data-testid="oracle-editing-cancel"
                className="font-bold hover:text-white transition-colors">Annuler</button>
            </div>
          )}
          <div className="p-2.5 flex items-center gap-1.5 relative" style={{ borderTop: '1px solid rgba(217,179,90,0.25)' }}>
            {attachOpen && (
              <div className="absolute bottom-12 left-2 right-2 z-20 rounded-xl p-2.5 space-y-1 border border-[#D9B35A]/40 shadow-2xl"
                style={{ background: '#2A1045' }} data-testid="oracle-attach-menu">
                <p className="text-[10px] font-bold uppercase tracking-wider text-[#E9CF8E]/80 mb-1">Joindre un fichier</p>
                <button type="button" onClick={() => pickFile('.pdf,.docx,.txt')} data-testid="oracle-attach-doc"
                  className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-[11px] text-white/80 hover:bg-white/10 hover:text-[#E9CF8E] transition-colors text-left">
                  <FileText size={13} /> Documents — PDF, Word, TXT
                </button>
                <button type="button" onClick={() => pickFile('.png,.jpg,.jpeg,.webp')} data-testid="oracle-attach-img"
                  className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-[11px] text-white/80 hover:bg-white/10 hover:text-[#E9CF8E] transition-colors text-left">
                  <ImageIcon size={13} /> Photos / images — JPG, PNG, WEBP
                </button>
                <button type="button" onClick={() => pickFile('.xlsx,.csv')} data-testid="oracle-attach-table"
                  className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-[11px] text-white/80 hover:bg-white/10 hover:text-[#E9CF8E] transition-colors text-left">
                  <Table size={13} /> Tableaux — Excel, CSV
                </button>
                <button type="button" onClick={() => pickFile('.zip')} data-testid="oracle-attach-zip"
                  className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-[11px] text-white/80 hover:bg-white/10 hover:text-[#E9CF8E] transition-colors text-left">
                  <FolderArchive size={13} /> Dossier complet — ZIP (PDF, Word, Excel…)
                </button>
                <p className="text-[9px] text-white/40 leading-snug pt-1 border-t border-white/10">
                  Oracle lit le fichier (ou chaque fichier du dossier ZIP) pour répondre à votre demande ou préparer
                  une action — toute modification reste soumise à votre confirmation. Pièces privées, liées à cette
                  discussion et réutilisables dans les échanges suivants.
                </p>
                <a href={`${API}/ai-guide/sample-file`} download data-testid="oracle-attach-sample"
                  className="inline-flex items-center gap-1.5 text-[10px] font-bold text-[#E9CF8E] hover:underline">
                  <Download size={11} /> Télécharger un fichier d'exemple (CSV)
                </a>
                {attachments.length > 0 && (
                  <div className="pt-1.5 border-t border-white/10 space-y-1" data-testid="oracle-attach-gallery">
                    <p className="text-[9.5px] font-bold uppercase tracking-wider text-[#E9CF8E]/60">
                      Pièces de la discussion ({attachments.length})
                    </p>
                    {attachments.map((a) => (
                      <div key={a.id} className="flex items-center justify-between gap-2 px-2 py-1 rounded-lg bg-white/[0.04] border border-white/10"
                        data-testid={`oracle-attachment-${a.id}`}>
                        <span className="flex items-center gap-1.5 text-[10px] text-white/75 truncate">
                          {a.kind === 'image' ? <ImageIcon size={11} /> : a.kind === 'dossier' ? <FolderArchive size={11} /> : a.kind === 'tableau' ? <Table size={11} /> : <FileText size={11} />}
                          <span className="truncate">{a.filename}</span>
                        </span>
                        <button type="button" onClick={() => deleteAttachment(a.id)}
                          data-testid={`oracle-attachment-delete-${a.id}`} title="Supprimer cette pièce jointe de la discussion"
                          className="text-white/35 hover:text-red-300 text-[12px] font-bold leading-none transition-colors">×</button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
            <input ref={fileRef} type="file" accept={accept} className="hidden"
              data-testid="oracle-contract-file"
              onChange={(e) => { const f = e.target.files?.[0]; e.target.value = ''; if (f) uploadFile(f); }} />
            <button type="button" onClick={() => { const n = !attachOpen; setAttachOpen(n); if (n) loadAttachments(); }} disabled={busy}
              data-testid="oracle-attach-btn"
              title="Joindre un fichier — documents (PDF, Word, TXT), photos (JPG, PNG, WEBP), tableaux (Excel, CSV)"
              className={`h-9 px-2 rounded-xl flex items-center gap-1 border text-[10px] font-bold disabled:opacity-40 transition-colors ${attachOpen
                ? 'bg-[#D9B35A]/20 border-[#D9B35A]/50 text-[#E9CF8E]'
                : 'bg-white/[0.06] border-white/15 text-white/60 hover:text-[#E9CF8E]'}`}>
              <Paperclip size={13} /> Joindre
            </button>
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
              onKeyDown={(e) => {
                if (e.key === 'Enter') { e.preventDefault(); send(); }
                else if (e.key === 'Escape') { e.preventDefault(); onClose?.(); }
                else if (e.key === 'ArrowUp' && !input) {
                  const lastUser = [...messages].reverse().find((m) => m.role === 'user' && !m.content.startsWith('📄') && !m.content.startsWith('📎'));
                  if (lastUser) { e.preventDefault(); editMsg(messages.lastIndexOf(lastUser), lastUser.content); }
                }
              }}
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
