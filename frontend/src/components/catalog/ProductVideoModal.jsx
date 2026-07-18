import { X, Clapperboard } from 'lucide-react';

export const ProductVideoModal = ({ product, onClose }) => {
  if (!product) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm"
      onClick={onClose} data-testid="product-video-modal">
      <div className="rounded-[20px] overflow-hidden max-w-2xl w-full bg-[#1a1028]"
        onClick={(e) => e.stopPropagation()} style={{ boxShadow: '0 24px 64px rgba(0,0,0,0.5)' }}>
        <div className="flex items-center justify-between px-5 py-3">
          <p className="text-sm font-semibold text-white flex items-center gap-2">
            <Clapperboard size={15} className="text-[#D9B35A]" /> Spot vidéo — {product.name}
          </p>
          <button type="button" onClick={onClose} data-testid="product-video-close"
            className="text-white/60 hover:text-white p-1"><X size={18} /></button>
        </div>
        <video src={product.video_url} controls autoPlay playsInline
          className="w-full aspect-video bg-black" data-testid="product-video-player" />
      </div>
    </div>
  );
};
