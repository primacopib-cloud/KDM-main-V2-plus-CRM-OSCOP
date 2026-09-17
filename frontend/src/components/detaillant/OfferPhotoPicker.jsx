import { useRef } from 'react';
import { Camera, X } from 'lucide-react';
import { toast } from 'sonner';
import { detaillantAPI } from '../../services/api.detaillant';
import { API } from '../../services/http';

const imgSrc = (u) => (u?.startsWith('/api/') ? `${API}${u.slice(4)}` : u);

export const OfferPhotoPicker = ({ photos, onChange, labels = null }) => {
  const inputRef = useRef(null);
  const slotRef = useRef(0);
  const maxPhotos = labels ? Math.max(labels.length, 1) : 3;
  const upload = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;
    try {
      const { url } = await detaillantAPI.uploadPhoto(file);
      if (labels) {
        const next = [...photos];
        next[slotRef.current] = url;
        onChange(next.slice(0, maxPhotos));
      } else {
        if (photos.length >= 3) { toast.error('Maximum 3 photos (1 principale + 2)'); return; }
        onChange([...photos, url]);
      }
      toast.success('✓ Photo ajoutée');
    } catch (err) { toast.error(err.message); }
  };
  const pick = (slot) => { slotRef.current = slot; inputRef.current?.click(); };
  if (labels) {
    return (
      <div data-testid="offer-photos">
        <label className="text-[10px] text-white/50 block mb-1">
          Photos du lot composé — une photo par produit pour mieux vendre (produit 1 obligatoire)
        </label>
        <div className="flex gap-3 flex-wrap">
          {labels.map((name, i) => (
            <div key={`${name}-${i}`} className="w-24">
              {photos[i] ? (
                <div className="relative w-24 h-16 rounded-lg overflow-hidden border border-white/15"
                  data-testid={`offer-photo-${i}`}>
                  <img src={imgSrc(photos[i])} alt={name} title={name} className="w-full h-full object-cover" />
                  {i === 0 && (
                    <span className="absolute bottom-0 inset-x-0 text-center text-[8px] font-bold bg-[#D9B35A] text-black">principale</span>
                  )}
                  <button onClick={() => onChange(photos.map((p, j) => (j === i ? '' : p)))}
                    data-testid={`offer-photo-remove-${i}`}
                    className="absolute top-0.5 right-0.5 w-4 h-4 rounded-full bg-black/70 flex items-center justify-center">
                    <X className="w-2.5 h-2.5 text-white" />
                  </button>
                </div>
              ) : (
                <button onClick={() => pick(i)} data-testid={`offer-photo-slot-${i}`}
                  className="w-24 h-16 rounded-lg border border-dashed border-white/25 flex flex-col items-center justify-center text-white/40 hover:text-[#E9CF8E] hover:border-[#D9B35A]/50">
                  <Camera className="w-4 h-4" />
                </button>
              )}
              <p className="text-[8px] text-white/45 mt-0.5 truncate text-center" title={name}>{name}</p>
            </div>
          ))}
          <input ref={inputRef} type="file" accept="image/png,image/jpeg,image/webp" className="hidden"
            onChange={upload} data-testid="offer-photo-input" />
        </div>
      </div>
    );
  }
  return (
    <div data-testid="offer-photos">
      <label className="text-[10px] text-white/50 block mb-1">
        Photos du lot — 1 principale obligatoire + 2 facultatives
      </label>
      <div className="flex gap-2 flex-wrap">
        {photos.map((url, i) => (
          <div key={url} className="relative w-16 h-16 rounded-lg overflow-hidden border border-white/15"
            data-testid={`offer-photo-${i}`}>
            <img src={imgSrc(url)} alt={`Photo ${i + 1}`} className="w-full h-full object-cover" />
            {i === 0 && (
              <span className="absolute bottom-0 inset-x-0 text-center text-[8px] font-bold bg-[#D9B35A] text-black">
                principale
              </span>
            )}
            <button onClick={() => onChange(photos.filter((p) => p !== url))} data-testid={`offer-photo-remove-${i}`}
              className="absolute top-0.5 right-0.5 w-4 h-4 rounded-full bg-black/70 flex items-center justify-center">
              <X className="w-2.5 h-2.5 text-white" />
            </button>
          </div>
        ))}
        {photos.filter(Boolean).length < 3 && (
          <button onClick={() => inputRef.current?.click()} data-testid="offer-photo-add"
            className="w-16 h-16 rounded-lg border border-dashed border-white/25 flex flex-col items-center justify-center text-white/40 hover:text-[#E9CF8E] hover:border-[#D9B35A]/50">
            <Camera className="w-4 h-4" />
            <span className="text-[8px] mt-0.5">{photos.length === 0 ? 'principale' : 'ajouter'}</span>
          </button>
        )}
        <input ref={inputRef} type="file" accept="image/png,image/jpeg,image/webp" className="hidden"
          onChange={upload} data-testid="offer-photo-input" />
      </div>
    </div>
  );
};
