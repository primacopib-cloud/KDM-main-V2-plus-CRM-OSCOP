import { useEffect, useState } from 'react';
import { Loader2, Trash2 } from 'lucide-react';
import { API, getAuthHeaders } from '../../services/http';

const KIND_LABELS = { fact: 'Fait', preference: 'Préférence', rule: 'Consigne', correction: 'Correction' };
const KIND_COLORS = {
  fact: 'text-sky-300', preference: 'text-emerald-300', rule: 'text-[#E9CF8E]', correction: 'text-orange-300',
};

export const OracleMemoryMenu = () => {
  const [items, setItems] = useState(null);

  useEffect(() => {
    fetch(`${API}/oracle-memory`, { credentials: 'include', headers: getAuthHeaders() })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => setItems(d?.memories || []))
      .catch(() => setItems([]));
  }, []);

  const remove = async (id) => {
    setItems((xs) => xs.filter((x) => x.id !== id));
    try {
      await fetch(`${API}/oracle-memory/${id}`, {
        method: 'DELETE', credentials: 'include', headers: getAuthHeaders(),
      });
    } catch { /* noop */ }
  };

  return (
    <span className="absolute right-0 top-8 z-10 w-64 max-h-72 overflow-y-auto rounded-xl p-2 flex flex-col gap-1"
      data-testid="oracle-memory-menu"
      style={{ background: 'rgba(30,12,52,0.98)', border: '1px solid rgba(217,179,90,0.4)' }}>
      <span className="px-1 py-0.5 text-[9.5px] uppercase tracking-wider text-[#E9CF8E]/70 font-bold">
        Mémoire d'Oracle — ce qu'il a appris de vous
      </span>
      {items === null && (
        <span className="flex items-center gap-1.5 px-1 py-2 text-[10px] text-white/40">
          <Loader2 size={11} className="animate-spin" /> Chargement…
        </span>
      )}
      {items !== null && items.length === 0 && (
        <span className="px-1 py-2 text-[10px] text-white/45 leading-snug" data-testid="oracle-memory-empty">
          Rien encore — Oracle retiendra automatiquement vos préférences, consignes et corrections au fil des discussions.
        </span>
      )}
      {(items || []).map((m) => (
        <span key={m.id} className="flex items-start gap-1.5 px-1.5 py-1 rounded-lg bg-white/[0.04] border border-white/10"
          data-testid={`oracle-memory-${m.id}`}>
          <span className="flex-1 text-[10px] text-white/75 leading-snug">
            <span className={`font-bold ${KIND_COLORS[m.kind] || 'text-white/60'}`}>
              {KIND_LABELS[m.kind] || m.kind}
            </span>
            {' — '}{m.text}
          </span>
          <button type="button" onClick={() => remove(m.id)} data-testid={`oracle-memory-delete-${m.id}`}
            title="Oublier ce souvenir"
            className="text-white/30 hover:text-red-300 transition-colors shrink-0 mt-0.5">
            <Trash2 size={11} />
          </button>
        </span>
      ))}
      <span className="px-1 pt-1 text-[8.5px] text-white/35 leading-snug border-t border-white/10">
        Mémoire privée, réutilisée dans toutes vos discussions. Supprimez un souvenir pour qu'Oracle l'oublie.
      </span>
    </span>
  );
};
