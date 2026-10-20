import { useState } from 'react';
import { Loader2 } from 'lucide-react';
import { API, getAuthHeaders } from '../../services/http';

export const OracleBulkProposals = ({ proposals, onRemove, onResult }) => {
  const [busyId, setBusyId] = useState(null);

  const act = async (path, p) => {
    if (busyId) return;
    setBusyId(p.id);
    try {
      const r = await fetch(`${API}/oracle-admin/${path}`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ proposal_id: p.id }),
      });
      const d = await r.json().catch(() => ({}));
      if (path === 'execute' && !r.ok) throw new Error(d.detail || 'Exécution impossible');
      onResult(path === 'execute' ? `✅ ${d.message}` : `Ligne annulée — ${p.summary}`);
    } catch (e) {
      onResult(`⚠ ${e.message}`);
    }
    setBusyId(null);
    onRemove(p.id);
  };

  if (!proposals.length) return null;
  return (
    <div className="rounded-xl p-3 space-y-2" data-testid="oracle-bulk-proposals"
      style={{ background: 'rgba(217,179,90,0.1)', border: '1.5px solid rgba(217,179,90,0.55)' }}>
      <p className="text-[10px] font-bold uppercase tracking-wider text-[#E9CF8E]">
        ⚠ {proposals.length} ajustement(s) de crédits — confirmez chaque ligne
      </p>
      {proposals.map((p, i) => (
        <div key={p.id} className="rounded-lg px-2 py-1.5 bg-white/[0.05] border border-white/10 space-y-1.5"
          data-testid={`oracle-bulk-row-${i}`}>
          <p className="text-[11px] text-white/85 leading-snug">{p.summary}</p>
          <div className="flex gap-1.5">
            <button type="button" onClick={() => act('execute', p)} disabled={busyId !== null}
              data-testid={`oracle-bulk-execute-${i}`}
              className="on-light gold-chip flex-1 h-7 rounded-full text-[10px] font-bold text-[#2A1045] disabled:opacity-50 transition-transform hover:scale-[1.02] flex items-center justify-center gap-1"
              style={{ background: 'linear-gradient(90deg, #E9CF8E, #D9B35A)' }}>
              {busyId === p.id ? <Loader2 size={11} className="animate-spin" /> : 'Exécuter'}
            </button>
            <button type="button" onClick={() => act('cancel', p)} disabled={busyId !== null}
              data-testid={`oracle-bulk-cancel-${i}`}
              className="flex-1 h-7 rounded-full text-[10px] font-bold text-white/70 border border-white/25 hover:bg-white/10 disabled:opacity-50 transition-colors">
              Annuler
            </button>
          </div>
        </div>
      ))}
    </div>
  );
};
