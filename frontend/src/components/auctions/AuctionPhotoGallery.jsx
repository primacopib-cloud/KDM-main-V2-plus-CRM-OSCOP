import { useEffect, useState } from 'react';
import { ChevronLeft, ChevronRight, X } from 'lucide-react';
import { API } from '../../services/http';

const imgSrc = (u) => (u?.startsWith('/api/') ? `${API}${u.slice(4)}` : u);

// Galerie plein écran des photos d'un lot COOP'ACT
export const AuctionPhotoGallery = ({ photos, title, onClose }) => {
  const [idx, setIdx] = useState(0);
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') onClose();
      if (e.key === 'ArrowRight') setIdx((i) => (i + 1) % photos.length);
      if (e.key === 'ArrowLeft') setIdx((i) => (i - 1 + photos.length) % photos.length);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [photos.length, onClose]);
  return (
    <div className="fixed inset-0 z-[100] bg-black/90 flex items-center justify-center p-4"
      onClick={onClose} data-testid="auction-photo-gallery">
      <button onClick={onClose} data-testid="gallery-close"
        className="absolute top-4 right-4 w-9 h-9 rounded-full bg-white/10 flex items-center justify-center text-white hover:bg-white/20">
        <X className="w-5 h-5" />
      </button>
      <div className="max-w-3xl w-full" onClick={(e) => e.stopPropagation()}>
        <div className="relative rounded-2xl overflow-hidden bg-white flex items-center justify-center" style={{ minHeight: 320 }}>
          <img src={imgSrc(photos[idx])} alt={`${title} — photo ${idx + 1}`}
            className="max-h-[70vh] w-full object-contain" data-testid="gallery-image" />
          {photos.length > 1 && (
            <>
              <button onClick={() => setIdx((i) => (i - 1 + photos.length) % photos.length)} data-testid="gallery-prev"
                className="absolute left-2 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-black/50 text-white flex items-center justify-center hover:bg-black/70">
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button onClick={() => setIdx((i) => (i + 1) % photos.length)} data-testid="gallery-next"
                className="absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-black/50 text-white flex items-center justify-center hover:bg-black/70">
                <ChevronRight className="w-4 h-4" />
              </button>
            </>
          )}
        </div>
        <div className="flex items-center justify-between mt-3">
          <p className="text-sm text-white font-semibold truncate">{title}</p>
          {photos.length > 1 && (
            <div className="flex gap-2">
              {photos.map((p, i) => (
                <button key={`${p}-${i}`} onClick={() => setIdx(i)} data-testid={`gallery-thumb-${i}`}
                  className={`w-12 h-12 rounded-lg overflow-hidden border-2 ${i === idx ? 'border-[#D9B35A]' : 'border-white/20 opacity-60'}`}>
                  <img src={imgSrc(p)} alt={`Miniature ${i + 1}`} className="w-full h-full object-cover" />
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
