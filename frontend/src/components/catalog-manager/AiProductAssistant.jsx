import { useRef, useState } from 'react';
import { Sparkles, Camera, ScanBarcode, ImagePlus, Loader2, Video } from 'lucide-react';
import { toast } from 'sonner';
import { BarcodeScanner } from './BarcodeScanner';

const API = process.env.REACT_APP_BACKEND_URL;

const downscale = (file) => new Promise((resolve) => {
  const reader = new FileReader();
  reader.onload = () => {
    const img = new Image();
    img.onload = () => {
      const max = 1000;
      const ratio = Math.min(1, max / Math.max(img.width, img.height));
      const canvas = document.createElement('canvas');
      canvas.width = Math.round(img.width * ratio);
      canvas.height = Math.round(img.height * ratio);
      canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height);
      resolve(canvas.toDataURL('image/jpeg', 0.85));
    };
    img.src = reader.result;
  };
  reader.readAsDataURL(file);
});

export const AiProductAssistant = ({ formData, onApply }) => {
  const fileRef = useRef(null);
  const [ean, setEan] = useState('');
  const [photo, setPhoto] = useState(null);
  const [scanning, setScanning] = useState(false);
  const [imgLoading, setImgLoading] = useState(false);
  const [offImage, setOffImage] = useState('');
  const [scannerOpen, setScannerOpen] = useState(false);

  const scan = async () => {
    if (!photo && !ean.trim()) return toast.error('Ajoutez une photo du produit ou saisissez un code EAN');
    setScanning(true);
    try {
      const r = await fetch(`${API}/api/catalog/admin/products/ai-scan`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ean: ean.trim(), photo }),
      });
      const d = await r.json();
      if (!r.ok) return toast.error(d.detail || 'Analyse échouée');
      const { off_image_url, ...fields } = d.fields || {};
      if (off_image_url) setOffImage(off_image_url);
      const applied = Object.keys(fields).length;
      onApply(fields);
      toast.success(`${applied} champ(s) remplis par l'IA${off_image_url ? " — image officielle trouvée, cliquez sur « Image produit »" : ''}`);
    } catch {
      toast.error('Erreur de connexion');
    } finally {
      setScanning(false);
    }
  };

  const findImage = async () => {
    if (!formData.name && !formData.ean && !offImage) return toast.error('Renseignez d\'abord le nom ou la marque du produit');
    setImgLoading(true);
    try {
      const r = await fetch(`${API}/api/catalog/admin/products/ai-image`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: formData.name, brand: formData.brand, ean: formData.ean, off_image_url: offImage }),
      });
      const d = await r.json();
      if (!r.ok) return toast.error(d.detail || 'Image indisponible');
      onApply({ image_url: d.image_url });
      toast.success(d.source === 'retrouvee' ? 'Image officielle du produit retrouvée' : 'Image produit générée par IA');
    } catch {
      toast.error('Erreur de connexion');
    } finally {
      setImgLoading(false);
    }
  };

  return (
    <div className="rounded-xl p-4 mb-4 bg-gradient-to-br from-[#D9B35A]/10 to-[#5B2E8C]/10 border border-[#D9B35A]/25 space-y-3" data-testid="ai-product-assistant">
      <p className="text-sm font-semibold text-white flex items-center gap-2">
        <Sparkles className="w-4 h-4 text-[#D9B35A]" /> Assistant IA — scannez, l'IA remplit la fiche
      </p>
      <div className="flex flex-wrap items-center gap-2">
        <input ref={fileRef} type="file" accept="image/*" capture="environment" className="hidden"
          data-testid="ai-scan-photo-input"
          onChange={async (e) => {
            const f = e.target.files?.[0];
            if (f) { setPhoto(await downscale(f)); toast.success('Photo prête — cliquez sur Analyser'); }
            e.target.value = '';
          }} />
        <button type="button" onClick={() => fileRef.current?.click()} data-testid="ai-scan-photo-btn"
          className={`px-3 py-2 rounded-lg text-xs font-bold inline-flex items-center gap-1.5 border transition-colors ${photo
            ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-300' : 'bg-white/[0.06] border-white/15 text-white/75 hover:text-white'}`}>
          <Camera className="w-3.5 h-3.5" /> {photo ? 'Photo prête ✓' : 'Photo du produit'}
        </button>
        <div className="flex items-center gap-1.5">
          <ScanBarcode className="w-4 h-4 text-white/40" />
          <input value={ean} onChange={(e) => setEan(e.target.value.replace(/\D/g, ''))} placeholder="Code-barres EAN"
            data-testid="ai-scan-ean-input"
            className="h-9 w-36 px-2.5 rounded-lg text-xs text-white bg-white/[0.05] border border-white/15 font-mono" />
          <button type="button" onClick={() => setScannerOpen(true)} data-testid="ai-scan-camera-btn"
            title="Scanner le code-barres avec la caméra"
            className="p-2 rounded-lg bg-white/[0.06] border border-white/15 text-white/70 hover:text-white transition-colors">
            <Video className="w-4 h-4" />
          </button>
        </div>
        <button type="button" onClick={scan} disabled={scanning} data-testid="ai-scan-btn"
          className="px-4 py-2 rounded-lg text-xs font-bold inline-flex items-center gap-1.5 disabled:opacity-60"
          style={{ background: '#D9B35A', color: '#1F0A33' }}>
          {scanning ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
          {scanning ? 'Analyse en cours...' : 'Analyser'}
        </button>
        <button type="button" onClick={findImage} disabled={imgLoading} data-testid="ai-image-btn"
          className="px-3 py-2 rounded-lg text-xs font-bold inline-flex items-center gap-1.5 bg-white/[0.06] border border-white/15 text-white/75 hover:text-white disabled:opacity-60 transition-colors">
          {imgLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ImagePlus className="w-3.5 h-3.5" />}
          {imgLoading ? 'Image en cours...' : 'Image produit (Marque)'}
        </button>
      </div>
      {formData.image_url && (
        <div className="flex items-center gap-3">
          <img src={`${API}${formData.image_url}`.replace(`${API}http`, 'http')} alt="Produit"
            data-testid="ai-image-preview"
            className="w-16 h-16 rounded-lg object-cover border border-white/15 bg-white" />
          <p className="text-[11px] text-white/50">Visuel attaché à la fiche — il sera affiché dans le catalogue.</p>
        </div>
      )}
      <p className="text-[10px] text-white/40">
        Photo (le code-barres est lu automatiquement s'il est visible) et/ou EAN → l'IA remplit nom, marque,
        descriptions, catégorie, nutrition et les tags de recherche du catalogue.
      </p>
      <BarcodeScanner open={scannerOpen} onClose={() => setScannerOpen(false)} onDetect={(code) => setEan(code)} />
    </div>
  );
};
