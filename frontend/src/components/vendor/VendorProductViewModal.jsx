import { Download, X, Package, Clapperboard } from 'lucide-react';
import { Button } from '../ui/button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '../ui/dialog';
import { Badge } from '../ui/badge';
import { getStatusBadge } from './vendorConstants';
import { VideoShareButtons } from './VideoShareButtons';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const Row = ({ label, value }) => (
  <div className="flex justify-between gap-4 py-1.5 border-b border-gray-100 text-sm">
    <span className="text-gray-500">{label}</span>
    <span className="font-medium text-gray-900 text-right">{value ?? '—'}</span>
  </div>
);

export const VendorProductViewModal = ({ product, vendorId, onClose }) => {
  if (!product) return null;
  const primary = (product.images || []).find((i) => i.is_primary) || (product.images || [])[0];

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto" data-testid="product-view-modal">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 pr-6">
            <Package className="w-5 h-5 text-purple-600" />
            {product.name}
            {getStatusBadge(product.status)}
          </DialogTitle>
          <DialogDescription>Fiche détaillée du produit — téléchargeable en PDF.</DialogDescription>
        </DialogHeader>

        {(product.images || []).length > 0 && (
          <div className="flex gap-2">
            {product.images.map((img, i) => (
              <img
                key={img.url}
                src={img.url.startsWith('http') ? img.url : `${API_URL}${img.url}`}
                alt={`${product.name} ${i + 1}`}
                className={`w-24 h-24 object-cover rounded-lg border ${img.is_primary ? 'ring-2 ring-amber-400' : ''}`}
                data-testid={`view-product-image-${i}`}
              />
            ))}
          </div>
        )}

        <p className="text-sm text-gray-600">{product.description}</p>

        {product.video_url && (
          <div data-testid="view-product-video-section">
            <p className="text-xs font-semibold text-purple-700 mb-1.5 flex items-center gap-1.5">
              <Clapperboard size={13} /> Spot vidéo du produit
            </p>
            <video
              src={product.video_url.startsWith('http') ? product.video_url : `${API_URL}${product.video_url}`}
              controls playsInline preload="metadata"
              className="w-full rounded-xl bg-black aspect-video"
              data-testid="view-product-video-player"
            />
            <VideoShareButtons videoUrl={product.video_url} productName={product.name} />
          </div>
        )}

        <div>
          <Row label="SKU" value={product.sku} />
          <Row label="EAN-13" value={product.ean13} />
          <Row label="Catégorie" value={product.category} />
          <Row label="Marque" value={product.brand} />
          <Row label="Prix HT" value={`${(product.price_ht || 0).toFixed(2)} €`} />
          <Row label="TVA" value={`${product.tva_rate}%`} />
          <Row label="Prix TTC" value={`${(product.price_ttc || 0).toFixed(2)} €`} />
          <Row label="Stock" value={product.stock_quantity} />
          <Row label="Origine" value={`${product.country_flag || ''} ${product.country_name || product.country_of_origin || '—'}`} />
        </div>

        <div className="flex flex-wrap gap-1">
          {(product.available_zones || []).map((z) => <Badge key={z} variant="secondary" className="text-xs">{z}</Badge>)}
        </div>

        <div className="flex justify-between gap-2 pt-2">
          <Button
            variant="outline"
            onClick={() => window.open(`${API_URL}/api/vendor/products/${vendorId}/${product.id}/pdf`, '_blank')}
            data-testid="download-product-sheet-btn"
            className="gap-2"
          >
            <Download className="w-4 h-4" /> Télécharger la fiche produit
          </Button>
          <Button variant="ghost" onClick={onClose} data-testid="close-product-view" className="gap-1">
            <X className="w-4 h-4" /> Fermer
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};
