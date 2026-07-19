import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { FileSignature, CheckCircle2, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import NavBar from '../components/NavBar';
import { API } from '../services/http';

export default function PartnerSignPage() {
  const [params] = useSearchParams();
  const token = params.get('token');
  const [conv, setConv] = useState(null);
  const [err, setErr] = useState(null);
  const [sign, setSign] = useState({ nom: '', qualite: '', lu_approuve: false });
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(null);

  useEffect(() => {
    fetch(`${API}/partner-conventions/by-token/${token}`)
      .then(async (r) => { const d = await r.json(); if (!r.ok) throw new Error(d.detail); setConv(d); })
      .catch((e) => setErr(e.message));
  }, [token]);

  const doSign = async () => {
    if (!sign.lu_approuve) return toast.error('Cochez « Lu et approuvé » pour signer');
    if (!sign.nom || !sign.qualite) return toast.error('Nom et qualité requis');
    setBusy(true);
    try {
      const r = await fetch(`${API}/partner-conventions/by-token/${token}/sign`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(sign),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Erreur');
      setDone(d.verification_code);
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };

  const inp = 'w-full h-11 rounded-xl px-3.5 text-sm text-white placeholder-white/35 bg-white/[0.05] border border-[#D9B35A]/25 focus:outline-none focus:ring-1 focus:ring-[#D9B35A]/60';
  return (
    <div className="min-h-screen" data-testid="partner-sign-page">
      <NavBar />
      <div className="max-w-2xl mx-auto px-4 pt-28 pb-16">
        {err ? (
          <div className="glass-panel rounded-[22px] p-10 text-center text-white/70 text-sm">{err}</div>
        ) : done ? (
          <div className="glass-panel rounded-[22px] p-10 text-center" data-testid="partner-sign-done">
            <CheckCircle2 className="w-14 h-14 mx-auto text-[#7BC94E] mb-4" />
            <h1 className="text-xl font-bold text-white mb-2">Convention signée ✔</h1>
            <p className="text-white/65 text-sm">Code de vérification : <strong className="text-[#E9CF8E]">{done}</strong></p>
            <p className="text-white/45 text-xs mt-3">Un exemplaire est archivé par la coopérative. Merci pour votre confiance !</p>
          </div>
        ) : !conv ? (
          <div className="flex justify-center py-16"><Loader2 className="w-7 h-7 animate-spin text-[#D9B35A]" /></div>
        ) : (
          <div className="glass-panel rounded-[22px] p-7 space-y-4">
            <h1 className="text-xl font-bold text-white" style={{ fontFamily: '"Playfair Display", serif' }}>{conv.title}</h1>
            <p className="text-[11px] text-white/45">Convention de partenariat {conv.partner_type} — O'SCOP Outremer × {conv.partner_name}</p>
            <div className="rounded-xl p-4 max-h-80 overflow-y-auto text-xs text-white/80 whitespace-pre-wrap leading-relaxed"
              style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(217,179,90,0.2)' }} data-testid="partner-convention-content">
              {conv.content}
            </div>
            <div className="grid sm:grid-cols-2 gap-3">
              <input className={inp} placeholder="Nom du signataire *" data-testid="partner-sign-nom" value={sign.nom} onChange={(e) => setSign({ ...sign, nom: e.target.value })} />
              <input className={inp} placeholder="Qualité (Gérant…) *" data-testid="partner-sign-qualite" value={sign.qualite} onChange={(e) => setSign({ ...sign, qualite: e.target.value })} />
            </div>
            <label className="flex items-start gap-2.5 text-sm text-white/80 cursor-pointer">
              <input type="checkbox" checked={sign.lu_approuve} data-testid="partner-sign-checkbox"
                onChange={(e) => setSign({ ...sign, lu_approuve: e.target.checked })} className="mt-0.5 accent-[#D4AF37]" />
              <span>« Lu et approuvé » — j'accepte la présente convention. La signature électronique vaut signature manuscrite (art. 1366-1367 C. civ.).</span>
            </label>
            <button type="button" onClick={doSign} disabled={busy} data-testid="partner-sign-btn"
              className="w-full py-3.5 rounded-xl inline-flex items-center justify-center gap-2 text-sm font-bold disabled:opacity-50"
              style={{ background: 'linear-gradient(135deg, #D9B35A 0%, #b8933e 100%)', color: '#1F0A33' }}>
              {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileSignature className="w-4 h-4" />} Signer électroniquement
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
