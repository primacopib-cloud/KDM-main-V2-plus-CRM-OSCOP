import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { PackageCheck, Check, X } from 'lucide-react';
import { Button } from '../ui/button';
import { lolodriveAPI } from '../../services/api';

export const RelayProductsQueue = () => {
  const [pending, setPending] = useState([]);
  const [acting, setActing] = useState(null);

  const load = () => { lolodriveAPI.adminRelayProducts('PENDING').then((d) => setPending(d.products || [])).catch(() => {}); };
  useEffect(() => { load(); }, []);

  const review = async (sku, action) => {
    let reason;
    if (action === 'reject') {
      reason = window.prompt('Motif du refus (transmis au gérant) :') || undefined;
    }
    setActing(sku);
    try {
      await lolodriveAPI.adminReviewRelayProduct(sku, action, reason);
      toast.success(action === 'approve' ? 'Produit approuvé — en ligne ✓' : 'Produit refusé');
      load();
    } catch (e) { toast.error(e.message); } finally { setActing(null); }
  };

  if (pending.length === 0) return null;
  return (
    <div className="mb-6 rounded-2xl border border-amber-400/35 bg-amber-400/[0.05] p-4" data-testid="relay-products-queue">
      <div className="font-semibold text-amber-300 flex items-center gap-2 mb-3">
        <PackageCheck className="w-4 h-4" />
        {pending.length} fiche(s) produit relais à valider
      </div>
      <div className="space-y-2">
        {pending.map((p) => (
          <div key={p.sku} className="flex flex-wrap items-center gap-3 p-3 rounded-xl bg-black/25 border border-white/[0.06]"
            data-testid={`pending-product-${p.sku}`}>
            <div className="flex-1 min-w-[220px]">
              <div className="text-sm font-semibold">{p.name} <span className="text-white/40 font-normal">— {(p.price_public_cents / 100).toFixed(2)} €</span></div>
              <div className="text-[11px] text-white/50">
                {p.point_code} · {p.category}{p.brand ? ` · ${p.brand}` : ''} — {p.description}
              </div>
            </div>
            <div className="flex gap-2 shrink-0">
              <Button size="sm" disabled={acting === p.sku} onClick={() => review(p.sku, 'approve')}
                className="bg-emerald-600 hover:bg-emerald-500 text-white" data-testid={`approve-${p.sku}`}>
                <Check className="w-3 h-3 mr-1" /> Approuver
              </Button>
              <Button size="sm" variant="outline" disabled={acting === p.sku} onClick={() => review(p.sku, 'reject')}
                className="border-red-400/40 text-red-300 hover:bg-red-500/10" data-testid={`reject-${p.sku}`}>
                <X className="w-3 h-3 mr-1" /> Refuser
              </Button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
