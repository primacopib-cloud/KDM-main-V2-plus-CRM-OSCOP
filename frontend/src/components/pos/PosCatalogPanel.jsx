import { useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';
import { Package, Plus, Loader2, Camera } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Textarea } from '../ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../ui/dialog';
import { lolodriveAPI } from '../../services/api';

const STATUS_STYLE = {
  PENDING: { label: 'En attente de validation', color: '#f59e0b' },
  APPROVED: { label: 'Approuvé — en ligne', color: '#10b981' },
  REJECTED: { label: 'Refusé', color: '#ef4444' },
};

export const PosCatalogPanel = () => {
  const [catalog, setCatalog] = useState(null);
  const [mine, setMine] = useState([]);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ name: '', category: '', brand: '', description: '', price: '' });
  const [photo, setPhoto] = useState(null);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef(null);

  const uploadPhoto = async (file) => {
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const r = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/lolodrive/manager/products/photo`, {
        method: 'POST', credentials: 'include', body: fd,
      });
      const d = await r.json();
      if (!r.ok) { toast.error(d.detail || 'Upload échoué'); return; }
      setPhoto(d.image_url);
      toast.success('Photo ajoutée à la fiche ✓');
    } catch { toast.error('Erreur de connexion'); } finally { setUploading(false); }
  };

  const load = () => {
    lolodriveAPI.posCatalog().then(setCatalog).catch(() => {});
    lolodriveAPI.managerProducts().then((d) => setMine(d.products || [])).catch(() => {});
  };
  useEffect(() => { load(); }, []);

  const submit = async () => {
    const cents = Math.round(parseFloat(String(form.price).replace(',', '.')) * 100);
    if (!form.name || !form.category || !form.description || !cents || cents <= 0) {
      return toast.error('Fiche incomplète : nom, catégorie, description et prix requis');
    }
    setSaving(true);
    try {
      await lolodriveAPI.managerSubmitProduct({
        name: form.name, category: form.category, brand: form.brand || undefined,
        description: form.description, price_public_cents: cents, image_url: photo || undefined,
      });
      toast.success('Fiche soumise au super admin pour validation ✓');
      setOpen(false);
      setForm({ name: '', category: '', brand: '', description: '', price: '' });
      setPhoto(null);
      load();
    } catch (e) { toast.error(e.message); } finally { setSaving(false); }
  };

  if (!catalog) return null;
  return (
    <div className="mt-6 rounded-2xl bg-white/[0.025] border border-white/[0.07] p-5" data-testid="pos-catalog-panel">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div className="font-semibold flex items-center gap-2">
          <Package className="w-4 h-4 text-[#D9B35A]" />
          Catalogue du relais {catalog.point_code || ''} ({catalog.products.length} produits)
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button size="sm" className="bg-[#D9B35A] hover:bg-[#c9a34a] text-black" data-testid="pos-submit-product-btn">
              <Plus className="w-3 h-3 mr-1" /> Proposer un produit
            </Button>
          </DialogTrigger>
          <DialogContent className="bg-[#15151c] border-white/10 text-white max-w-md">
            <DialogHeader><DialogTitle>Nouvelle fiche produit — soumise au super admin</DialogTitle></DialogHeader>
            <div className="space-y-3">
              <Input placeholder="Nom du produit *" value={form.name} data-testid="product-name-input"
                onChange={(e) => setForm({ ...form, name: e.target.value })} className="bg-white/5 border-white/10" />
              <div className="grid grid-cols-2 gap-3">
                <Input placeholder="Catégorie *" value={form.category} data-testid="product-category-input"
                  onChange={(e) => setForm({ ...form, category: e.target.value })} className="bg-white/5 border-white/10" />
                <Input placeholder="Marque / producteur" value={form.brand} data-testid="product-brand-input"
                  onChange={(e) => setForm({ ...form, brand: e.target.value })} className="bg-white/5 border-white/10" />
              </div>
              <Textarea placeholder="Description complète *" value={form.description} rows={3} data-testid="product-description-input"
                onChange={(e) => setForm({ ...form, description: e.target.value })} className="bg-white/5 border-white/10" />
              <Input placeholder="Prix public en € * (ex: 4.50)" value={form.price} data-testid="product-price-input"
                onChange={(e) => setForm({ ...form, price: e.target.value })} className="bg-white/5 border-white/10" />
              <input ref={fileRef} type="file" accept="image/*" className="hidden" data-testid="product-photo-input"
                onChange={(e) => { const f = e.target.files?.[0]; if (f) uploadPhoto(f); e.target.value = ''; }} />
              <div className="flex items-center gap-3">
                <Button type="button" variant="outline" size="sm" disabled={uploading}
                  onClick={() => fileRef.current?.click()} data-testid="product-photo-btn"
                  className="border-white/15 text-white/80">
                  {uploading ? <Loader2 className="w-3 h-3 mr-1 animate-spin" /> : <Camera className="w-3 h-3 mr-1 text-[#D9B35A]" />}
                  {photo ? 'Changer la photo' : 'Ajouter une photo'}
                </Button>
                {photo && <img src={photo} alt="Aperçu produit" data-testid="product-photo-preview"
                  className="w-12 h-12 rounded-lg object-cover border border-[#D9B35A]/40" />}
              </div>
              <Button onClick={submit} disabled={saving} className="w-full bg-[#D9B35A] hover:bg-[#c9a34a] text-black" data-testid="product-submit-btn">
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Soumettre pour validation'}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {mine.length > 0 && (
        <div className="mb-4 space-y-1.5" data-testid="pos-my-submissions">
          <p className="text-[11px] uppercase tracking-wider text-white/40">Mes fiches produits</p>
          {mine.map((p) => (
            <div key={p.sku} className="flex items-center justify-between text-xs p-2 rounded-lg bg-white/[0.03] border border-white/[0.06]">
              <span className="truncate">{p.name} — {(p.price_public_cents / 100).toFixed(2)} €</span>
              <span className="px-2 py-0.5 rounded-full font-semibold shrink-0"
                style={{ color: STATUS_STYLE[p.status]?.color, background: `${STATUS_STYLE[p.status]?.color}1a` }}
                data-testid={`submission-status-${p.sku}`}>
                {STATUS_STYLE[p.status]?.label || p.status}{p.status === 'REJECTED' && p.reject_reason ? ` · ${p.reject_reason}` : ''}
              </span>
            </div>
          ))}
        </div>
      )}

      <div className="max-h-72 overflow-y-auto space-y-1.5" data-testid="pos-catalog-list">
        {catalog.products.map((p) => (
          <div key={p.sku} className="flex items-center justify-between text-xs p-2 rounded-lg bg-white/[0.02]">
            <span className="truncate">
              {p.name}
              {p.point_code && <span className="ml-2 px-1.5 py-0.5 rounded text-[10px] font-bold text-[#D9B35A] bg-[#D9B35A]/10 border border-[#D9B35A]/30">Relais</span>}
            </span>
            <span className="font-mono shrink-0 ml-3">
              {(p.price_public_cents / 100).toFixed(2)} € <span className="text-[#D9B35A]">· {p.uc_public} UC</span>
              {p.price_pass_cents != null && <span className="text-white/40"> (PASS {(p.price_pass_cents / 100).toFixed(2)} € · {p.uc_pass} UC)</span>}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};
