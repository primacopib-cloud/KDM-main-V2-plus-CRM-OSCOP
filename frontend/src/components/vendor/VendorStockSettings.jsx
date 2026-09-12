import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Bell, Link2, Loader2, RefreshCw, Settings2 } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

// Paramètres stock & synchronisation catalogue (espace vendeur, onglet Mes produits)
export const VendorStockSettings = ({ vendorId, onChanged }) => {
  const [open, setOpen] = useState(false);
  const [threshold, setThreshold] = useState('');
  const [applying, setApplying] = useState(false);
  const [sync, setSync] = useState({ url: '', enabled: false });
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    if (!open || !vendorId) return;
    fetch(`${API}/api/vendors/${vendorId}/catalog-sync`, { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => d && setSync(d))
      .catch(() => {});
  }, [open, vendorId]);

  const applyThreshold = async () => {
    const t = parseInt(threshold, 10);
    if (Number.isNaN(t) || t < 0) return toast.error('Seuil invalide');
    setApplying(true);
    try {
      const r = await fetch(`${API}/api/vendor/products-threshold/${vendorId}`, {
        method: 'PUT', credentials: 'include',
        headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ threshold: t }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Échec');
      toast.success(d.message);
      onChanged?.();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setApplying(false);
    }
  };

  const saveSync = async (enabled) => {
    setSaving(true);
    try {
      const r = await fetch(`${API}/api/vendors/${vendorId}/catalog-sync`, {
        method: 'PUT', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: sync.url, enabled }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Échec');
      setSync((s) => ({ ...s, enabled }));
      toast.success(enabled ? 'Synchronisation quotidienne activée' : 'Configuration enregistrée');
    } catch (e) {
      toast.error(e.message);
    } finally {
      setSaving(false);
    }
  };

  const runNow = async () => {
    setRunning(true);
    try {
      const r = await fetch(`${API}/api/vendors/${vendorId}/catalog-sync/run`, {
        method: 'POST', credentials: 'include',
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Échec');
      setSync((s) => ({ ...s, last_status: d.status, last_message: d.message, last_run_at: new Date().toISOString() }));
      (d.status === 'success' ? toast.success : toast.error)(d.message);
      if (d.status === 'success') onChanged?.();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div>
      <div className="flex justify-end">
        <button type="button" onClick={() => setOpen(!open)}
          data-testid="vendor-stock-settings-btn"
          className="inline-flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-bold text-white/70 border border-white/10 hover:bg-white/5">
          <Settings2 className="w-4 h-4" /> Paramètres stock & synchro
        </button>
      </div>
      {open && (
        <div className="mt-3 grid md:grid-cols-2 gap-3" data-testid="vendor-stock-settings-panel">
          <div className="rounded-lg border border-white/15 bg-white/5 p-4 text-xs text-white/80">
            <p className="font-bold flex items-center gap-2 mb-2"><Bell className="w-4 h-4" /> Seuil d'alerte stock bas — tous les produits</p>
            <p className="text-white/50 mb-3">Applique le même seuil d'alerte à l'ensemble de votre catalogue (email + notification quand le stock passe dessous).</p>
            <div className="flex gap-2">
              <input type="number" min="0" value={threshold} onChange={(e) => setThreshold(e.target.value)}
                placeholder="Ex : 10" data-testid="bulk-threshold-input"
                className="w-24 px-3 py-2 rounded-lg bg-transparent border border-white/15 text-white" />
              <button type="button" disabled={applying} onClick={applyThreshold}
                data-testid="bulk-threshold-apply-btn"
                className="px-3 py-2 rounded-lg font-bold bg-amber-500/90 hover:bg-amber-400 text-black disabled:opacity-50">
                {applying ? 'Application…' : 'Appliquer à tous'}
              </button>
            </div>
          </div>
          <div className="rounded-lg border border-white/15 bg-white/5 p-4 text-xs text-white/80">
            <p className="font-bold flex items-center gap-2 mb-2"><Link2 className="w-4 h-4" /> Import planifié (synchronisation quotidienne)</p>
            <p className="text-white/50 mb-3">Déposez l'URL https publique de votre fichier catalogue (.csv ou .xlsx) : il sera importé automatiquement chaque jour.</p>
            <input type="url" value={sync.url} onChange={(e) => setSync((s) => ({ ...s, url: e.target.value }))}
              placeholder="https://mon-site.com/catalogue.csv" data-testid="catalog-sync-url-input"
              className="w-full px-3 py-2 rounded-lg bg-transparent border border-white/15 text-white mb-2" />
            <div className="flex flex-wrap gap-2 items-center">
              <button type="button" disabled={saving} onClick={() => saveSync(!sync.enabled)}
                data-testid="catalog-sync-toggle-btn"
                className={`px-3 py-2 rounded-lg font-bold disabled:opacity-50 ${sync.enabled
                  ? 'bg-emerald-600 hover:bg-emerald-500 text-white' : 'border border-white/15 text-white/70 hover:bg-white/5'}`}>
                {sync.enabled ? 'Synchro active — désactiver' : 'Activer la synchro quotidienne'}
              </button>
              <button type="button" disabled={running || !sync.url} onClick={runNow}
                data-testid="catalog-sync-run-btn"
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg font-bold border border-white/15 text-white/70 hover:bg-white/5 disabled:opacity-50">
                {running ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
                Tester maintenant
              </button>
            </div>
            {sync.last_run_at && (
              <p className="mt-2 text-white/50" data-testid="catalog-sync-last-status">
                Dernière synchro : {new Date(sync.last_run_at).toLocaleString('fr-FR')} — {' '}
                <span className={sync.last_status === 'success' ? 'text-emerald-400' : 'text-red-400'}>
                  {sync.last_message}
                </span>
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
