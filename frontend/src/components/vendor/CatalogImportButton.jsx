import { useRef, useState } from 'react';
import { toast } from 'sonner';
import { Loader2, Upload } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

// Import catalogue fournisseur (.csv ; UTF-8 ou .xlsx) selon l'annexe technique V1.0
export const CatalogImportButton = ({ vendorId, onImported }) => {
  const inputRef = useRef(null);
  const [busy, setBusy] = useState(false);
  const [report, setReport] = useState(null);

  const upload = async (file) => {
    if (!file) return;
    setBusy(true);
    setReport(null);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const r = await fetch(`${API}/api/vendors/${vendorId}/catalog-import`, {
        method: 'POST', body: fd, credentials: 'include',
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Import impossible');
      if (d.rejected) {
        setReport(d);
        toast.error(`Import rejeté — ${d.error_count} anomalie(s). Rapport envoyé par email.`);
      } else {
        toast.success(d.message);
        onImported?.();
      }
    } catch (e) {
      toast.error(e.message || 'Import impossible');
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = '';
    }
  };

  return (
    <div>
      <input ref={inputRef} type="file" accept=".csv,.xlsx" className="hidden"
        data-testid="catalog-import-input"
        onChange={(e) => upload(e.target.files?.[0])} />
      <button type="button" disabled={busy} onClick={() => inputRef.current?.click()}
        data-testid="catalog-import-btn"
        className="inline-flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-bold text-white/85 border border-white/15 hover:bg-white/5 disabled:opacity-50">
        {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
        Importer catalogue (.csv / .xlsx)
      </button>
      {report?.rejected && (
        <div className="mt-3 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-300 max-h-48 overflow-y-auto"
          data-testid="catalog-import-errors">
          <p className="font-bold mb-1">Fichier rejeté — {report.error_count} anomalie(s) :</p>
          <ul className="list-disc pl-4 space-y-0.5">
            {report.errors.map((e, i) => <li key={i}>{e}</li>)}
          </ul>
        </div>
      )}
    </div>
  );
};
