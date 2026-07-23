import { useState } from 'react';
import { Truck, FileDown, Loader2, PenLine } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders, getSessionToken } from '../../../services/http';

export const downloadTransportPdf = async (path, filename) => {
  try {
    const r = await fetch(`${API}${path}`, {
      credentials: 'include', headers: { Authorization: `Bearer ${getSessionToken()}`, ...getAuthHeaders() },
    });
    if (!r.ok) throw new Error('Génération du PDF impossible');
    const blob = await r.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = filename; a.click();
    window.URL.revokeObjectURL(url);
  } catch (e) { toast.error(e.message); }
};

export const LogiscopSubscribeCard = ({ convention, zones, onChanged }) => {
  const [busy, setBusy] = useState(false);
  const [sig, setSig] = useState({ name: '', quality: '', place: '', approved: false });

  const call = async (path, body) => {
    const r = await fetch(`${API}${path}`, {
      method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getSessionToken()}`, ...getAuthHeaders() },
      body: body ? JSON.stringify(body) : undefined,
    });
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || 'Opération impossible');
    return d;
  };

  const subscribe = async () => {
    setBusy(true);
    try {
      await call('/logiscop-transport/subscribe');
      toast.success('Convention cadre LOGI\'SCOP générée — signez-la pour activer l\'option transport');
      onChanged();
    } catch (e) { toast.error(e.message); }
    setBusy(false);
  };

  const sign = async () => {
    setBusy(true);
    try {
      await call(`/logiscop-transport/convention/${convention.id}/sign`, sig);
      toast.success('Convention signée — vous pouvez émettre des Ordres de Transport');
      onChanged();
    } catch (e) { toast.error(e.message); }
    setBusy(false);
  };

  const inp = 'w-full h-9 px-3 rounded-lg bg-white/[0.06] border border-white/15 text-sm text-white placeholder:text-white/35';

  if (!convention) {
    return (
      <div className="rounded-xl p-5 bg-white/[0.03] border border-white/[0.08]" data-testid="logiscop-subscribe-card">
        <p className="flex items-center gap-2 text-sm font-semibold text-white/85 mb-2">
          <Truck className="w-4 h-4 text-[#D9B35A]" /> Option Transport routier LOGI'SCOP (Mode D)
        </p>
        <p className="text-xs text-white/55 mb-1">
          LOGI'SCOP agit comme <b>Transporteur Contractant</b> : il prend en charge, déplace et livre vos marchandises
          avec ses propres moyens, sous convention d'adhésion-cadre tripartite (V1.2).
        </p>
        <p className="text-[11px] text-white/40 mb-3">
          Zones couvertes par votre abonnement : <b className="text-[#E9CF8E]">{zones.join(', ') || 'aucune'}</b>
        </p>
        <button type="button" onClick={subscribe} disabled={busy || zones.length === 0} data-testid="logiscop-subscribe-btn"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold bg-[#D9B35A] text-[#1F0A33] hover:bg-[#c9a34a] disabled:opacity-50">
          {busy ? <Loader2 size={13} className="animate-spin" /> : <Truck size={13} />}
          Souscrire à l'option transport LOGI'SCOP
        </button>
      </div>
    );
  }

  return (
    <div className="rounded-xl p-5 bg-white/[0.03] border border-[#D9B35A]/30" data-testid="logiscop-sign-card">
      <p className="flex items-center gap-2 text-sm font-semibold text-white/85 mb-1">
        <PenLine className="w-4 h-4 text-[#D9B35A]" /> Signature de la Convention Cadre {convention.ref}
      </p>
      <p className="text-[11px] text-white/50 mb-3">
        Téléchargez et lisez la convention (Mode D V1.2 — zones {convention.zones.join(', ')}), puis signez-la électroniquement.
      </p>
      <button type="button" data-testid="logiscop-convention-pdf-btn"
        onClick={() => downloadTransportPdf(`/logiscop-transport/convention/${convention.id}/pdf`,
          `convention-logiscop-${convention.ref.replace(/\//g, '-')}.pdf`)}
        className="inline-flex items-center gap-1.5 px-3 py-1.5 mb-4 rounded-lg text-[11px] font-bold bg-white/[0.06] text-white/75 hover:text-[#E9CF8E] border border-white/15">
        <FileDown size={12} /> Télécharger la convention (PDF)
      </button>
      <div className="grid sm:grid-cols-3 gap-2 mb-3">
        <input className={inp} placeholder="Nom du signataire *" value={sig.name} data-testid="logiscop-sign-name"
          onChange={(e) => setSig({ ...sig, name: e.target.value })} />
        <input className={inp} placeholder="Qualité (ex. Gérant) *" value={sig.quality} data-testid="logiscop-sign-quality"
          onChange={(e) => setSig({ ...sig, quality: e.target.value })} />
        <input className={inp} placeholder="Fait à (lieu)" value={sig.place} data-testid="logiscop-sign-place"
          onChange={(e) => setSig({ ...sig, place: e.target.value })} />
      </div>
      <label className="flex items-center gap-2 text-xs text-white/70 mb-3 cursor-pointer">
        <input type="checkbox" checked={sig.approved} data-testid="logiscop-sign-approved"
          onChange={(e) => setSig({ ...sig, approved: e.target.checked })} className="accent-[#D9B35A]" />
        « Lu et approuvé » — j'accepte la Convention et ses Annexes au nom du Donneur d'Ordre
      </label>
      <button type="button" onClick={sign} data-testid="logiscop-sign-btn"
        disabled={busy || !sig.approved || sig.name.length < 2 || sig.quality.length < 2}
        className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold bg-[#D9B35A] text-[#1F0A33] hover:bg-[#c9a34a] disabled:opacity-50">
        {busy ? <Loader2 size={13} className="animate-spin" /> : <PenLine size={13} />} Signer électroniquement
      </button>
    </div>
  );
};
