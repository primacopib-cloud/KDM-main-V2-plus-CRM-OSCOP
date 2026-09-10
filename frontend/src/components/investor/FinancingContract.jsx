import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { FileSignature, Download, Loader2, CheckCircle2, Clock, X } from 'lucide-react';
import { getAuthHeaders } from '../../services/http';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const inputCls = 'w-full rounded-lg bg-white/[0.06] border border-white/15 px-3 py-2 text-sm text-white placeholder-white/30 focus:outline-none focus:border-[#D9B35A]/60';

export const FinancingContract = ({ fp }) => {
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState(null);
  const [busy, setBusy] = useState(false);
  const [f, setF] = useState({ denomination: '', forme_capital: '', immatriculation: '', adresse: '', rep_nom: '', rep_qualite: '', lu_approuve: false });

  const loadStatus = () => fetch(`${API_URL}/api/public/financing-contract/verify/${fp.id}`)
    .then((r) => (r.ok ? r.json() : null)).then(setStatus).catch(() => {});

  useEffect(() => { if (open) loadStatus(); }, [open]); // eslint-disable-line react-hooks/exhaustive-deps

  const download = async (lang) => {
    try {
      const r = await fetch(`${API_URL}/api/product-financing/${fp.id}/contract.pdf?lang=${lang}`, { headers: getAuthHeaders(), credentials: 'include' });
      if (!r.ok) throw new Error();
      const blob = await r.blob();
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `convention-financement-${fp.reference}-${lang}.pdf`;
      a.click();
      URL.revokeObjectURL(a.href);
    } catch { toast.error('Convention indisponible'); }
  };

  const sign = async () => {
    if (!f.lu_approuve || !f.denomination || !f.rep_nom || !f.rep_qualite) {
      return toast.error('Complétez tous les champs obligatoires et cochez « Lu et approuvé »');
    }
    setBusy(true);
    try {
      const r = await fetch(`${API_URL}/api/product-financing/${fp.id}/contract/sign`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        credentials: 'include', body: JSON.stringify(f),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Erreur');
      toast.success(`Convention signée électroniquement — code ${d.verification_code}`);
      loadStatus();
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };

  return (
    <>
      <button type="button" onClick={() => setOpen(true)} data-testid={`fin-contract-btn-${fp.reference}`}
        className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-[8px] text-[11px] font-bold text-violet-200 bg-violet-500/15 border border-violet-400/40 hover:bg-violet-500/25 transition-colors">
        <FileSignature className="w-3 h-3" /> Convention
      </button>
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" data-testid="fin-contract-modal">
          <div className="w-full max-w-[520px] max-h-[88vh] overflow-y-auto rounded-2xl border border-[#D9B35A]/30 bg-[#241243] p-5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <FileSignature className="w-4 h-4 text-[#D9B35A]" /> Convention de financement — {fp.reference}
              </h3>
              <button type="button" onClick={() => setOpen(false)} className="text-white/50 hover:text-white" data-testid="fin-contract-close"><X className="w-4 h-4" /></button>
            </div>
            <div className="space-y-1.5 mb-4 text-[11px]">
              <p className="m-0 flex items-center gap-1.5 text-white/75">
                {status?.signature_financeur ? <CheckCircle2 className="w-3.5 h-3.5 text-[#8CC63E]" /> : <Clock className="w-3.5 h-3.5 text-[#FBBF24]" />}
                <span data-testid="fin-contract-sig-investor">Financeur {status?.signature_financeur ? `— signé (${status.signature_financeur.verification_code})` : '— en attente de votre signature'}</span>
              </p>
              <p className="m-0 flex items-center gap-1.5 text-white/75">
                {status?.signature_oscop ? <CheckCircle2 className="w-3.5 h-3.5 text-[#8CC63E]" /> : <Clock className="w-3.5 h-3.5 text-[#FBBF24]" />}
                <span data-testid="fin-contract-sig-oscop">O'SCOP (Débiteur) {status?.signature_oscop ? `— contresigné (${status.signature_oscop.verification_code})` : '— en attente de contresignature'}</span>
              </p>
            </div>
            <div className="flex gap-2 mb-4">
              {['fr', 'en'].map((lang) => (
                <button key={lang} type="button" onClick={() => download(lang)} data-testid={`fin-contract-dl-${lang}`}
                  className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs font-bold text-[#E9CF8E] bg-[#D9B35A]/15 border border-[#D9B35A]/40 hover:bg-[#D9B35A]/25">
                  <Download className="w-3.5 h-3.5" /> PDF {lang.toUpperCase()}
                </button>
              ))}
              <a href={`/verifier-financement/${fp.id}`} target="_blank" rel="noreferrer" data-testid="fin-contract-verify"
                className="inline-flex items-center px-3 py-2 rounded-lg text-xs font-bold text-sky-200 bg-sky-500/15 border border-sky-400/40 hover:bg-sky-500/25">
                Vérifier
              </a>
            </div>
            {!status?.signature_financeur && (
              <div className="space-y-2.5 border-t border-white/10 pt-3">
                <p className="text-[11px] text-white/55 m-0">Vos informations de Financeur (reportées dans la convention) :</p>
                <input className={inputCls} placeholder="Nom ou dénomination sociale *" value={f.denomination} data-testid="fin-contract-denomination"
                  onChange={(e) => setF({ ...f, denomination: e.target.value })} />
                <input className={inputCls} placeholder="Forme juridique et capital (ex : SARL au capital de 10 000 € / personne physique)" value={f.forme_capital} data-testid="fin-contract-forme"
                  onChange={(e) => setF({ ...f, forme_capital: e.target.value })} />
                <input className={inputCls} placeholder="Numéro d'immatriculation (SIRET, le cas échéant)" value={f.immatriculation} data-testid="fin-contract-immat"
                  onChange={(e) => setF({ ...f, immatriculation: e.target.value })} />
                <input className={inputCls} placeholder="Adresse ou siège" value={f.adresse} data-testid="fin-contract-adresse"
                  onChange={(e) => setF({ ...f, adresse: e.target.value })} />
                <div className="grid grid-cols-2 gap-2">
                  <input className={inputCls} placeholder="Représenté par (nom) *" value={f.rep_nom} data-testid="fin-contract-rep-nom"
                    onChange={(e) => setF({ ...f, rep_nom: e.target.value })} />
                  <input className={inputCls} placeholder="En qualité de *" value={f.rep_qualite} data-testid="fin-contract-rep-qualite"
                    onChange={(e) => setF({ ...f, rep_qualite: e.target.value })} />
                </div>
                <label className="flex items-start gap-2 text-[11px] text-white/80 cursor-pointer">
                  <input type="checkbox" checked={f.lu_approuve} data-testid="fin-contract-lu"
                    onChange={(e) => setF({ ...f, lu_approuve: e.target.checked })} className="mt-0.5 accent-[#D4AF37]" />
                  <span>« Lu et approuvé » — je signe électroniquement la convention (règlement eIDAS n° 910/2014, art. 1367 du Code civil)</span>
                </label>
                <button type="button" onClick={sign} disabled={busy} data-testid="fin-contract-sign-btn"
                  className="w-full py-2.5 rounded-xl inline-flex items-center justify-center gap-2 text-sm font-bold disabled:opacity-50"
                  style={{ background: 'linear-gradient(135deg, #D9B35A 0%, #b8933e 100%)', color: '#1F0A33' }}>
                  {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileSignature className="w-4 h-4" />} Signer la convention
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
};
