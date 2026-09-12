import { useEffect, useRef, useState } from 'react';
import { Gavel, RefreshCw, X } from 'lucide-react';
import { getAuthHeaders } from '../../services/http';

const API = process.env.REACT_APP_BACKEND_URL;

// Salle d'enchère live : polling 3 s des offres pendant qu'un lot est en cours
export const LiveAuctionRoom = ({ cid, onClose }) => {
  const [data, setData] = useState(null);
  const [flash, setFlash] = useState(null);
  const lastCount = useRef(0);

  useEffect(() => {
    let stop = false;
    const load = async () => {
      try {
        const r = await fetch(`${API}/api/admin/consultations/${cid}/live`, {
          headers: getAuthHeaders(), credentials: 'include',
        });
        if (!r.ok || stop) return;
        const d = await r.json();
        if (d.bids.length > lastCount.current && lastCount.current > 0) {
          setFlash(d.bids[0]?.id);
          setTimeout(() => setFlash(null), 2200);
        }
        lastCount.current = d.bids.length;
        setData(d);
      } catch { /* polling silencieux */ }
    };
    load();
    const iv = setInterval(load, 3000);
    return () => { stop = true; clearInterval(iv); };
  }, [cid]);

  const eur = (c) => (c == null ? '—' : `${(c / 100).toLocaleString('fr-FR', { minimumFractionDigits: 2 })} €`);
  const live = data?.consultation?.status === 'EN_COURS';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: 'rgba(15,5,25,0.8)' }} data-testid="live-auction-room">
      <div className="w-full max-w-2xl rounded-2xl p-5 max-h-[85vh] overflow-y-auto" style={{ background: '#1F0A33', border: '1px solid rgba(217,179,90,0.35)' }}>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <Gavel className="w-4 h-4 text-[#D9B35A]" />
            Salle d'enchère live — {data?.consultation?.ref || '…'}
            {live && (
              <span className="inline-flex items-center gap-1.5 text-[10px] font-bold text-red-300 bg-red-500/15 border border-red-400/40 rounded-full px-2 py-0.5" data-testid="live-badge">
                <span className="w-1.5 h-1.5 rounded-full bg-red-400 animate-pulse" /> EN DIRECT
              </span>
            )}
          </h3>
          <button type="button" onClick={onClose} data-testid="live-room-close" className="text-white/60 hover:text-white"><X className="w-4 h-4" /></button>
        </div>
        {!data ? (
          <p className="text-xs text-white/50 flex items-center gap-2"><RefreshCw className="w-3 h-3 animate-spin" /> Connexion à la salle…</p>
        ) : (
          <>
            <div className="grid grid-cols-3 gap-2 mb-4 text-center">
              <div className="rounded-xl p-3" style={{ background: 'rgba(255,255,255,0.04)' }}>
                <p className="text-[10px] text-white/50 uppercase">Fournisseurs inscrits</p>
                <p className="text-lg font-bold text-white" data-testid="live-entries-count">{data.entries_count}</p>
              </div>
              <div className="rounded-xl p-3" style={{ background: 'rgba(255,255,255,0.04)' }}>
                <p className="text-[10px] text-white/50 uppercase">Offres reçues</p>
                <p className="text-lg font-bold text-white" data-testid="live-bids-count">{data.bids.length}</p>
              </div>
              <div className="rounded-xl p-3" style={{ background: 'rgba(217,179,90,0.1)', border: '1px solid rgba(217,179,90,0.3)' }}>
                <p className="text-[10px] text-[#E9CF8E] uppercase">Meilleure offre HT</p>
                <p className="text-lg font-bold text-[#E9CF8E]" data-testid="live-best-amount">
                  {data.amounts_hidden ? '🔒 Scellée' : eur(data.best_amount_ht_cents)}
                </p>
              </div>
            </div>
            <p className="text-[11px] text-white/45 mb-2">
              {data.amounts_hidden
                ? 'Offres scellées : les montants restent masqués jusqu\'à la clôture (ouverture automatique des plis).'
                : 'Enchère inversée : la meilleure offre est la moins-disante. Actualisation automatique toutes les 3 secondes.'}
            </p>
            <div className="space-y-1.5" data-testid="live-bids-list">
              {data.bids.length === 0 && <p className="text-xs text-white/40 italic">Aucune offre pour le moment — en attente des fournisseurs…</p>}
              {data.bids.map((b) => (
                <div key={b.id} data-testid={`live-bid-${b.id}`}
                  className="flex items-center justify-between rounded-lg px-3 py-2 text-xs transition-colors"
                  style={{
                    background: flash === b.id ? 'rgba(140,198,62,0.18)' : 'rgba(255,255,255,0.04)',
                    border: `1px solid ${flash === b.id ? 'rgba(140,198,62,0.5)' : 'rgba(255,255,255,0.08)'}`,
                  }}>
                  <span className="text-white/85 font-semibold">{b.vendor}</span>
                  <span className="text-white/40">tour {b.round ?? 1} · {b.status}</span>
                  <span className="font-bold text-[#E9CF8E]">{b.sealed ? '🔒' : eur(b.amount_ht_cents)}</span>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
};
