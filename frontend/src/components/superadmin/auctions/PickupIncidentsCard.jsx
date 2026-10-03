import { useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle2 } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../../services/http';

// Superadmin : avoirs gagnants à régler + déductions POP'S (articles manquants au retrait)
export const PickupIncidentsCard = () => {
  const [data, setData] = useState(null);

  const load = () => fetch(`${API}/admin/auctions/pickup-incidents`, {
    credentials: 'include', headers: getAuthHeaders(),
  }).then((r) => r.json()).then(setData).catch(() => setData(null));

  useEffect(() => { load(); }, []);

  const settle = async (id) => {
    try {
      const r = await fetch(`${API}/admin/auctions/pickup-incidents/${id}/settle`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Erreur');
      toast.success('Avoir marqué comme réglé ✓');
      load();
    } catch (e) {
      toast.error(e.message);
    }
  };

  if (!data || !(data.incidents || []).length) return null;
  return (
    <div className="rounded-xl border border-amber-400/20 bg-amber-500/[0.04] p-3 mb-4" data-testid="pickup-incidents-card">
      <p className="text-[11px] font-bold text-amber-300 uppercase mb-1 flex items-center gap-1">
        <AlertTriangle className="w-3.5 h-3.5" /> Incidents de retrait — avoirs à régler ({data.pending_count})
      </p>
      <p className="text-[10px] text-white/50 mb-2">
        En attente : <b className="text-amber-300">{Number(data.pending_credit_eur).toFixed(2)} €</b> d'avoirs gagnants ·
        {' '}<b className="text-amber-300">{Number(data.pending_deduction_eur).toFixed(2)} €</b> à déduire des règlements POP'S
      </p>
      <div className="space-y-1.5 max-h-56 overflow-y-auto">
        {data.incidents.map((i) => (
          <div key={i.auction_id} className="rounded-lg border border-white/10 p-2 text-[10.5px] text-white/70"
            data-testid={`pickup-incident-${i.auction_id}`}>
            <p>
              <b className="text-[#E9CF8E]">{i.title}</b> · {i.reference} — manquant(s) : {(i.missing_names || []).join(', ')}
            </p>
            <p className="text-white/50">
              Gagnant {i.winner_name} : avoir <b className="text-amber-300">{Number(i.credit_eur).toFixed(2)} €</b> ·
              {' '}POP'S {i.pops_name || '—'} : déduction <b className="text-amber-300">{Number(i.pops_deduction_eur).toFixed(2)} €</b>
              {' '}(règlement ajusté)
            </p>
            {i.settled ? (
              <span className="text-emerald-300 font-bold" data-testid={`incident-settled-${i.auction_id}`}>
                ✓ Réglé le {new Date(i.settled_at).toLocaleDateString('fr-FR')}
              </span>
            ) : (
              <button onClick={() => settle(i.auction_id)} data-testid={`incident-settle-${i.auction_id}`}
                className="mt-1 inline-flex items-center gap-1 px-2.5 h-6 rounded-full text-[10px] font-bold text-emerald-300 border border-emerald-400/40 bg-emerald-500/10 hover:bg-emerald-500/20">
                <CheckCircle2 className="w-3 h-3" /> Marquer réglé (avoir + déduction)
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
