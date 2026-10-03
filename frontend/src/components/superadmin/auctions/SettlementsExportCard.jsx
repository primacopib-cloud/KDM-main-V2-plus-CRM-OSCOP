import { useState } from 'react';
import { FileSpreadsheet } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../../services/http';

// Superadmin : export CSV comptable mensuel des règlements POP'S et avoirs
export const SettlementsExportCard = () => {
  const [month, setMonth] = useState(new Date().toISOString().slice(0, 7));

  const download = async () => {
    try {
      const r = await fetch(`${API}/admin/auctions/settlements/export.csv?month=${month}`, {
        credentials: 'include', headers: getAuthHeaders(),
      });
      if (!r.ok) {
        const d = await r.json().catch(() => ({}));
        throw new Error(d.detail || 'Erreur export');
      }
      const blob = await r.blob();
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `reglements-pops-${month}.csv`;
      a.click();
      URL.revokeObjectURL(a.href);
      toast.success('Export comptable téléchargé ✓');
    } catch (e) {
      toast.error(e.message);
    }
  };

  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3 mb-4 flex flex-wrap items-center gap-2"
      data-testid="settlements-export-card">
      <p className="text-[11px] font-bold text-white/60 uppercase flex items-center gap-1 mr-2">
        <FileSpreadsheet className="w-3.5 h-3.5 text-[#D9B35A]" /> Export comptable — règlements POP'S &amp; avoirs
      </p>
      <input type="month" value={month} onChange={(e) => setMonth(e.target.value)}
        data-testid="settlements-export-month"
        className="h-8 px-2 rounded-lg bg-white/[0.05] border border-white/15 text-white text-xs" />
      <button onClick={download} data-testid="settlements-export-btn"
        className="px-3 h-8 rounded-full text-[11px] font-bold text-[#E9CF8E] border border-[#D9B35A]/40 hover:bg-[#D9B35A]/15">
        Télécharger CSV
      </button>
    </div>
  );
};
