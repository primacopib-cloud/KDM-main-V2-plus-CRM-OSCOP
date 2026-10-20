import { useEffect, useState } from 'react';
import { Loader2, Trash2, Users, Eraser, FileDown } from 'lucide-react';
import { API, getAuthHeaders } from '../../services/http';

const KIND_LABELS = { fact: 'Fait', preference: 'Préférence', rule: 'Consigne', correction: 'Correction' };
const KIND_COLORS = {
  fact: 'text-sky-300', preference: 'text-emerald-300', rule: 'text-[#E9CF8E]', correction: 'text-orange-300',
};

const MemoryRow = ({ m, onDelete, onShare, shared }) => (
  <span className="flex items-start gap-1.5 px-1.5 py-1 rounded-lg bg-white/[0.04] border border-white/10"
    data-testid={`oracle-memory-${m.id}`}>
    <span className="flex-1 text-[10px] text-white/75 leading-snug">
      <span className={`font-bold ${KIND_COLORS[m.kind] || 'text-white/60'}`}>
        {KIND_LABELS[m.kind] || m.kind}
      </span>
      {' — '}{m.text}
      {shared && m.created_by && (
        <span className="block text-[8.5px] text-white/35">partagée par {m.created_by}</span>
      )}
    </span>
    {onShare && (
      <button type="button" onClick={() => onShare(m.id)} data-testid={`oracle-memory-share-${m.id}`}
        title="Partager cette consigne avec toute l'équipe admin"
        className="text-white/30 hover:text-[#E9CF8E] transition-colors shrink-0 mt-0.5">
        <Users size={11} />
      </button>
    )}
    <button type="button" onClick={() => onDelete(m.id)} data-testid={`oracle-memory-delete-${m.id}`}
      title="Oublier ce souvenir"
      className="text-white/30 hover:text-red-300 transition-colors shrink-0 mt-0.5">
      <Trash2 size={11} />
    </button>
  </span>
);

export const OracleMemoryMenu = () => {
  const [items, setItems] = useState(null);
  const [shared, setShared] = useState([]);
  const [team, setTeam] = useState(null);
  const [teamLabel, setTeamLabel] = useState('');
  const [confirmAll, setConfirmAll] = useState(false);

  useEffect(() => {
    fetch(`${API}/oracle-memory`, { credentials: 'include', headers: getAuthHeaders() })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        setItems(d?.memories || []);
        setShared(d?.shared || []);
        setTeam(d?.team || null);
        setTeamLabel(d?.team_label || '');
      })
      .catch(() => setItems([]));
  }, []);

  const remove = async (id) => {
    setItems((xs) => (xs || []).filter((x) => x.id !== id));
    setShared((xs) => xs.filter((x) => x.id !== id));
    try {
      await fetch(`${API}/oracle-memory/${id}`, {
        method: 'DELETE', credentials: 'include', headers: getAuthHeaders(),
      });
    } catch { /* noop */ }
  };

  const share = async (id) => {
    const m = (items || []).find((x) => x.id === id);
    if (!m) return;
    setItems((xs) => xs.filter((x) => x.id !== id));
    setShared((xs) => [{ ...m, created_by: 'vous' }, ...xs]);
    try {
      await fetch(`${API}/oracle-memory/${id}/share`, {
        method: 'POST', credentials: 'include', headers: getAuthHeaders(),
      });
    } catch { /* noop */ }
  };

  const forgetAll = async () => {
    if (!confirmAll) { setConfirmAll(true); return; }
    setConfirmAll(false);
    setItems([]);
    try {
      await fetch(`${API}/oracle-memory/all`, {
        method: 'DELETE', credentials: 'include', headers: getAuthHeaders(),
      });
    } catch { /* noop */ }
  };

  return (
    <span className="absolute right-0 top-8 z-10 w-64 max-h-80 overflow-y-auto rounded-xl p-2 flex flex-col gap-1"
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
        <MemoryRow key={m.id} m={m} onDelete={remove} onShare={team ? share : null} />
      ))}
      {items !== null && items.length > 0 && (
        <>
          <a href={`${API}/oracle-memory/export.pdf`} target="_blank" rel="noreferrer"
            data-testid="oracle-memory-export-pdf"
            className="mt-0.5 flex items-center justify-center gap-1.5 h-7 rounded-lg text-[10px] font-bold border bg-white/[0.04] border-white/15 text-white/55 hover:text-[#E9CF8E] hover:border-[#D9B35A]/40 transition-colors">
            <FileDown size={11} /> Exporter ma mémoire en PDF (RGPD)
          </a>
          <button type="button" onClick={forgetAll} data-testid="oracle-memory-forget-all"
            className={`flex items-center justify-center gap-1.5 h-7 rounded-lg text-[10px] font-bold border transition-colors ${
              confirmAll
                ? 'bg-red-500/25 border-red-400/60 text-red-200'
                : 'bg-white/[0.04] border-white/15 text-white/55 hover:text-red-300 hover:border-red-400/40'}`}>
            <Eraser size={11} />
            {confirmAll ? 'Confirmer l\'oubli total ? (irréversible)' : 'Tout oublier (RGPD)'}
          </button>
        </>
      )}
      {team && (
        <>
          <span className="px-1 pt-1.5 text-[9.5px] uppercase tracking-wider text-[#E9CF8E]/70 font-bold border-t border-white/10"
            data-testid="oracle-memory-shared-title">
            <Users size={10} className="inline mr-1 -mt-0.5" />Consignes partagées — {teamLabel}
          </span>
          {shared.length === 0 && (
            <span className="px-1 py-1 text-[9.5px] text-white/40 leading-snug" data-testid="oracle-memory-shared-empty">
              Aucune consigne collective — partagez un souvenir avec <Users size={9} className="inline -mt-0.5" /> ou
              dictez une règle d'équipe à Oracle.
            </span>
          )}
          {shared.map((m) => (
            <MemoryRow key={m.id} m={m} onDelete={remove} shared />
          ))}
        </>
      )}
      <span className="px-1 pt-1 text-[8.5px] text-white/35 leading-snug border-t border-white/10">
        Mémoire privée réutilisée dans toutes vos discussions{team ? ` ; les consignes partagées s'appliquent à tous les membres de votre équipe (${teamLabel})` : ''}.
        Exportez votre mémoire en PDF avant « Tout oublier » (conformité RGPD).
      </span>
    </span>
  );
};
