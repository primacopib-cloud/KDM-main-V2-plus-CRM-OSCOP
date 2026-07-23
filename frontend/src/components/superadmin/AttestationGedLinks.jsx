import { useState } from 'react';
import { Archive, ExternalLink, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';

const STATUS = { signed: ['signée', '#7BC94E'], closed: ['clôturée', '#93C5FD'], pending_countersign: ['en attente', '#FBBF24'] };

export const AttestationGedLinks = ({ attestations }) => {
  const [busy, setBusy] = useState('');

  const openGed = async (a) => {
    setBusy(a.id);
    try {
      const r = await fetch(`${API}/attestations/${a.id}/ged-info`, { credentials: 'include', headers: getAuthHeaders() });
      const d = await r.json();
      if (!r.ok || !d.archived) throw new Error('Document non archivé dans la GEDESS');
      const doc = d.document;
      toast.success(`Archivée dans la GEDESS — ${a.ref}`, {
        description: doc
          ? `${doc.original_filename} · ${Math.round((doc.file_size || 0) / 1024)} Ko · catégorie ${doc.categorie} · doc ${d.doc_id.slice(0, 8)}…`
          : `Document GEDESS ${d.doc_id.slice(0, 8)}… (vérification live indisponible)`,
        duration: 8000,
      });
      if (d.gedess_url) window.open(`${d.gedess_url}/ged?doc=${d.doc_id}`, '_blank', 'noopener');
    } catch (e) { toast.error(e.message); }
    setBusy('');
  };

  if (!attestations || attestations.length === 0) return null;

  return (
    <div className="mt-2 space-y-1">
      <p className="text-[11px] uppercase tracking-wide text-white/40">Attestations récentes & archivage GEDESS</p>
      {attestations.slice(0, 6).map((a) => {
        const [label, color] = STATUS[a.status] || [a.status, '#999'];
        return (
          <div key={a.id} className="flex flex-wrap items-center justify-between gap-2 px-3 py-1.5 rounded-lg bg-white/[0.03] text-[11px]"
            data-testid={`ged-att-row-${a.id}`}>
            <span className="text-white/75">
              <b className="text-white/90">{a.ref}</b> · {a.vendor_name}
              <span className="font-bold" style={{ color }}> · {label}</span>
            </span>
            {a.ged_doc_id ? (
              <button type="button" disabled={busy === a.id} onClick={() => openGed(a)}
                data-testid={`ged-link-btn-${a.id}`}
                className="inline-flex items-center gap-1 px-2 py-1 rounded text-[10px] font-bold bg-[#7BC94E]/12 text-[#A5E27E] hover:bg-[#7BC94E]/20 disabled:opacity-50">
                {busy === a.id ? <Loader2 size={10} className="animate-spin" /> : <Archive size={10} />}
                GEDESS ✓ <ExternalLink size={9} />
              </button>
            ) : (
              <span className="text-[10px] text-white/30 inline-flex items-center gap-1"><Archive size={10} /> non archivée</span>
            )}
          </div>
        );
      })}
    </div>
  );
};
