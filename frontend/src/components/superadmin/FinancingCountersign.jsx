import { useState } from 'react';
import { toast } from 'sonner';
import { FileSignature, Loader2, X } from 'lucide-react';
import { getAuthHeaders } from '../../services/http';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const inputCls = 'w-full rounded-lg bg-white/[0.06] border border-white/15 px-3 py-2 text-sm text-white placeholder-white/30 focus:outline-none focus:border-[#D9B35A]/60';

export const FinancingCountersign = ({ fp, onDone }) => {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [f, setF] = useState({ rep_nom: '', rep_qualite: '', lu_approuve: false });

  const countersign = async () => {
    if (!f.lu_approuve || !f.rep_nom || !f.rep_qualite) {
      return toast.error('Complétez le nom, la qualité et cochez « Lu et approuvé »');
    }
    setBusy(true);
    try {
      const r = await fetch(`${API_URL}/api/product-financing/${fp.id}/contract/countersign`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', ...getAuthHeaders() }, credentials: 'include',
        body: JSON.stringify(f),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Erreur');
      toast.success(`Contresigné pour O'SCOP — code ${d.verification_code}`);
      setOpen(false);
      onDone?.();
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };

  return (
    <>
      <button type="button" onClick={() => setOpen(true)} data-testid={`fin-countersign-${fp.reference}`}
        title="Contresigner la convention de financement au nom d'O'SCOP"
        className="inline-flex items-center gap-1 px-2 py-1 rounded-md font-semibold text-violet-300 bg-violet-500/10 border border-violet-400/40 hover:bg-violet-500/20">
        <FileSignature className="w-3 h-3" /> Convention
      </button>
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" data-testid="fin-countersign-modal">
          <div className="w-full max-w-[440px] rounded-2xl border border-[#D9B35A]/30 bg-[#241243] p-5 space-y-2.5">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-white">Contresignature O'SCOP — {fp.reference}</h3>
              <button type="button" onClick={() => setOpen(false)} className="text-white/50 hover:text-white"><X className="w-4 h-4" /></button>
            </div>
            <p className="text-[11px] text-white/55 m-0">Convention de financement ponctuel — signature du Débiteur (règlement eIDAS n° 910/2014).</p>
            <input className={inputCls} placeholder="Nom du signataire O'SCOP *" value={f.rep_nom} data-testid="fin-countersign-nom"
              onChange={(e) => setF({ ...f, rep_nom: e.target.value })} />
            <input className={inputCls} placeholder="Qualité (ex : Présidente de la SCIC) *" value={f.rep_qualite} data-testid="fin-countersign-qualite"
              onChange={(e) => setF({ ...f, rep_qualite: e.target.value })} />
            <label className="flex items-start gap-2 text-[11px] text-white/80 cursor-pointer">
              <input type="checkbox" checked={f.lu_approuve} data-testid="fin-countersign-lu"
                onChange={(e) => setF({ ...f, lu_approuve: e.target.checked })} className="mt-0.5 accent-[#D4AF37]" />
              <span>« Lu et approuvé » — signature électronique au nom d'O'SCOP</span>
            </label>
            <button type="button" onClick={countersign} disabled={busy} data-testid="fin-countersign-submit"
              className="w-full py-2.5 rounded-xl inline-flex items-center justify-center gap-2 text-sm font-bold disabled:opacity-50"
              style={{ background: 'linear-gradient(135deg, #D9B35A 0%, #b8933e 100%)', color: '#1F0A33' }}>
              {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileSignature className="w-4 h-4" />} Contresigner
            </button>
          </div>
        </div>
      )}
    </>
  );
};
