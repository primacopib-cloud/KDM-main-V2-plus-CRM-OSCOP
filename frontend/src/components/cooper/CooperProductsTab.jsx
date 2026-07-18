import { useState, useEffect, useCallback } from 'react';
import { Loader2, Check, X, Package } from 'lucide-react';
import { toast } from 'sonner';
import { apiCall } from '../../services/http';

export const CooperProductsTab = () => {
  const [products, setProducts] = useState(null);

  const load = useCallback(() => {
    apiCall('/vendor/admin/products/pending').then((d) => setProducts(d.products || d || [])).catch((e) => {
      toast.error(e.message || 'Erreur de chargement');
      setProducts([]);
    });
  }, []);

  useEffect(() => { load(); }, [load]);

  const act = async (productId, action) => {
    try {
      await apiCall(`/vendor/admin/products/${productId}/${action}`, { method: 'POST', body: JSON.stringify({}) });
      toast.success(action === 'approve' ? 'Produit validé et publié au catalogue' : 'Produit rejeté');
      load();
    } catch (e) {
      toast.error(e.message || 'Erreur');
    }
  };

  if (products === null) return <div className="flex justify-center py-10"><Loader2 className="w-6 h-6 animate-spin text-[#6FA82E]" /></div>;

  return (
    <div className="space-y-3" data-testid="cooper-products-tab">
      {products.length === 0 ? (
        <div className="glass-panel-soft rounded-[18px] p-8 text-center text-sm opacity-60" data-testid="cooper-products-empty">
          Aucun produit vendeur en attente de validation.
        </div>
      ) : products.map((p) => (
        <div key={p.id} className="glass-panel-soft rounded-[18px] p-4 flex flex-wrap items-center gap-4" data-testid={`cooper-product-${p.id}`}>
          {p.images?.[0]?.url ? (
            <img src={p.images[0].url} alt={p.name} className="w-12 h-12 rounded-xl object-cover flex-shrink-0" />
          ) : (
            <div className="w-12 h-12 rounded-xl bg-black/5 flex items-center justify-center flex-shrink-0"><Package className="w-5 h-5 opacity-40" /></div>
          )}
          <div className="flex-1 min-w-[200px]">
            <p className="font-semibold text-sm">{p.name}</p>
            <p className="text-xs opacity-60">{p.vendor_name || p.vendor_id} · {p.category || '—'} · {p.price_ht ? `${p.price_ht} € HT` : ''}</p>
          </div>
          <div className="flex gap-2">
            <button onClick={() => act(p.id, 'approve')}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-[#6FA82E]/15 text-[#4d7a1c] border border-[#6FA82E]/40 hover:bg-[#6FA82E]/25 transition-colors"
              data-testid={`cooper-product-approve-${p.id}`}>
              <Check className="w-3.5 h-3.5" /> Valider
            </button>
            <button onClick={() => act(p.id, 'reject')}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-medium bg-red-500/10 text-red-600 border border-red-500/30 hover:bg-red-500/20 transition-colors"
              data-testid={`cooper-product-reject-${p.id}`}>
              <X className="w-3.5 h-3.5" /> Rejeter
            </button>
          </div>
        </div>
      ))}
    </div>
  );
};
