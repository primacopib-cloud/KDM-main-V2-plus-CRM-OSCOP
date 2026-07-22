import { useEffect, useState } from 'react';
import { Percent, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '../ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../ui/dialog';
import { CATEGORIES } from './constants';

const API = process.env.REACT_APP_BACKEND_URL;

export const MarginSettings = () => {
  const [open, setOpen] = useState(false);
  const [margins, setMargins] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    fetch(`${API}/api/catalog/admin/pricing-margins`, { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null)).then((d) => setMargins(d?.margins || {})).catch(() => {});
  }, [open]);

  const save = async () => {
    setSaving(true);
    try {
      const r = await fetch(`${API}/api/catalog/admin/pricing-margins`, {
        method: 'PUT', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ margins: Object.fromEntries(Object.entries(margins).map(([k, v]) => [k, parseInt(v || '0', 10)])) }),
      });
      if (!r.ok) return toast.error('Enregistrement échoué');
      toast.success('Marges cibles enregistrées — le Prix IA les respectera');
      setOpen(false);
    } finally { setSaving(false); }
  };

  return (
    <>
      <Button variant="outline" onClick={() => setOpen(true)} data-testid="margin-settings-btn"
        className="border-white/15 text-white/70 hover:text-white hover:bg-white/10">
        <Percent className="w-4 h-4 mr-2" /> Marges IA
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-md bg-[#0a0d14] border-white/10">
          <DialogHeader>
            <DialogTitle className="text-white flex items-center gap-2 text-base">
              <Percent className="w-4 h-4 text-[#D9B35A]" /> Marges cibles du Prix IA
            </DialogTitle>
          </DialogHeader>
          <p className="text-xs text-white/50">Marge (%) appliquée par l'IA sur le coût d'approvisionnement estimé, par catégorie.</p>
          {!margins ? <Loader2 className="w-5 h-5 animate-spin text-[#D9B35A] mx-auto my-4" /> : (
            <div className="grid grid-cols-2 gap-2">
              {CATEGORIES.map((c) => (
                <label key={c.value} className="flex items-center justify-between gap-2 px-3 py-2 rounded-lg bg-white/[0.04] border border-white/10 text-xs text-white/75">
                  <span className="truncate">{c.icon} {c.label}</span>
                  <span className="flex items-center gap-1">
                    <input value={margins[c.value] ?? 25} data-testid={`margin-input-${c.value}`}
                      onChange={(e) => setMargins({ ...margins, [c.value]: e.target.value.replace(/\D/g, '') })}
                      className="w-12 h-7 px-1.5 rounded-md text-right text-white bg-white/[0.06] border border-white/15" />
                    %
                  </span>
                </label>
              ))}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)} className="border-white/10">Annuler</Button>
            <Button onClick={save} disabled={saving || !margins} data-testid="margin-save-btn" className="bg-[#D9B35A] hover:bg-[#c9a34a] text-black">
              {saving && <Loader2 className="w-4 h-4 mr-2 animate-spin" />} Enregistrer
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
};
