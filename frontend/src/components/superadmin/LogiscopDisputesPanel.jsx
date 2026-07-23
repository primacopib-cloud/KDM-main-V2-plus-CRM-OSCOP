import { useCallback, useEffect, useState } from 'react';
import { Scale, Download } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';

const STATUSES = [['OPEN', 'Ouvert'], ['UNDER_REVIEW', 'En instruction'], ['RESOLVED', 'Résolu']];
const RESPS = [['INDETERMINEE', 'Indéterminée'], ['TRANSPORTEUR', 'Transporteur'],
  ['DONNEUR_ORDRE', 'Donneur d\'Ordre'], ['PARTAGEE', 'Partagée']];
const STATUS_COLOR = { OPEN: '#F87171', UNDER_REVIEW: '#FBBF24', RESOLVED: '#7BC94E' };

export const LogiscopDisputesPanel = () => {
  const [disputes, setDisputes] = useState([]);
  const [notes, setNotes] = useState({});
  const sel = 'h-7 px-1.5 rounded bg-white/[0.06] border border-white/15 text-[10px] text-white';

  const load = useCallback(() => {
    fetch(`${API}/logiscop-transport/admin/disputes`, { credentials: 'include', headers: getAuthHeaders() })
      .then((r) => (r.ok ? r.json() : [])).then(setDisputes).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const update = async (d, body, msg) => {
    try {
      const r = await fetch(`${API}/logiscop-transport/admin/disputes/${d.id}`, {
        method: 'PATCH', credentials: 'include',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify(body),
      });
      if (!r.ok) throw new Error((await r.json()).detail || 'Mise à jour impossible');
      toast.success(msg);
      load();
    } catch (e) { toast.error(e.message); }
  };

  const download = async (path, filename) => {
    const r = await fetch(`${API}${path}`, { credentials: 'include', headers: getAuthHeaders() });
    if (!r.ok) { toast.error('Pièce indisponible'); return; }
    const url = window.URL.createObjectURL(await r.blob());
    const a = document.createElement('a'); a.href = url; a.download = filename; a.click();
    window.URL.revokeObjectURL(url);
  };

  if (!disputes.length) return null;

  return (
    <div className="mb-4 rounded-lg p-3 bg-red-500/[0.04] border border-red-500/20" data-testid="admin-disputes-panel">
      <p className="flex items-center gap-2 text-[11px] font-bold text-white/60 mb-2">
        <Scale size={12} className="text-red-300" /> Dossiers de litige ({disputes.length}) — incidents température (article 12)
      </p>
      <div className="space-y-2">
        {disputes.map((d) => (
          <div key={d.id} className="rounded-lg p-2.5 bg-white/[0.03] border border-white/[0.08] text-[11px]"
            data-testid={`admin-dispute-${d.ref}`}>
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-bold text-white">{d.ref}</span>
              <span className="text-white/50">OT {d.ot_ref} · {d.company_name}</span>
              <span className="font-bold" style={{ color: STATUS_COLOR[d.status] }}>
                {STATUSES.find(([v]) => v === d.status)?.[1]}
              </span>
              {d.incident && (
                <span className="text-white/45">
                  {d.incident.violations_count} hors consigne {d.incident.consigne}±{d.incident.tolerance} °C
                  (min {d.incident.min} / max {d.incident.max})
                </span>
              )}
              <span className="ml-auto inline-flex items-center gap-1.5">
                <select value={d.status} className={sel} data-testid={`dispute-status-${d.ref}`}
                  onChange={(e) => update(d, { status: e.target.value }, `Litige ${d.ref} → ${e.target.value}`)}>
                  {STATUSES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
                <select value={d.responsibility} className={sel} data-testid={`dispute-resp-${d.ref}`}
                  onChange={(e) => update(d, { responsibility: e.target.value }, `Responsabilité → ${e.target.value}`)}>
                  {RESPS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              </span>
            </div>
            <div className="mt-1.5 flex flex-wrap items-center gap-2">
              <input placeholder="Note de résolution…" value={notes[d.id] ?? d.resolution_note ?? ''}
                data-testid={`dispute-note-${d.ref}`}
                onChange={(e) => setNotes({ ...notes, [d.id]: e.target.value })}
                className="flex-1 min-w-[220px] h-7 px-2 rounded bg-white/[0.06] border border-white/15 text-[10px] text-white placeholder:text-white/35" />
              <button type="button" data-testid={`dispute-note-save-${d.ref}`}
                onClick={() => update(d, { resolution_note: notes[d.id] ?? d.resolution_note ?? '' }, 'Note enregistrée')}
                className="px-2 py-1 rounded-lg text-[10px] font-bold bg-white/[0.06] text-white/70 hover:text-[#E9CF8E] border border-white/15">
                Enregistrer
              </button>
              {(d.pieces || []).map((p) => (
                <button key={p.id} type="button"
                  onClick={() => download(`/logiscop-transport/disputes/pieces/${p.id}/download`, p.name)}
                  className="inline-flex items-center gap-1 text-[10px] text-[#93C5FD] hover:text-[#E9CF8E]">
                  <Download size={10} /> {p.name}
                </button>
              ))}
            </div>
            {(d.timeline || []).length > 0 && (
              <p className="mt-1 text-[10px] text-white/35">
                {d.timeline[d.timeline.length - 1].at.slice(0, 16).replace('T', ' ')} — {d.timeline[d.timeline.length - 1].action}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
