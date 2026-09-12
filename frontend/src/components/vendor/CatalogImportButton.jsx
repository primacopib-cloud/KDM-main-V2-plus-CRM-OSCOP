import { useRef, useState } from 'react';
import { toast } from 'sonner';
import { CheckCircle2, FileDown, History, Loader2, Upload, XCircle } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

// Import catalogue fournisseur (.csv ; UTF-8 ou .xlsx) : aperçu → confirmation, avec historique
export const CatalogImportButton = ({ vendorId, onImported }) => {
  const inputRef = useRef(null);
  const [busy, setBusy] = useState(false);
  const [report, setReport] = useState(null);
  const [preview, setPreview] = useState(null);
  const [pendingFile, setPendingFile] = useState(null);
  const [history, setHistory] = useState(null);

  const upload = async (file, confirm = false) => {
    if (!file) return;
    setBusy(true);
    setReport(null);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const r = await fetch(`${API}/api/vendors/${vendorId}/catalog-import${confirm ? '?confirm=true' : ''}`, {
        method: 'POST', body: fd, credentials: 'include',
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Import impossible');
      if (d.rejected) {
        setPreview(null);
        setPendingFile(null);
        setReport(d);
        toast.error(`Import rejeté — ${d.error_count} anomalie(s). Rapport envoyé par email.`);
      } else if (d.preview) {
        setPreview(d);
        setPendingFile(file);
      } else {
        setPreview(null);
        setPendingFile(null);
        toast.success(d.message);
        onImported?.();
      }
      if (history) fetchHistory();
    } catch (e) {
      toast.error(e.message || 'Import impossible');
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = '';
    }
  };

  const fetchHistory = async () => {
    try {
      const r = await fetch(`${API}/api/vendors/${vendorId}/catalog-imports`, { credentials: 'include' });
      const d = await r.json();
      setHistory(d.items || []);
    } catch {
      toast.error("Impossible de charger l'historique");
    }
  };

  return (
    <div className="w-full space-y-3">
      <div className="flex justify-end items-center gap-2 flex-wrap">
        <span className="text-xs text-white/50 mr-1">Modèle officiel :</span>
        <a href={`${API}/api/vendors/catalog-template/csv`} download
          data-testid="catalog-template-csv-link"
          className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-bold text-white/70 border border-white/10 hover:bg-white/5">
          <FileDown className="w-4 h-4" /> CSV
        </a>
        <a href={`${API}/api/vendors/catalog-template/xlsx`} download
          data-testid="catalog-template-xlsx-link"
          className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-bold text-white/70 border border-white/10 hover:bg-white/5">
          <FileDown className="w-4 h-4" /> XLSX
        </a>
        <input ref={inputRef} type="file" accept=".csv,.xlsx" className="hidden"
          data-testid="catalog-import-input"
          onChange={(e) => upload(e.target.files?.[0])} />
        <button type="button" onClick={() => (history ? setHistory(null) : fetchHistory())}
          data-testid="catalog-import-history-btn"
          className="inline-flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-bold text-white/85 border border-white/15 hover:bg-white/5">
          <History className="w-4 h-4" /> Historique imports
        </button>
        <button type="button" disabled={busy} onClick={() => inputRef.current?.click()}
          data-testid="catalog-import-btn"
          className="inline-flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-bold text-white/85 border border-white/15 hover:bg-white/5 disabled:opacity-50">
          {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
          Importer catalogue (.csv / .xlsx)
        </button>
      </div>

      {preview && (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-white/85"
          data-testid="catalog-import-preview">
          <p className="font-bold mb-2">Aperçu — {preview.total} produit(s) détecté(s) dans {pendingFile?.name}. Rien n'a encore été créé.</p>
          <div className="max-h-56 overflow-y-auto">
            <table className="w-full text-left">
              <thead><tr className="text-white/50">
                <th className="pr-2 pb-1">SKU</th><th className="pr-2 pb-1">Désignation</th>
                <th className="pr-2 pb-1">Prix HT</th><th className="pr-2 pb-1">TVA</th>
                <th className="pr-2 pb-1">Stock</th><th className="pb-1">Image</th>
              </tr></thead>
              <tbody>
                {preview.products.map((p) => (
                  <tr key={p.sku} className="border-t border-white/10">
                    <td className="pr-2 py-1 font-mono">{p.sku}</td>
                    <td className="pr-2 py-1">{p.name}</td>
                    <td className="pr-2 py-1">{p.price_ht.toFixed(2)} €</td>
                    <td className="pr-2 py-1">{p.tva_rate} %</td>
                    <td className="pr-2 py-1">{p.stock_quantity}</td>
                    <td className="py-1">{p.image_url ? '🖼 oui' : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex gap-2 mt-3">
            <button type="button" disabled={busy} onClick={() => upload(pendingFile, true)}
              data-testid="catalog-import-confirm-btn"
              className="px-3 py-2 rounded-lg text-xs font-bold bg-emerald-600 hover:bg-emerald-500 text-white disabled:opacity-50">
              {busy ? 'Import en cours…' : `Confirmer l'import (${preview.total})`}
            </button>
            <button type="button" onClick={() => { setPreview(null); setPendingFile(null); }}
              data-testid="catalog-import-cancel-btn"
              className="px-3 py-2 rounded-lg text-xs font-bold border border-white/15 text-white/70 hover:bg-white/5">
              Annuler
            </button>
          </div>
        </div>
      )}

      {report?.rejected && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-300 max-h-48 overflow-y-auto"
          data-testid="catalog-import-errors">
          <p className="font-bold mb-1">Fichier rejeté — {report.error_count} anomalie(s) :</p>
          <ul className="list-disc pl-4 space-y-0.5">
            {report.errors.map((e, i) => <li key={i}>{e}</li>)}
          </ul>
        </div>
      )}

      {history && (
        <div className="rounded-lg border border-white/15 bg-white/5 p-3 text-xs text-white/80"
          data-testid="catalog-import-history">
          <p className="font-bold mb-2">Historique des imports</p>
          {history.length === 0 ? <p className="text-white/50">Aucun import pour le moment.</p> : (
            <ul className="space-y-1.5">
              {history.map((h) => (
                <li key={h.id} className="flex items-center gap-2 border-t border-white/10 pt-1.5 first:border-0 first:pt-0">
                  {h.status === 'success'
                    ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                    : <XCircle className="w-3.5 h-3.5 text-red-400 shrink-0" />}
                  <span className="text-white/50 shrink-0">{new Date(h.created_at).toLocaleString('fr-FR')}</span>
                  <span className="truncate">{h.filename}</span>
                  <span className="ml-auto shrink-0">
                    {h.status === 'success'
                      ? `${h.created ?? 0} créé(s), ${h.updated ?? 0} màj${h.images_downloaded ? `, ${h.images_downloaded} image(s)` : ''}`
                      : `rejeté — ${h.error_count} anomalie(s)`}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
};
