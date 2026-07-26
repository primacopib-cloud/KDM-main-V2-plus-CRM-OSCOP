import { useEffect, useState } from 'react';
import { Share2, Loader2, AlertTriangle } from 'lucide-react';
import { API, getAuthHeaders } from '../../services/http';

export const SharePreviewTester = () => {
  const [kind, setKind] = useState('home');
  const [productId, setProductId] = useState('');
  const [products, setProducts] = useState([]);
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const opts = { headers: getAuthHeaders(), credentials: 'include' };

  useEffect(() => {
    fetch(`${API}/admin/share-preview/products`, opts)
      .then((r) => (r.ok ? r.json() : { products: [] }))
      .then((d) => setProducts(d.products || []))
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const test = async () => {
    setBusy(true); setError(''); setPreview(null);
    try {
      const q = kind === 'product' ? `?kind=product&product_id=${productId}` : '?kind=home';
      const r = await fetch(`${API}/admin/share-preview${q}`, opts);
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Erreur');
      setPreview(d);
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  };

  const selectCls = 'h-9 rounded-lg px-2.5 text-xs text-white bg-white/[0.06] border border-white/15 focus:outline-none';
  return (
    <div className="glass-panel-soft rounded-[18px] p-4" data-testid="share-preview-tester">
      <h3 className="text-sm font-semibold text-[#D9B35A] flex items-center gap-2 mb-1">
        <Share2 className="w-4 h-4" /> Testeur d'aperçu de partage
      </h3>
      <p className="text-[11px] text-white/45 mb-3">Visualisez la carte affichée sur WhatsApp / LinkedIn lors du partage du site ou d'une fiche produit.</p>
      <div className="flex flex-wrap items-center gap-2 mb-4">
        <select value={kind} onChange={(e) => setKind(e.target.value)} className={selectCls} data-testid="share-preview-kind">
          <option value="home">Racine du site</option>
          <option value="product">Fiche produit</option>
        </select>
        {kind === 'product' && (
          <select value={productId} onChange={(e) => setProductId(e.target.value)} className={selectCls} data-testid="share-preview-product">
            <option value="">— Choisir un produit —</option>
            {products.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        )}
        <button type="button" onClick={test} disabled={busy || (kind === 'product' && !productId)}
          data-testid="share-preview-test-btn"
          className="h-9 px-4 rounded-lg text-xs font-bold disabled:opacity-40 inline-flex items-center gap-1.5"
          style={{ background: 'linear-gradient(135deg,#D9B35A,#b8933e)', color: '#1F0A33' }}>
          {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null} Tester l'aperçu
        </button>
      </div>
      {error && <p className="text-xs text-red-400 flex items-center gap-1.5"><AlertTriangle className="w-3.5 h-3.5" /> {error}</p>}
      {preview && (
        <div className="max-w-sm rounded-xl overflow-hidden border border-white/10" style={{ background: '#0b141a' }} data-testid="share-preview-card">
          {preview.image
            ? <img src={preview.image} alt="Aperçu OG" className="w-full h-44 object-cover" data-testid="share-preview-image" />
            : <div className="w-full h-24 flex items-center justify-center text-xs text-white/40 bg-white/[0.04]">Aucune image og:image détectée</div>}
          <div className="p-3">
            <p className="text-[13px] font-semibold text-white/90 leading-snug" data-testid="share-preview-title">{preview.title || 'Sans titre'}</p>
            {preview.description && <p className="text-[11.5px] text-white/55 mt-1 line-clamp-2">{preview.description}</p>}
            <p className="text-[10.5px] text-white/35 mt-1.5 uppercase">{preview.domain}</p>
          </div>
          <div className="px-3 pb-2.5 flex flex-wrap gap-2 text-[10px]">
            <span className={preview.image_absolute ? 'text-emerald-400' : 'text-amber-400'}>
              {preview.image_absolute ? '✓ image en URL absolue' : '⚠ image en URL relative (risque de non-affichage)'}
            </span>
            <span className="text-white/35">HTTP {preview.status_code}</span>
          </div>
        </div>
      )}
    </div>
  );
};
