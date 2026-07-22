import { useState } from 'react';
import { Layers, Loader2, Sparkles } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '../ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../ui/dialog';

const API = process.env.REACT_APP_BACKEND_URL;
const STATUS = { cree: ['Créé ✓', 'text-emerald-400'], existant: ['Déjà présent', 'text-amber-300'], introuvable: ['EAN introuvable', 'text-red-400'], erreur: ['Erreur', 'text-red-400'] };

export const BulkEanImport = ({ onDone }) => {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);

  const run = async () => {
    const eans = text.split(/[\s,;]+/).filter((e) => e.trim());
    if (!eans.length) return toast.error('Saisissez au moins un code EAN (un par ligne, max 10)');
    setLoading(true);
    setResults(null);
    try {
      const r = await fetch(`${API}/api/catalog/admin/products/bulk-ai`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ eans }),
      });
      const d = await r.json();
      if (!r.ok) return toast.error(d.detail || 'Import échoué');
      setResults(d.results);
      toast.success(`${d.created} fiche(s) produit créée(s) en brouillon sur ${d.total} EAN`);
      if (d.created) onDone?.();
    } catch { toast.error('Erreur de connexion'); } finally { setLoading(false); }
  };

  return (
    <>
      <Button variant="outline" onClick={() => { setOpen(true); setResults(null); }} data-testid="bulk-ean-btn"
        className="border-[#D9B35A]/40 text-[#E9CF8E] hover:bg-[#D9B35A]/10">
        <Layers className="w-4 h-4 mr-2" /> Import EAN en masse
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-lg bg-[#0a0d14] border-white/10">
          <DialogHeader>
            <DialogTitle className="text-white flex items-center gap-2 text-base">
              <Layers className="w-4 h-4 text-[#D9B35A]" /> Fiches produit en série par codes-barres
            </DialogTitle>
          </DialogHeader>
          <p className="text-xs text-white/50">Collez jusqu'à 10 codes EAN (un par ligne) — l'IA crée les fiches en brouillon avec descriptions, tags et image officielle.</p>
          <textarea rows={6} value={text} onChange={(e) => setText(e.target.value)} data-testid="bulk-ean-textarea"
            placeholder={'3017620422003\n3175680011480\n...'}
            className="w-full px-3 py-2 rounded-lg text-sm font-mono text-white bg-white/[0.05] border border-white/15" />
          {results && (
            <div className="space-y-1 max-h-40 overflow-y-auto" data-testid="bulk-ean-results">
              {results.map((r) => {
                const [label, cls] = STATUS[r.status] || [r.status, 'text-white/60'];
                return (
                  <div key={r.ean} className="flex items-center gap-2 text-xs py-1 border-b border-white/5 last:border-0">
                    <span className="font-mono text-white/60">{r.ean}</span>
                    <span className="flex-1 text-white/80 truncate">{r.name || ''}</span>
                    <span className={`font-bold ${cls}`}>{label}</span>
                  </div>
                );
              })}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)} className="border-white/10">Fermer</Button>
            <Button onClick={run} disabled={loading} data-testid="bulk-ean-run-btn" className="bg-[#D9B35A] hover:bg-[#c9a34a] text-black">
              {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Sparkles className="w-4 h-4 mr-2" />}
              {loading ? 'Création en cours…' : 'Créer les fiches par IA'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
};
