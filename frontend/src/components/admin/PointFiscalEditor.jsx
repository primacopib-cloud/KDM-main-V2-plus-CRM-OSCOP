import { useState } from 'react';
import { toast } from 'sonner';
import { Landmark, Loader2 } from 'lucide-react';
import { lolodriveAPI } from '../../services/api';

// Super admin : SIRET + N° TVA du relais (affichés sur les tickets de caisse)
export const PointFiscalEditor = ({ point }) => {
  const [siret, setSiret] = useState(point.siret || '');
  const [vat, setVat] = useState(point.vat_number || '');
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    try {
      await lolodriveAPI.adminUpdatePoint(point.id, { siret: siret.trim(), vat_number: vat.trim() });
      toast.success('Infos fiscales enregistrées — visibles sur les tickets ✓');
    } catch (e) { toast.error(e.message); } finally { setSaving(false); }
  };

  return (
    <div className="rounded-lg bg-white/[0.03] border border-white/[0.06] p-2.5 mb-3" data-testid={`fiscal-editor-${point.code}`}>
      <div className="text-[10px] font-semibold text-white/50 flex items-center gap-1 mb-1.5">
        <Landmark className="w-3 h-3" /> Infos fiscales (tickets de caisse)
      </div>
      <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
        <input value={siret} onChange={(e) => setSiret(e.target.value)} placeholder="SIRET"
          data-testid={`siret-input-${point.code}`}
          className="flex-1 min-w-[120px] bg-white/5 border border-white/10 rounded px-2 py-1 text-white font-mono" />
        <input value={vat} onChange={(e) => setVat(e.target.value)} placeholder="N° TVA (FRxx…)"
          data-testid={`vat-input-${point.code}`}
          className="flex-1 min-w-[120px] bg-white/5 border border-white/10 rounded px-2 py-1 text-white font-mono" />
        <button type="button" onClick={save} disabled={saving} data-testid={`fiscal-save-${point.code}`}
          className="px-2.5 py-1 rounded text-[11px] font-bold text-black bg-[#D9B35A] hover:bg-[#c9a34a] disabled:opacity-60">
          {saving ? <Loader2 className="w-3 h-3 animate-spin" /> : 'OK'}
        </button>
      </div>
    </div>
  );
};
