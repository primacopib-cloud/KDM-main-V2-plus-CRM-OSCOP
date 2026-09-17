import { useEffect, useState } from 'react';
import { Download, FileSignature, ScrollText } from 'lucide-react';
import { toast } from 'sonner';
import { detaillantAPI } from '../../services/api.detaillant';
import { API, getAuthHeaders } from '../../services/http';

export const downloadAuthedPdf = async (path, filename) => {
  const res = await fetch(`${API}${path}`, { headers: getAuthHeaders(), credentials: 'include' });
  if (!res.ok) { toast.error('PDF indisponible'); return; }
  const url = URL.createObjectURL(await res.blob());
  const a = document.createElement('a');
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
};

// Convention cadre de partenariat POP'S COOP'ACT : lecture + signature électronique
export const DetaillantConventionCard = ({ onSignedChange = () => {} }) => {
  const [data, setData] = useState(null);
  const [open, setOpen] = useState(false);
  const [name, setName] = useState('');
  const load = () => detaillantAPI.convention().then((d) => { setData(d); onSignedChange(d.signed); }).catch(() => {});
  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  if (!data) return null;

  const sign = async () => {
    try {
      await detaillantAPI.signConvention(name);
      toast.success('✓ Convention cadre signée électroniquement');
      setOpen(false);
      load();
    } catch (e) { toast.error(e.message); }
  };

  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4" data-testid="dt-convention-card">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-bold text-[#E9CF8E] flex items-center gap-2">
          <ScrollText className="w-4 h-4" /> Convention cadre de partenariat POP'S COOP'ACT (v{data.version})
        </h3>
        {data.signed && !data.needs_resign ? (
          <span className="flex items-center gap-2">
            <span className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-emerald-500/15 text-emerald-300 border border-emerald-400/40"
              data-testid="dt-convention-signed-badge">
              ✓ Signée par {data.signature?.signer_name} le {new Date(data.signature?.signed_at).toLocaleDateString('fr-FR')}
            </span>
            <button type="button" data-testid="dt-convention-pdf-btn"
              onClick={() => downloadAuthedPdf('/detaillant/convention/pdf', 'convention-pops-coopact.pdf')}
              title="Télécharger la convention signée en PDF horodaté"
              className="inline-flex items-center gap-1 h-7 px-2.5 rounded-lg text-[10px] font-bold border border-[#D9B35A]/50 text-[#F2D07A] hover:bg-[#D9B35A]/15">
              <Download className="w-3 h-3" /> PDF
            </button>
          </span>
        ) : data.needs_resign ? (
          <span className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-orange-500/15 text-orange-300 border border-orange-400/40"
            data-testid="dt-convention-resign-badge">
            ⚠️ Nouvelle version v{data.version} à re-signer (signée : v{data.signature?.version})
          </span>
        ) : (
          <span className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-amber-500/15 text-amber-300 border border-amber-400/40"
            data-testid="dt-convention-unsigned-badge">Signature requise avant abonnement</span>
        )}
      </div>
      <button type="button" onClick={() => setOpen((o) => !o)} data-testid="dt-convention-toggle"
        className="mt-2 text-[11px] font-semibold text-[#F2D07A] hover:underline">
        {open ? 'Masquer la convention' : 'Lire la convention complète'}
      </button>
      {open && (
        <div className="mt-3">
          <div className="max-h-72 overflow-y-auto rounded-xl bg-white/[0.03] border border-white/10 p-3 space-y-2"
            data-testid="dt-convention-text">
            <p className="text-[11px] text-white/70">{data.parties}</p>
            {data.articles.map((a) => (
              <div key={a.title}>
                <p className="text-[11px] font-bold text-white/85">{a.title}</p>
                <p className="text-[11px] text-white/60">{a.text}</p>
              </div>
            ))}
          </div>
          {(!data.signed || data.needs_resign) && (
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <input value={name} onChange={(e) => setName(e.target.value)}
                placeholder="Nom complet du signataire" data-testid="dt-convention-signer-input"
                className="h-9 px-3 rounded-lg bg-white/[0.05] border border-white/15 text-xs text-white placeholder-white/30 outline-none flex-1 min-w-[200px]" />
              <button type="button" onClick={sign} disabled={name.trim().length < 3}
                data-testid="dt-convention-sign-btn"
                className="inline-flex items-center gap-1.5 h-9 px-4 rounded-full bg-[#D9B35A] text-black text-xs font-bold hover:bg-[#E9CF8E] disabled:opacity-40">
                <FileSignature className="w-3.5 h-3.5" /> Je signe la convention
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
