import { useEffect, useState } from 'react';
import { Languages, Loader2, CheckCircle2, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '../ui/button';

const API = process.env.REACT_APP_BACKEND_URL;

export const TranslateCatalogButton = () => {
  const [loading, setLoading] = useState(false);
  const [health, setHealth] = useState(null);

  const loadHealth = () => {
    fetch(`${API}/api/catalog/admin/translation-health`, { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null)).then(setHealth).catch(() => {});
  };
  useEffect(loadHealth, []);

  const run = async () => {
    if (!window.confirm("L'IA va traduire en anglais, espagnol, créole et arabe tous les produits du catalogue acheteur sans traduction complète (par lots de 10). Continuer ?")) return;
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/catalog/admin/translate-all`, { method: 'POST', credentials: 'include' });
      const d = await r.json();
      if (!r.ok) return toast.error(d.detail || 'Traduction échouée');
      toast.success(d.message || `${d.translated} produit(s) traduits EN + ES + GCF + AR${d.remaining ? ` — ${d.remaining} restant(s), relancez pour continuer` : ' — catalogue 100% traduit ✓'}`, { duration: 8000 });
      loadHealth();
    } catch { toast.error('Erreur de connexion'); } finally { setLoading(false); }
  };

  return (
    <span className="inline-flex items-center gap-2">
      {health && (() => {
        const allDone = health.ok && !health.missing_drafts;
        const label = allDone ? 'Traductions 100 %'
          : !health.ok
            ? `${health.missing} produit(s) sans traduction${health.missing_drafts ? ` + ${health.missing_drafts} brouillon(s)` : ''}`
            : `${health.missing_drafts} brouillon(s) à traduire avant publication`;
        return (
          <span data-testid="translation-health-badge"
            className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-[11px] font-semibold border ${allDone
              ? 'text-emerald-300 bg-emerald-400/10 border-emerald-400/30'
              : 'text-amber-300 bg-amber-400/10 border-amber-400/30'}`}>
            {allDone ? <CheckCircle2 className="w-3 h-3" /> : <AlertTriangle className="w-3 h-3" />}
            {label}
          </span>
        );
      })()}
      <Button variant="outline" onClick={run} disabled={loading} data-testid="translate-catalog-btn"
        className="border-white/15 text-white/70 hover:text-white hover:bg-white/10">
        {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Languages className="w-4 h-4 mr-2" />}
        {loading ? 'Traduction…' : 'Traduire catalogue (IA)'}
      </Button>
    </span>
  );
};
