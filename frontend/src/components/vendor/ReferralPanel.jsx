import { useCallback, useEffect, useState } from 'react';
import { Gift, Copy, CheckCircle2, MessageCircle, Mail } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

export const ReferralPanel = () => {
  const [data, setData] = useState(null);
  const [claim, setClaim] = useState('');

  const load = useCallback(() => {
    fetch(`${API}/api/referral/me`, { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null)).then(setData).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const stored = localStorage.getItem('referral_code');
    if (!data || data.my_sponsor_code || !stored) return;
    if (stored === data.code) { localStorage.removeItem('referral_code'); return; }
    fetch(`${API}/api/referral/claim`, {
      method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code: stored }),
    }).then(async (r) => {
      const d = await r.json();
      localStorage.removeItem('referral_code');
      if (r.ok) { toast.success(`Code parrain ${stored} appliqué automatiquement`); load(); }
      else toast.error(d.detail || 'Code parrain non applicable');
    }).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  if (!data) return null;
  const link = `${window.location.origin}/adhesion-vendeur?parrain=${data.code}`;

  const shareText = `Rejoignez KDMARCHÉ × O'SCOP avec mon code parrain ${data.code} : ${link}`;
  const copy = () => {
    navigator.clipboard.writeText(shareText);
    toast.success('Code et lien de parrainage copiés');
  };

  const submitClaim = async () => {
    if (!claim.trim()) return toast.error('Saisissez un code parrain');
    const r = await fetch(`${API}/api/referral/claim`, {
      method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code: claim.trim() }),
    });
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    toast.success(d.message);
    setClaim('');
    load();
  };

  return (
    <div className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-5 space-y-3" data-testid="referral-panel">
      <h3 className="font-semibold text-white flex items-center gap-2">
        <Gift className="w-4 h-4 text-[#D9B35A]" /> Programme de parrainage — {data.bonus} CREDI'SCOP par filleul
      </h3>
      <div className="flex flex-wrap items-center gap-2">
        <span className="px-3 py-1.5 rounded-lg font-mono font-bold text-sm text-[#E9CF8E] bg-[#D9B35A]/10 border border-[#D9B35A]/25" data-testid="referral-code">{data.code}</span>
        <button type="button" onClick={copy} data-testid="referral-copy-btn"
          className="px-3 py-1.5 rounded-lg text-[11px] font-bold bg-white/10 text-white/70 hover:text-white inline-flex items-center gap-1 transition-colors">
          <Copy className="w-3.5 h-3.5" /> Copier le lien d'invitation
        </button>
        <a href={`https://wa.me/?text=${encodeURIComponent(shareText)}`} target="_blank" rel="noreferrer" data-testid="referral-whatsapp-btn"
          className="px-3 py-1.5 rounded-lg text-[11px] font-bold inline-flex items-center gap-1 transition-all hover:brightness-110"
          style={{ background: '#25D366', color: '#0b3d22' }}>
          <MessageCircle className="w-3.5 h-3.5" /> WhatsApp
        </a>
        <a href={`mailto:?subject=${encodeURIComponent("Rejoignez KDMARCHÉ × O'SCOP")}&body=${encodeURIComponent(shareText)}`} data-testid="referral-email-btn"
          className="px-3 py-1.5 rounded-lg text-[11px] font-bold bg-white/10 text-white/70 hover:text-white inline-flex items-center gap-1 transition-colors">
          <Mail className="w-3.5 h-3.5" /> Email
        </a>
        {data.total_earned > 0 && (
          <span className="text-xs font-bold text-emerald-400" data-testid="referral-earned">+{data.total_earned} CREDI'SCOP gagnés</span>
        )}
      </div>
      {data.referred?.length > 0 && (
        <div className="space-y-1">
          {data.referred.map((f, i) => (
            <div key={i} className="flex items-center gap-2 text-xs py-1 border-b border-white/5 last:border-0">
              <span className="flex-1 text-white/70">{f.email}</span>
              {f.bonus_paid
                ? <span className="inline-flex items-center gap-1 text-emerald-400 font-bold"><CheckCircle2 className="w-3 h-3" /> Bonus versé</span>
                : <span className="text-white/40">En attente de sa 1ère inscription</span>}
            </div>
          ))}
        </div>
      )}
      {!data.my_sponsor_code && (
        <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-white/10">
          <span className="text-xs text-white/55">J'ai un code parrain :</span>
          <input className="h-8 w-36 rounded-lg px-2.5 text-xs text-white bg-white/[0.05] border border-white/15 uppercase"
            placeholder="KDM-XXXXXX" value={claim} onChange={(e) => setClaim(e.target.value)} data-testid="referral-claim-input" />
          <button type="button" onClick={submitClaim} data-testid="referral-claim-btn"
            className="px-3 py-1.5 rounded-lg text-[11px] font-bold" style={{ background: '#D9B35A', color: '#1F0A33' }}>
            Enregistrer
          </button>
        </div>
      )}
      {data.my_sponsor_code && <p className="text-[11px] text-white/40">Parrainé avec le code {data.my_sponsor_code}.</p>}
      <p className="text-[11px] text-white/40">
        Votre filleul saisit votre code dans son espace (avant sa première consultation) — vous recevez le bonus
        dès sa première inscription, et votre filleul reçoit aussi un bonus de bienvenue. Le tout est tracé au registre.
      </p>
    </div>
  );
};
