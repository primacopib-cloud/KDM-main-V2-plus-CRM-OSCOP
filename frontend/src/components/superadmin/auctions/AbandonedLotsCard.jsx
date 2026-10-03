import { useEffect, useState } from 'react';
import { HandHeart, PackageX, RotateCcw } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../../services/http';

// Superadmin : lots remportés jamais retirés (règle J+30) — remise en salle ou don solidaire
export const AbandonedLotsCard = () => {
  const [data, setData] = useState(null);

  const load = () => fetch(`${API}/admin/auctions/abandoned`, {
    credentials: 'include', headers: getAuthHeaders(),
  }).then((r) => r.json()).then(setData).catch(() => setData(null));

  useEffect(() => { load(); }, []);

  const resolve = async (id, action) => {
    try {
      const r = await fetch(`${API}/admin/auctions/abandoned/${id}/resolve`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ action }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Erreur');
      toast.success(action === 'RELIST' ? `Lot remis en salle ✓ (${d.new_reference})` : `Don enregistré ✓ — ${d.don}`);
      load();
    } catch (e) {
      toast.error(e.message);
    }
  };

  if (!data || !(data.abandoned || []).length) return null;
  return (
    <div className="rounded-xl border border-red-400/20 bg-red-500/[0.04] p-3 mb-4" data-testid="abandoned-lots-card">
      <p className="text-[11px] font-bold text-red-300 uppercase mb-1 flex items-center gap-1">
        <PackageX className="w-3.5 h-3.5" /> Lots abandonnés (règle J+30) — {data.pending_count} à trancher
      </p>
      <p className="text-[10px] text-white/50 mb-2">
        Non retirés sous 30 jours : crédits du gagnant définitivement engagés, lot à remettre en salle ou à donner.
      </p>
      <div className="space-y-1.5 max-h-56 overflow-y-auto">
        {data.abandoned.map((i) => (
          <div key={i.id} className="rounded-lg border border-white/10 p-2 text-[10.5px] text-white/70"
            data-testid={`abandoned-lot-${i.id}`}>
            <p>
              <b className="text-[#E9CF8E]">{i.title}</b> · {i.reference} — {i.pops_name || "POP'S"}
              <span className="text-white/40"> · gagné par {i.winner_name} ({Number(i.paid_eur || 0).toFixed(2)} €)</span>
            </p>
            {i.action === 'PENDING' ? (
              <span className="inline-flex gap-1.5 mt-1">
                <button onClick={() => resolve(i.id, 'RELIST')} data-testid={`abandoned-relist-${i.id}`}
                  className="inline-flex items-center gap-1 px-2.5 h-6 rounded-full text-[10px] font-bold text-[#E9CF8E] border border-[#D9B35A]/40 bg-[#D9B35A]/10 hover:bg-[#D9B35A]/20">
                  <RotateCcw className="w-3 h-3" /> Remettre en salle
                </button>
                <button onClick={() => resolve(i.id, 'DON')} data-testid={`abandoned-don-${i.id}`}
                  className="inline-flex items-center gap-1 px-2.5 h-6 rounded-full text-[10px] font-bold text-emerald-300 border border-emerald-400/40 bg-emerald-500/10 hover:bg-emerald-500/20">
                  <HandHeart className="w-3 h-3" /> Don solidaire
                </button>
              </span>
            ) : (
              <p className="mt-1 font-bold text-emerald-300" data-testid={`abandoned-resolved-${i.id}`}>
                ✓ {i.action === 'RELIST' ? `Remis en salle (${i.resolution?.new_reference})` : `Don — ${i.resolution?.note}`}
                {' '}le {new Date(i.resolution?.at).toLocaleDateString('fr-FR')}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
