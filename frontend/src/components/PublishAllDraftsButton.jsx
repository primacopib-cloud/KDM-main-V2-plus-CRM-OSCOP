import { useState } from 'react';
import { Rocket, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from './ui/button';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export const PublishAllDraftsButton = ({ products, onDone }) => {
  const [busy, setBusy] = useState(false);
  const draftIds = products.filter((p) => p.status === 'draft').map((p) => p.id);
  if (!draftIds.length) return null;

  const publishAll = async () => {
    setBusy(true);
    try {
      const res = await fetch(`${API_URL}/api/catalog/admin/products/publish-bulk`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids: draftIds }),
      });
      const d = await res.json();
      if (!res.ok) { toast.error(d.detail || 'Publication échouée'); return; }
      toast.success(`${d.published} fiche(s) brouillon publiée(s) au catalogue ✓`);
      onDone?.();
    } catch { toast.error('Erreur de connexion'); } finally { setBusy(false); }
  };

  return (
    <Button onClick={publishAll} disabled={busy} data-testid="publish-all-drafts-btn"
      variant="outline" className="border-emerald-500/50 text-emerald-400 hover:bg-emerald-500/10">
      {busy ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Rocket className="w-4 h-4 mr-2" />}
      Publier tous les brouillons ({draftIds.length})
    </Button>
  );
};
