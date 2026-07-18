import { useRef } from 'react';
import { toast } from 'sonner';
import { ImagePlus, Star, X } from 'lucide-react';
import { Label } from '../ui/label';

/** Sélecteur de photos produit : max 3, PNG/JPEG, une principale. */
export const ProductPhotoUploader = ({ photos, setPhotos }) => {
  const inputRef = useRef(null);

  const addFiles = (files) => {
    const valid = Array.from(files).filter((f) => ['image/png', 'image/jpeg'].includes(f.type));
    if (valid.length < files.length) toast.error('Formats acceptés : PNG ou JPEG uniquement');
    const room = 3 - photos.length;
    if (valid.length > room) toast.error('Maximum 3 photos par produit');
    const next = valid.slice(0, room).map((file, i) => ({
      file, preview: URL.createObjectURL(file),
      isPrimary: photos.length === 0 && i === 0,
    }));
    setPhotos([...photos, ...next]);
  };

  const remove = (idx) => {
    const next = photos.filter((_, i) => i !== idx);
    if (next.length && !next.some((p) => p.isPrimary)) next[0].isPrimary = true;
    setPhotos(next);
  };

  const setPrimary = (idx) => setPhotos(photos.map((p, i) => ({ ...p, isPrimary: i === idx })));

  return (
    <div className="space-y-2" data-testid="product-photos-section">
      <Label>Photos produit (max 3 — PNG ou JPEG, 1 principale)</Label>
      <div className="flex flex-wrap gap-3">
        {photos.map((p, idx) => (
          <div key={p.preview} className="relative w-24 h-24 rounded-lg overflow-hidden border border-gray-200" data-testid={`product-photo-${idx}`}>
            <img src={p.preview} alt={`photo ${idx + 1}`} className="w-full h-full object-cover" />
            <button type="button" onClick={() => remove(idx)} data-testid={`product-photo-remove-${idx}`}
              className="absolute top-1 right-1 p-0.5 rounded-full bg-black/60 text-white hover:bg-red-600">
              <X size={12} />
            </button>
            <button type="button" onClick={() => setPrimary(idx)} data-testid={`product-photo-primary-${idx}`}
              title={p.isPrimary ? 'Photo principale' : 'Définir comme principale'}
              className={`absolute bottom-1 left-1 p-0.5 rounded-full ${p.isPrimary ? 'bg-amber-400 text-white' : 'bg-black/50 text-white/70 hover:bg-amber-400'}`}>
              <Star size={12} fill={p.isPrimary ? 'currentColor' : 'none'} />
            </button>
            {p.isPrimary && (
              <span className="absolute bottom-0 right-0 text-[8px] font-bold bg-amber-400 text-white px-1 rounded-tl">PRINCIPALE</span>
            )}
          </div>
        ))}
        {photos.length < 3 && (
          <button
            type="button" onClick={() => inputRef.current?.click()}
            data-testid="product-photo-add-btn"
            className="w-24 h-24 rounded-lg border-2 border-dashed border-gray-300 flex flex-col items-center justify-center gap-1 text-gray-400 hover:border-purple-400 hover:text-purple-500 transition-colors"
          >
            <ImagePlus size={20} />
            <span className="text-[10px]">Ajouter</span>
          </button>
        )}
      </div>
      <input
        ref={inputRef} type="file" accept="image/png,image/jpeg" multiple hidden
        data-testid="product-photo-input"
        onChange={(e) => { addFiles(e.target.files); e.target.value = ''; }}
      />
    </div>
  );
};

/** Upload séquentiel des photos après création/édition du produit. */
export const uploadProductPhotos = async (apiUrl, vendorId, productId, photos) => {
  let uploaded = 0;
  for (const p of photos) {
    const fd = new FormData();
    fd.append('file', p.file);
    fd.append('is_primary', p.isPrimary ? 'true' : 'false');
    const r = await fetch(`${apiUrl}/api/vendor/products/${vendorId}/${productId}/upload-image`, {
      method: 'POST', body: fd,
    });
    if (r.ok) uploaded += 1;
  }
  return uploaded;
};
