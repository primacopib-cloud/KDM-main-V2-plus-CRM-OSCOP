import { useCallback, useEffect, useState } from 'react';
import { Archive, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';

export const RcrAnnualArchiveCard = () => {
  const [runs, setRuns] = useState([]);
  const [busy, setBusy] = useState(false);
  const [year, setYear] = useState(String(new Date().getFullYear() - 1));

  const load = useCallback(() => {
    fetch(`${API}/convention/admin/rcr-annual-archive/runs`, { credentials: 'include', headers: getAuthHeaders() })
      .then((r) => (r.ok ? r.json() : { runs: [] })).then((d) => setRuns(d.runs || [])).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const run = async () => {
    setBusy(true);
    try {
      const r = await fetch(`${API}/convention/admin/rcr-annual-archive/${year}`, {
        method: 'POST', credentials: 'include', headers: getAuthHeaders(),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Archivage impossible');
      toast.success(`Exercice ${year} : ${d.archived} archivé(s), ${d.already} déjà fait(s), ${d.errors} erreur(s)`);
      load();
    } catch (e) { toast.error(e.message); }
    setBusy(false);
  };

  return (
    <div className="rounded-xl p-4" style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)' }}
      data-testid="rcr-annual-archive-card">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
        <p className="flex items-center gap-2 text-sm font-semibold text-white/85">
          <Archive className="w-4 h-4 text-[#93C5FD]" /> Archivage GEDESS des relevés annuels fiscaux RCR
        </p>
        <span className="inline-flex items-center gap-2">
          <input value={year} onChange={(e) => setYear(e.target.value.replace(/\D/g, '').slice(0, 4))}
            data-testid="annual-archive-year-input"
            className="w-16 h-8 px-2 rounded-lg bg-white/[0.06] border border-white/15 text-xs text-white text-center" />
          <button type="button" disabled={busy || year.length !== 4} onClick={run} data-testid="annual-archive-run-btn"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold bg-white/[0.06] text-white/75 hover:text-[#E9CF8E] border border-white/15 disabled:opacity-50">
            {busy ? <Loader2 size={12} className="animate-spin" /> : <Archive size={12} />} Archiver maintenant
          </button>
        </span>
      </div>
      <p className="text-[10px] text-white/40 mb-2">
        Automatique au 1er janvier pour l'exercice écoulé (relance quotidienne + alerte email en cas d'échec).
      </p>
      {runs.length > 0 && (
        <div className="space-y-0.5" data-testid="annual-archive-runs">
          {runs.slice(0, 8).map((r) => (
            <p key={`${r.year}-${r.vendor_id}`} className="text-[10px] text-white/55">
              <b className={r.status === 'SUCCESS' ? 'text-[#A5E27E]' : 'text-red-300'}>{r.status}</b>
              {' '}· exercice {r.year} — {r.vendor_name || r.vendor_id}
              {r.ged_doc_id && <span className="text-white/35"> · doc GED {r.ged_doc_id.slice(0, 8)}</span>}
              {r.error && <span className="text-red-300/70"> · {r.error.slice(0, 60)}</span>}
            </p>
          ))}
        </div>
      )}
    </div>
  );
};
