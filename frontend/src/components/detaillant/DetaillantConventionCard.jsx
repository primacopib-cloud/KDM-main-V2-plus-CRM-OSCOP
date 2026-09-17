import { useEffect, useState } from 'react';
import { FileSignature, ScrollText } from 'lucide-react';
import { toast } from 'sonner';
import { detaillantAPI } from '../../services/api.detaillant';

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
        {data.signed ? (
          <span className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-emerald-500/15 text-emerald-300 border border-emerald-400/40"
            data-testid="dt-convention-signed-badge">
            ✓ Signée par {data.signature?.signer_name} le {new Date(data.signature?.signed_at).toLocaleDateString('fr-FR')}
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
          {!data.signed && (
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
