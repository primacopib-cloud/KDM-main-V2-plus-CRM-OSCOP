import { useCallback, useEffect, useState } from 'react';
import { PenLine, Loader2, CheckSquare, Square } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';

const fdate = (d) => (d ? new Date(d).toLocaleDateString('fr-FR') : '—');

export const AttestationQueue = ({ onSigned }) => {
  const [pending, setPending] = useState(null);
  const [selected, setSelected] = useState([]);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    fetch(`${API}/attestations/admin/pending`, { credentials: 'include', headers: getAuthHeaders() })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => { if (d) { setPending(d.pending); setSelected(d.pending.map((a) => a.id)); } })
      .catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const toggle = (id) => setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));

  const sign = async (ids) => {
    setBusy(true);
    try {
      const r = await fetch(`${API}/attestations/admin/countersign-bulk`, {
        method: 'POST', credentials: 'include',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Contre-signature impossible');
      toast.success(`${d.count} attestation(s) contre-signée(s)`, {
        description: 'PDF signés envoyés aux fournisseurs et archivés dans la GEDESS.',
      });
      load();
      onSigned?.();
    } catch (e) { toast.error(e.message); }
    setBusy(false);
  };

  if (!pending || pending.length === 0) return null;

  return (
    <div className="rounded-xl p-4" style={{ background: 'rgba(251,191,36,0.05)', border: '1px solid rgba(251,191,36,0.25)' }}
      data-testid="attestation-queue-panel">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
        <p className="flex items-center gap-2 text-sm font-semibold text-white/85">
          <PenLine className="w-4 h-4 text-[#FBBF24]" /> File d'attente — contre-signature O'SCOP / KDMARCHÉ ({pending.length})
        </p>
        <span className="inline-flex gap-2">
          <button type="button" disabled={busy || selected.length === 0} onClick={() => sign(selected)}
            data-testid="countersign-selection-btn"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold disabled:opacity-50"
            style={{ background: '#D9B35A', color: '#070A10' }}>
            {busy ? <Loader2 size={12} className="animate-spin" /> : <PenLine size={12} />}
            Contre-signer la sélection ({selected.length})
          </button>
        </span>
      </div>
      <div className="space-y-1.5">
        {pending.map((a) => (
          <button key={a.id} type="button" onClick={() => toggle(a.id)}
            data-testid={`queue-row-${a.id}`}
            className="w-full flex flex-wrap items-center justify-between gap-2 px-3 py-2 rounded-lg bg-white/[0.04] hover:bg-white/[0.07] text-xs text-left">
            <span className="inline-flex items-center gap-2 text-white/85">
              {selected.includes(a.id)
                ? <CheckSquare size={14} className="text-[#D9B35A] shrink-0" />
                : <Square size={14} className="text-white/30 shrink-0" />}
              <span>
                <b>{a.ref}</b> — {a.vendor_name} · {a.product_name}
                {a.replaced_ref && <span className="text-[#93C5FD]"> · renouvellement de {a.replaced_ref}</span>}
              </span>
            </span>
            <span className="text-white/40">émise le {fdate(a.created_at)} · plafond RCR {(a.plafond_cible_cents / 100).toFixed(2)} €</span>
          </button>
        ))}
      </div>
    </div>
  );
};
