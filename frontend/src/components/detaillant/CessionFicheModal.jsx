import { useEffect, useState } from 'react';
import { FileSignature, X } from 'lucide-react';
import { toast } from 'sonner';
import { detaillantAPI } from '../../services/api.detaillant';

const fmt = (iso) => (iso ? new Date(iso).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' }) : '—');
const STATUS = { DRAFT: ['À signer', 'text-amber-300 border-amber-400/40 bg-amber-500/15'],
  SIGNED: ['Signée', 'text-emerald-300 border-emerald-400/40 bg-emerald-500/15'],
  EFFECTIVE: ['En vigueur', 'text-[#F2D07A] border-[#D9B35A]/50 bg-[#D9B35A]/15'] };

// Fiche de cession universelle POP'S COOP'ACT : rubriques par catégorie + horodatage + signature
export const CessionFicheModal = ({ offerId, onClose, onSigned = () => {} }) => {
  const [c, setC] = useState(null);
  const [checked, setChecked] = useState([]);
  const [name, setName] = useState('');
  useEffect(() => {
    detaillantAPI.cession(offerId).then((d) => { setC(d); setChecked(d.declarations_checked || []); })
      .catch((e) => { toast.error(e.message); onClose(); });
  }, [offerId]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!c) return null;
  const [stLabel, stCls] = STATUS[c.status] || STATUS.DRAFT;
  const toggle = (d) => setChecked((l) => (l.includes(d) ? l.filter((x) => x !== d) : [...l, d]));
  const sign = async () => {
    try {
      await detaillantAPI.signCession(offerId, { signer_name: name, declarations_checked: checked });
      toast.success('✓ Fiche de cession signée — votre offre peut être validée');
      onSigned();
      onClose();
    } catch (e) { toast.error(e.message); }
  };

  return (
    <div className="fixed inset-0 z-[80] bg-black/70 flex items-center justify-center p-4" onClick={onClose}>
      <div className="w-full max-w-2xl max-h-[85vh] overflow-y-auto rounded-2xl bg-[#2c1247] border border-white/15 p-5"
        onClick={(e) => e.stopPropagation()} data-testid="cession-fiche-modal">
        <div className="flex items-start justify-between gap-2">
          <div>
            <h3 className="text-sm font-bold text-[#E9CF8E]">Fiche de cession de produits et lots</h3>
            <p className="text-[10px] text-white/45">Formulaire universel POP'S COOP'ACT · Réf. {c.reference}</p>
          </div>
          <div className="flex items-center gap-2">
            <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${stCls}`} data-testid="cession-status">{stLabel}</span>
            <button onClick={onClose} className="text-white/50 hover:text-white" data-testid="cession-close"><X className="w-4 h-4" /></button>
          </div>
        </div>

        <div className="mt-3 grid sm:grid-cols-2 gap-3 text-[11px]">
          <div className="rounded-xl bg-white/[0.04] p-3">
            <p className="font-bold text-white/80 mb-1">Cédant — Partenaire POP'S</p>
            <p className="text-white/60">{c.cedant.company_name} · {c.cedant.locality} ({c.cedant.country_code})</p>
            {c.cedant.siret && <p className="text-white/45">SIREN/SIRET : {c.cedant.siret}</p>}
          </div>
          <div className="rounded-xl bg-white/[0.04] p-3">
            <p className="font-bold text-white/80 mb-1">Cessionnaire</p>
            <p className="text-white/60">{c.cessionnaire}</p>
          </div>
        </div>

        <div className="mt-3 rounded-xl bg-white/[0.04] p-3 text-[11px]">
          <p className="font-bold text-white/80 mb-1">Nature du lot</p>
          <p className="text-white/60">{c.lot_designation} — {c.qty_lots} lot(s) ×3 {c.lot_type === 'COMPOSED' ? '(composé)' : ''} · Catégorie : {c.category || '—'} · État : {c.condition === 'NEW' ? 'Neuf' : 'Occasion'}</p>
          <table className="w-full mt-2 text-[10px]">
            <thead><tr className="text-white/40 text-left"><th className="pr-2">Réf.</th><th className="pr-2">Désignation</th><th className="pr-2">Qté</th><th>DLC/DDM</th></tr></thead>
            <tbody>
              {c.products.map((p) => (
                <tr key={p.sku} className="text-white/65 border-t border-white/[0.06]">
                  <td className="pr-2 py-1">{p.sku}</td><td className="pr-2">{p.name}</td>
                  <td className="pr-2">{p.qty}</td><td>{p.dlc ? p.dlc.split('-').reverse().join('/') : 'N/A'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-3 grid sm:grid-cols-2 gap-3 text-[11px]">
          <div className="rounded-xl bg-white/[0.04] p-3">
            <p className="font-bold text-white/80 mb-1">Valorisation financière</p>
            <p className="text-white/60">Prix boutique : {c.valuation.lot_price} {c.valuation.currency}</p>
            <p className="text-white/60">Remise : −{Number(c.valuation.discount_pct).toFixed(0)} % → <b className="text-[#E9CF8E]">{c.valuation.final_price} {c.valuation.currency}</b></p>
            {c.valuation.warranty && <p className="text-white/45">Garantie : {c.valuation.warranty}</p>}
          </div>
          <div className="rounded-xl bg-white/[0.04] p-3" data-testid="cession-dates">
            <p className="font-bold text-white/80 mb-1">Effet et expiration (horodatés)</p>
            <p className="text-white/60">Date d'effet (ouverture en salle) : <b>{fmt(c.effective_from)}</b></p>
            <p className="text-white/60">Expiration (fin de l'offre) : <b>{fmt(c.effective_until)}</b></p>
            {!c.effective_from && <p className="text-[10px] text-white/40 mt-1">Horodaté automatiquement à la validation de l'offre.</p>}
          </div>
        </div>

        <div className="mt-3 rounded-xl bg-white/[0.04] p-3">
          <p className="text-[11px] font-bold text-white/80 mb-2">Déclarations et contrôles applicables ({c.category || 'catégorie générale'})</p>
          <div className="space-y-1.5">
            {c.declarations.map((d) => (
              <label key={d} className="flex items-start gap-2 text-[11px] text-white/70 cursor-pointer">
                <input type="checkbox" checked={checked.includes(d)} disabled={c.status !== 'DRAFT'}
                  onChange={() => toggle(d)} data-testid={`cession-decl-${c.declarations.indexOf(d)}`}
                  className="mt-0.5 accent-[#D9B35A]" />
                {d}
              </label>
            ))}
          </div>
        </div>

        {c.status === 'DRAFT' ? (
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <input value={name} onChange={(e) => setName(e.target.value)}
              placeholder="Nom du signataire (Bon pour accord)" data-testid="cession-signer-input"
              className="h-9 px-3 rounded-lg bg-white/[0.05] border border-white/15 text-xs text-white placeholder-white/30 outline-none flex-1 min-w-[200px]" />
            <button type="button" onClick={sign}
              disabled={name.trim().length < 3 || checked.length < c.declarations.length}
              data-testid="cession-sign-btn"
              className="inline-flex items-center gap-1.5 h-9 px-4 rounded-full bg-[#D9B35A] text-black text-xs font-bold hover:bg-[#E9CF8E] disabled:opacity-40">
              <FileSignature className="w-3.5 h-3.5" /> Bon pour accord — je signe
            </button>
          </div>
        ) : (
          <p className="mt-3 text-[10px] text-white/45" data-testid="cession-signature-info">
            Signée par {c.signer_name} le {fmt(c.signed_at)} — mention « Bon pour accord ».
          </p>
        )}
      </div>
    </div>
  );
};
