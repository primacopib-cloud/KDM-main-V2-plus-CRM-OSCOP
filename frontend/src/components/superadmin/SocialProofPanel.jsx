import { useCallback, useEffect, useState } from 'react';
import { MessageSquareQuote, Check, X, Wand2, Send, Loader2, Star } from 'lucide-react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const BADGE = {
  pending: 'bg-[#D9B35A]/15 text-[#E9CF8E]',
  approved: 'bg-emerald-400/15 text-emerald-300',
  rejected: 'bg-red-400/15 text-red-300',
};
const LABEL = { pending: 'En attente', approved: 'Publié', rejected: 'Rejeté' };

export const SocialProofPanel = () => {
  const [items, setItems] = useState([]);
  const [invitedCount, setInvitedCount] = useState(0);
  const [inviting, setInviting] = useState(false);
  const [polishing, setPolishing] = useState(null);

  const load = useCallback(() => {
    fetch(`${API}/admin/social-proof/testimonials`, { credentials: 'include' })
      .then((r) => r.json()).then((d) => { setItems(d.items || []); setInvitedCount(d.invited_count || 0); }).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const moderate = async (t, status) => {
    const r = await fetch(`${API}/admin/social-proof/testimonials/${t.id}`, {
      method: 'PATCH', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    });
    if (r.ok) { toast.success(status === 'approved' ? 'Témoignage publié sur la vitrine' : 'Témoignage rejeté'); load(); }
  };

  const polish = async (t) => {
    setPolishing(t.id);
    const r = await fetch(`${API}/admin/social-proof/testimonials/${t.id}/polish`, { method: 'POST', credentials: 'include' });
    const d = await r.json();
    setPolishing(null);
    if (!r.ok) return toast.error(d.detail || 'Reformulation impossible');
    toast.success('Témoignage reformulé par PROSPECT\'IA');
    load();
  };

  const invite = async () => {
    setInviting(true);
    const r = await fetch(`${API}/admin/social-proof/invite`, {
      method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ limit: 20 }),
    });
    const d = await r.json();
    setInviting(false);
    if (!r.ok) return toast.error(d.detail || 'Envoi impossible');
    toast.success(d.sent ? `${d.sent} invitation(s) envoyée(s) aux membres actifs` : d.message);
    load();
  };

  return (
    <div className="glass-panel-soft rounded-[18px] p-5" data-testid="social-proof-panel">
      <div className="flex items-center justify-between flex-wrap gap-2 mb-2">
        <h3 className="font-display text-base text-white flex items-center gap-2">
          <MessageSquareQuote size={15} style={{ color: '#D9B35A' }} /> Preuve sociale — Témoignages
        </h3>
        <button onClick={invite} disabled={inviting} data-testid="social-proof-invite-btn"
          className="h-9 px-3 rounded-lg text-xs font-semibold text-[#1A092D] inline-flex items-center gap-1.5 disabled:opacity-50"
          style={{ background: 'linear-gradient(135deg, #D9B35A, #F2D07A)' }}>
          {inviting ? <Loader2 size={13} className="animate-spin" /> : <Send size={13} />} Inviter 20 membres à témoigner (email IA)
        </button>
      </div>
      <p className="text-xs text-white/50 mb-3">
        PROSPECT'IA rédige et envoie les demandes de témoignage aux membres actifs ({invitedCount} déjà invités), reformule les textes reçus,
        et vous publiez les meilleurs sur la page d'accueil en un clic.
      </p>
      {items.length ? (
        <div className="space-y-2 max-h-96 overflow-y-auto">
          {items.map((t) => (
            <div key={t.id} className="p-3 rounded-xl bg-white/[0.04] border border-white/10 text-xs" data-testid={`testimonial-${t.id}`}>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-white font-medium">{t.name}</span>
                {t.company && <span className="text-white/50">· {t.company}</span>}
                {t.territory && <span className="text-white/40">({t.territory})</span>}
                <span className="inline-flex items-center gap-0.5 text-[#E9CF8E]">
                  {Array.from({ length: t.rating || 5 }).map((_, i) => <Star key={i} size={10} fill="currentColor" />)}
                </span>
                <span className={`px-2 py-0.5 rounded font-semibold ${BADGE[t.status]}`}>{LABEL[t.status]}</span>
                {t.polished && <span className="px-1.5 py-0.5 rounded bg-purple-400/15 text-purple-300">✨ Reformulé IA</span>}
                <div className="ml-auto flex gap-1">
                  {t.status !== 'approved' && (
                    <button onClick={() => moderate(t, 'approved')} data-testid={`testimonial-approve-${t.id}`}
                      className="p-1.5 rounded-lg hover:bg-emerald-500/15 text-emerald-300" title="Publier"><Check size={14} /></button>
                  )}
                  {t.status !== 'rejected' && (
                    <button onClick={() => moderate(t, 'rejected')} className="p-1.5 rounded-lg hover:bg-red-500/15 text-white/40 hover:text-red-300" title="Rejeter"><X size={14} /></button>
                  )}
                  <button onClick={() => polish(t)} disabled={polishing === t.id} data-testid={`testimonial-polish-${t.id}`}
                    className="p-1.5 rounded-lg hover:bg-white/10 text-[#E9CF8E] disabled:opacity-50" title="Reformuler par IA">
                    {polishing === t.id ? <Loader2 size={14} className="animate-spin" /> : <Wand2 size={14} />}
                  </button>
                </div>
              </div>
              <p className="text-white/65 mt-1.5 italic">« {t.text} »</p>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-xs text-white/40">Aucun témoignage reçu pour le moment — lancez une invitation IA aux membres actifs.</p>
      )}
    </div>
  );
};
