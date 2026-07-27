import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Coins, Check } from 'lucide-react';
import { lolodriveAPI } from '../../services/api';

export const RelayFeeSetting = () => {
  const [fee, setFee] = useState(null);
  const [value, setValue] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    lolodriveAPI.adminGetRelayFee().then((d) => { setFee(d.fee_uc); setValue(String(d.fee_uc)); }).catch(() => {});
  }, []);

  const save = async () => {
    const v = parseFloat(String(value).replace(',', '.'));
    if (Number.isNaN(v) || v < 0) return toast.error('Valeur UC invalide');
    setSaving(true);
    try {
      const r = await lolodriveAPI.adminSetRelayFee(v);
      setFee(r.fee_uc);
      setValue(String(r.fee_uc));
      toast.success(`Frais produits relais mis à jour : ${r.fee_uc} UC / produit vendu ✓`);
    } catch (e) { toast.error(e.message); } finally { setSaving(false); }
  };

  if (fee === null) return null;
  return (
    <div className="mb-6 rounded-2xl border border-[#7c3aed]/35 bg-[#7c3aed]/[0.06] p-4 flex flex-wrap items-center gap-3"
      data-testid="relay-fee-setting">
      <span className="flex items-center gap-2 font-semibold text-[#c4b5fd] text-sm">
        <Coins className="w-4 h-4" /> Frais UC produits relais (CREDI'SCOP)
      </span>
      <span className="text-xs text-white/50 flex-1 min-w-[240px]">
        Chaque produit soumis par un gérant (hors catalogue KDMARCHÉ) vendu au comptoir débite cette valeur × quantité du CREDI'SCOP du gérant.
      </span>
      <span className="flex items-center gap-2 shrink-0">
        <input type="number" min="0" step="0.5" value={value} data-testid="relay-fee-input"
          onChange={(e) => setValue(e.target.value)}
          className="w-20 px-2 py-1 rounded-lg bg-white/5 border border-[#7c3aed]/40 text-white text-sm font-mono" />
        <span className="text-xs text-white/60">UC / produit</span>
        <button type="button" onClick={save} disabled={saving} data-testid="relay-fee-save-btn"
          className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold text-white bg-[#7c3aed] hover:bg-[#6d28d9] disabled:opacity-50">
          <Check className="w-3 h-3" /> Enregistrer
        </button>
      </span>
    </div>
  );
};
