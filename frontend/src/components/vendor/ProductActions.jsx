import { useState } from 'react';
import { Eye, Edit, Download, Sparkles, Clapperboard, X } from 'lucide-react';
import { Button } from '../ui/button';
import { VideoShareButtons } from './VideoShareButtons';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const VendorVideoModal = ({ product, onClose }) => (
  <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
    onClick={onClose} data-testid="vendor-video-modal">
    <div className="rounded-[20px] p-5 max-w-xl w-full bg-white" onClick={(e) => e.stopPropagation()}
      style={{ boxShadow: '0 24px 64px rgba(76,42,110,0.3)' }}>
      <div className="flex items-start justify-between mb-3">
        <h3 className="font-display text-lg text-[#1F2A3A] flex items-center gap-2">
          <Clapperboard size={16} className="text-purple-600" /> Spot vidéo — {product.name}
        </h3>
        <button type="button" onClick={onClose} data-testid="vendor-video-close"
          className="opacity-50 hover:opacity-100 p-1"><X size={18} /></button>
      </div>
      <video src={product.video_url.startsWith('http') ? product.video_url : `${API_URL}${product.video_url}`}
        controls playsInline className="w-full rounded-xl bg-black aspect-video" data-testid="vendor-video-player" />
      <VideoShareButtons videoUrl={product.video_url} productName={product.name} />
    </div>
  </div>
);

export const ProductActions = ({ product, vendorId, onView, onEdit, onAI }) => {
  const [videoOpen, setVideoOpen] = useState(false);
  return (
    <div className="flex flex-col gap-2">
      <Button variant="outline" size="sm" className="gap-1" onClick={onView}
        data-testid={`view-product-${product.id}`}>
        <Eye className="w-3 h-3" /> Voir
      </Button>
      {product.status !== 'pending_approval' && (
        <Button variant="outline" size="sm" className="gap-1" onClick={onEdit}
          data-testid={`edit-product-${product.id}`}>
          <Edit className="w-3 h-3" /> Modifier
        </Button>
      )}
      <Button variant="outline" size="sm" className="gap-1 text-purple-600"
        onClick={() => window.open(`${API_URL}/api/vendor/products/${vendorId}/${product.id}/pdf`, '_blank')}
        data-testid={`download-sheet-${product.id}`}>
        <Download className="w-3 h-3" /> Fiche PDF
      </Button>
      <Button size="sm" className="gap-1 bg-purple-600 hover:bg-purple-700 text-white" onClick={onAI}
        data-testid={`ai-studio-${product.id}`}>
        <Sparkles className="w-3 h-3" /> Studio IA
      </Button>
      {product.video_url && (
        <Button variant="outline" size="sm" className="gap-1 text-[#B8860B] border-[#D9B35A]"
          onClick={() => setVideoOpen(true)} data-testid={`video-spot-${product.id}`}>
          <Clapperboard className="w-3 h-3" /> Spot vidéo
        </Button>
      )}
      {videoOpen && <VendorVideoModal product={product} onClose={() => setVideoOpen(false)} />}
    </div>
  );
};
