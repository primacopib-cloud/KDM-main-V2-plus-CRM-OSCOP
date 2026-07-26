import { useRef, useState } from 'react';
import { ImagePlus, Loader2, X } from 'lucide-react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const SIZES = [['s', 'Petite'], ['m', 'Moyenne'], ['l', 'Grande']];
const SHAPES = [['round', 'Ronde'], ['square', 'Carrée'], ['banner', 'Bannière']];
const selCls = 'h-7 px-1.5 rounded-md bg-white/[0.06] border border-white/15 text-[10.5px] text-white';

export const CountdownImagesEditor = ({ images = [], onChange }) => {
  const fileRef = useRef(null);
  const [uploading, setUploading] = useState(false);

  const upload = async (files) => {
    setUploading(true);
    const next = [...images];
    try {
      for (const f of files) {
        const fd = new FormData();
        fd.append('file', f);
        const r = await fetch(`${API}/admin/credit-promotions/upload-image`, {
          method: 'POST', credentials: 'include', body: fd,
        });
        const d = await r.json();
        if (!r.ok) { toast.error(d.detail || `Upload échoué : ${f.name}`); continue; }
        next.push({ url: d.url, size: 'm', shape: 'round' });
      }
      onChange(next);
      if (next.length > images.length) toast.success(`${next.length - images.length} visuel(s) téléversé(s)`);
    } catch { toast.error('Erreur de connexion'); } finally { setUploading(false); }
  };

  const setProp = (i, key, value) => {
    onChange(images.map((img, idx) => (idx === i ? { ...img, [key]: value } : img)));
  };

  return (
    <div className="w-full space-y-2" data-testid="countdown-images-editor">
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-[10px] uppercase opacity-50">Visuels des mentions (carrousel) :</span>
        <input ref={fileRef} type="file" accept="image/*" multiple className="hidden" data-testid="countdown-image-input"
          onChange={(e) => { const fs = Array.from(e.target.files || []); if (fs.length) upload(fs); e.target.value = ''; }} />
        <button type="button" onClick={() => fileRef.current?.click()} disabled={uploading} data-testid="countdown-image-upload-btn"
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[10.5px] font-bold bg-white/10 text-[#E9CF8E] hover:bg-white/15 disabled:opacity-50 transition-colors">
          {uploading ? <Loader2 className="w-3 h-3 animate-spin" /> : <ImagePlus className="w-3 h-3" />}
          {uploading ? 'Téléversement…' : 'Téléverser une ou plusieurs images'}
        </button>
        <span className="text-[10px] text-white/35">Sans visuel : icônes + images automatiques selon les mentions.</span>
      </div>
      {images.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {images.map((img, i) => (
            <div key={img.url} className="flex items-center gap-1.5 p-1.5 rounded-lg bg-white/[0.04] border border-white/10" data-testid={`countdown-image-row-${i}`}>
              <img src={`${process.env.REACT_APP_BACKEND_URL}${img.url}`} alt=""
                className={`w-9 h-9 object-cover border border-[#D9B35A]/40 ${img.shape === 'round' ? 'rounded-full' : 'rounded-md'}`} />
              <select value={img.size} onChange={(e) => setProp(i, 'size', e.target.value)} className={selCls} data-testid={`countdown-image-size-${i}`}>
                {SIZES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
              <select value={img.shape} onChange={(e) => setProp(i, 'shape', e.target.value)} className={selCls} data-testid={`countdown-image-shape-${i}`}>
                {SHAPES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
              <button type="button" onClick={() => onChange(images.filter((_, idx) => idx !== i))}
                data-testid={`countdown-image-remove-${i}`} className="p-1 rounded text-white/40 hover:text-red-400">
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
