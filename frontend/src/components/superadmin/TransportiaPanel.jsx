import { useCallback, useEffect, useState } from 'react';
import { Truck, Plus, Trash2, Send, Sparkles, Loader2, MessageCircleQuestion } from 'lucide-react';
import { toast } from 'sonner';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../ui/dialog';
import { PhoneInput } from '../PhoneInput';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const STATUS_LABELS = {
  NEW: ['À contacter', 'bg-white/10 text-white/70'],
  INVITED: ['Invité', 'bg-blue-500/15 text-blue-300'],
  FOLLOWED_UP: ['Relancé', 'bg-amber-500/15 text-amber-300'],
  REGISTERED: ['Inscrit ✓', 'bg-emerald-500/15 text-emerald-300'],
  DECLINED: ['Refusé', 'bg-red-500/15 text-red-300'],
};
const TERRITORIES = ['GUADELOUPE', 'MARTINIQUE', 'GUYANE', 'REUNION', 'MAYOTTE'];

export const TransportiaPanel = () => {
  const [data, setData] = useState(null);
  const [form, setForm] = useState({ company: '', contact_name: '', email: '', phone: '', territory: 'GUADELOUPE', fleet_type: '' });
  const [draft, setDraft] = useState(null);
  const [genLoading, setGenLoading] = useState('');
  const [sending, setSending] = useState(false);
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [asking, setAsking] = useState(false);

  const load = useCallback(() => {
    fetch(`${API}/admin/transportia/prospects`, { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null)).then(setData).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const addProspect = async () => {
    if (!form.company || !form.email) return toast.error('Société et email requis');
    const r = await fetch(`${API}/admin/transportia/prospects`, {
      method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form),
    });
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    toast.success(`${d.company} ajouté à la prospection`);
    setForm({ company: '', contact_name: '', email: '', phone: '', territory: 'GUADELOUPE', fleet_type: '' });
    load();
  };

  const generate = async (p, kind) => {
    setGenLoading(p.id + kind);
    const r = await fetch(`${API}/admin/transportia/prospects/${p.id}/generate-${kind}`, {
      method: 'POST', credentials: 'include',
    });
    const d = await r.json();
    setGenLoading('');
    if (!r.ok) return toast.error(d.detail || 'Génération échouée');
    setDraft({ prospect: p, kind: kind === 'invite' ? 'invite' : 'followup', subject: d.subject, body: d.body });
  };

  const send = async () => {
    setSending(true);
    const r = await fetch(`${API}/admin/transportia/prospects/${draft.prospect.id}/send`, {
      method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ subject: draft.subject, body: draft.body, kind: draft.kind }),
    });
    const d = await r.json();
    setSending(false);
    if (!r.ok) return toast.error(d.detail || 'Envoi échoué');
    toast.success(`Email envoyé à ${draft.prospect.company}`);
    setDraft(null);
    load();
  };

  const setStatus = async (p, status) => {
    await fetch(`${API}/admin/transportia/prospects/${p.id}`, {
      method: 'PUT', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    });
    load();
  };

  const remove = async (p) => {
    if (!window.confirm(`Supprimer le prospect ${p.company} ?`)) return;
    await fetch(`${API}/admin/transportia/prospects/${p.id}`, { method: 'DELETE', credentials: 'include' });
    load();
  };

  const ask = async () => {
    if (!question.trim()) return;
    setAsking(true);
    const r = await fetch(`${API}/admin/transportia/assist`, {
      method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    });
    const d = await r.json();
    setAsking(false);
    if (!r.ok) return toast.error(d.detail || 'Assistant indisponible');
    setAnswer(d.answer);
  };

  if (!data) return null;
  const inputCls = 'h-9 px-2.5 rounded-lg text-xs text-white bg-white/[0.05] border border-white/15';

  return (
    <div className="glass-panel-soft rounded-[18px] p-5 space-y-4" data-testid="transportia-panel">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h3 className="font-display text-base text-white flex items-center gap-2">
          <Truck size={15} style={{ color: '#D9B35A' }} /> TRANSPORT'IA — recrutement des transporteurs LOGICOOP
        </h3>
        <div className="flex gap-2 flex-wrap" data-testid="transportia-stats">
          {Object.entries(STATUS_LABELS).map(([k, [label, cls]]) => (
            <span key={k} className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${cls}`}>
              {data.counts?.[k] || 0} {label}
            </span>
          ))}
        </div>
      </div>

      <div className="flex flex-wrap gap-2 items-center p-3 rounded-xl bg-white/[0.03] border border-white/[0.07]">
        <input className={`${inputCls} w-40`} placeholder="Société *" value={form.company}
          onChange={(e) => setForm({ ...form, company: e.target.value })} data-testid="transportia-company-input" />
        <input className={`${inputCls} w-32`} placeholder="Contact" value={form.contact_name}
          onChange={(e) => setForm({ ...form, contact_name: e.target.value })} />
        <input className={`${inputCls} w-44`} placeholder="Email *" value={form.email}
          onChange={(e) => setForm({ ...form, email: e.target.value })} data-testid="transportia-email-input" />
        <PhoneInput value={form.phone} onChange={(v) => setForm({ ...form, phone: v })} testId="transportia-phone-input" />
        <select className={`${inputCls} w-32`} value={form.territory}
          onChange={(e) => setForm({ ...form, territory: e.target.value })}>
          {TERRITORIES.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <input className={`${inputCls} w-36`} placeholder="Flotte (frigo, PL...)" value={form.fleet_type}
          onChange={(e) => setForm({ ...form, fleet_type: e.target.value })} />
        <button onClick={addProspect} data-testid="transportia-add-btn"
          className="px-3 h-9 rounded-lg text-xs font-bold inline-flex items-center gap-1"
          style={{ background: '#D9B35A', color: '#1F0A33' }}>
          <Plus size={13} /> Ajouter
        </button>
      </div>

      <div className="space-y-2 max-h-80 overflow-y-auto">
        {data.items.length === 0 && (
          <p className="text-xs text-white/40 italic">Aucun transporteur en prospection — ajoutez votre premier prospect ci-dessus.</p>
        )}
        {data.items.map((p) => {
          const [label, cls] = STATUS_LABELS[p.status] || STATUS_LABELS.NEW;
          return (
            <div key={p.id} className="flex items-center gap-2 p-2.5 rounded-xl bg-white/[0.03] border border-white/[0.06]" data-testid={`transportia-prospect-${p.id}`}>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-white font-semibold truncate">{p.company}
                  <span className="text-white/40 font-normal text-xs"> · {p.territory}{p.fleet_type ? ` · ${p.fleet_type}` : ''}</span>
                </p>
                <p className="text-[11px] text-white/45 truncate">{p.contact_name ? `${p.contact_name} — ` : ''}{p.email}{p.phone ? ` · ${p.phone}` : ''}</p>
              </div>
              <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${cls}`}>{label}</span>
              {p.status !== 'REGISTERED' && (
                <button onClick={() => generate(p, p.status === 'NEW' ? 'invite' : 'followup')}
                  disabled={genLoading === p.id + (p.status === 'NEW' ? 'invite' : 'followup')}
                  data-testid={`transportia-generate-${p.id}`}
                  className="px-2.5 py-1.5 rounded-lg text-[11px] font-bold inline-flex items-center gap-1 bg-[#D9B35A]/15 border border-[#D9B35A]/30 text-[#E9CF8E]">
                  {genLoading.startsWith(p.id) ? <Loader2 size={11} className="animate-spin" /> : <Sparkles size={11} />}
                  {p.status === 'NEW' ? 'Invitation IA' : 'Relance IA'}
                </button>
              )}
              <select value={p.status} onChange={(e) => setStatus(p, e.target.value)}
                className="h-8 px-1.5 rounded-lg text-[10px] text-white bg-white/[0.05] border border-white/15">
                {Object.entries(STATUS_LABELS).map(([k, [l]]) => <option key={k} value={k}>{l}</option>)}
              </select>
              <button onClick={() => remove(p)} className="p-1.5 rounded-lg text-white/40 hover:text-red-400">
                <Trash2 size={13} />
              </button>
            </div>
          );
        })}
      </div>

      <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.07] space-y-2">
        <p className="text-xs font-semibold text-white/70 flex items-center gap-1.5">
          <MessageCircleQuestion size={13} className="text-[#D9B35A]" /> Assistant objections — l'IA vous aide à répondre aux transporteurs
        </p>
        <div className="flex gap-2">
          <input className={`${inputCls} flex-1`} placeholder="Ex : « Combien ça coûte de rejoindre LOGICOOP ? »"
            value={question} onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && ask()} data-testid="transportia-assist-input" />
          <button onClick={ask} disabled={asking} data-testid="transportia-assist-btn"
            className="px-3 h-9 rounded-lg text-xs font-bold inline-flex items-center gap-1 bg-white/[0.06] border border-white/15 text-white/75">
            {asking ? <Loader2 size={12} className="animate-spin" /> : <Sparkles size={12} />} Demander
          </button>
        </div>
        {answer && <p className="text-xs text-white/70 whitespace-pre-line p-2.5 rounded-lg bg-white/[0.04] border border-white/[0.06]" data-testid="transportia-assist-answer">{answer}</p>}
      </div>

      <Dialog open={!!draft} onOpenChange={(o) => !o && setDraft(null)}>
        <DialogContent className="max-w-xl bg-[#1A092D] border-white/10">
          <DialogHeader>
            <DialogTitle className="text-white text-base flex items-center gap-2">
              <Send size={15} className="text-[#D9B35A]" />
              {draft?.kind === 'invite' ? 'Invitation' : 'Relance'} — {draft?.prospect?.company}
            </DialogTitle>
          </DialogHeader>
          {draft && (
            <div className="space-y-3">
              <input className={`${inputCls} w-full`} value={draft.subject}
                onChange={(e) => setDraft({ ...draft, subject: e.target.value })} data-testid="transportia-draft-subject" />
              <textarea rows={9} value={draft.body} onChange={(e) => setDraft({ ...draft, body: e.target.value })}
                data-testid="transportia-draft-body"
                className="w-full px-2.5 py-2 rounded-lg text-xs text-white bg-white/[0.05] border border-white/15" />
              <p className="text-[10px] text-white/40">Destinataire : {draft.prospect.email} — vous pouvez modifier le texte avant envoi.</p>
            </div>
          )}
          <DialogFooter>
            <button onClick={() => setDraft(null)} className="px-3 py-2 rounded-lg text-xs text-white/60 border border-white/15">Annuler</button>
            <button onClick={send} disabled={sending} data-testid="transportia-send-btn"
              className="px-4 py-2 rounded-lg text-xs font-bold inline-flex items-center gap-1.5"
              style={{ background: '#D9B35A', color: '#1F0A33' }}>
              {sending ? <Loader2 size={12} className="animate-spin" /> : <Send size={12} />} Envoyer l'email
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};
