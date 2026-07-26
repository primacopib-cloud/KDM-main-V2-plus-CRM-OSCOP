import { useState } from 'react';
import { Wand2, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from './ui/button';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export const AiPriceDraftsButton = ({ products, onDone }) => {
  const [busy, setBusy] = useState(false);
  const draftIds = products.filter((p) => p.status === 'draft').map((p) => p.id);
  if (!draftIds.length) return null;

  const priceAll = async () => {
    setBusy(true);
    toast.info(`Prix IA en cours sur ${draftIds.length} fiche(s)…`);
    try {
      const res = await fetch(`${API_URL}/api/catalog/admin/products/ai-price-bulk`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids: draftIds }),
      });
      const d = await res.json();
      if (!res.ok) { toast.error(d.detail || 'Prix IA échoué'); return; }
      const fails = (d.results || []).filter((r) => !r.ok);
      toast.success(`Prix IA appliqué à ${d.priced}/${d.count} fiche(s) ✓`, { duration: 6000 });
      if (fails.length) toast.warning(`${fails.length} échec(s) : ${fails.map((f) => f.name || f.id).join(', ')}`);
      onDone?.();
    } catch { toast.error('Erreur de connexion'); } finally { setBusy(false); }
  };

  return (
    <Button onClick={priceAll} disabled={busy} data-testid="ai-price-drafts-btn"
      variant="outline" className="border-[#7c3aed]/60 text-[#c4b5fd] hover:bg-[#7c3aed]/15">
      {busy ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Wand2 className="w-4 h-4 mr-2" />}
      Prix IA en lot ({draftIds.length})
    </Button>
  );
};
