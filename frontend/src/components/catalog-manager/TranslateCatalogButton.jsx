import { useState } from 'react';
import { Languages, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '../ui/button';

const API = process.env.REACT_APP_BACKEND_URL;

export const TranslateCatalogButton = () => {
  const [loading, setLoading] = useState(false);

  const run = async () => {
    if (!window.confirm("L'IA va traduire en anglais et espagnol tous les produits du catalogue acheteur sans traduction (par lots de 15). Continuer ?")) return;
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/catalog/admin/translate-all`, { method: 'POST', credentials: 'include' });
      const d = await r.json();
      if (!r.ok) return toast.error(d.detail || 'Traduction échouée');
      toast.success(d.message || `${d.translated} produit(s) traduits EN + ES${d.remaining ? ` — ${d.remaining} restant(s), relancez pour continuer` : ' — catalogue 100% traduit ✓'}`, { duration: 8000 });
    } catch { toast.error('Erreur de connexion'); } finally { setLoading(false); }
  };

  return (
    <Button variant="outline" onClick={run} disabled={loading} data-testid="translate-catalog-btn"
      className="border-white/15 text-white/70 hover:text-white hover:bg-white/10">
      {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Languages className="w-4 h-4 mr-2" />}
      {loading ? 'Traduction…' : 'Traduire catalogue (IA)'}
    </Button>
  );
};
