import { useEffect, useState, useCallback } from 'react';
import { HandCoins, Check, X } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';
import { Button } from '../ui/button';

const STATUS = {
  NEW: ['Nouveau', 'bg-amber-500/15 text-amber-300 border-amber-400/30'],
  ACCEPTED: ['Retenu', 'bg-emerald-500/15 text-emerald-300 border-emerald-400/30'],
  DECLINED: ['Décliné', 'bg-red-500/15 text-red-300 border-red-400/30'],
};

export const FinancingInterestsPanel = () => {
  const [items, setItems] = useState([]);
  const [busy, setBusy] = useState(null);

  const load = useCallback(() => {
    fetch(`${API}/investor/financing-interests`, { headers: getAuthHeaders() })
      .then((r) => r.json())
      .then((d) => setItems(d.interests || []))
      .catch(() => {});
  }, []);
  useEffect(load, [load]);

  const decide = async (it, decision) => {
    setBusy(it.id);
    try {
      const res = await fetch(`${API}/investor/financing-interests/${it.id}/decision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ decision }),
      });
      const d = await res.json();
      if (!res.ok) throw new Error(d.detail || 'Erreur');
      toast.success(decision === 'accept' ? 'Intérêt retenu — investisseur notifié' : 'Intérêt décliné — investisseur notifié');
      load();
    } catch (e) {
      toast.error(String(e.message || e));
    } finally {
      setBusy(null);
    }
  };

  if (items.length === 0) return null;
  return (
    <div className="glass-panel-soft rounded-[18px] p-5 mt-5" data-testid="financing-interests-panel">
      <h3 className="text-lg font-bold text-white flex items-center gap-2 mb-3">
        <HandCoins className="w-5 h-5 text-[#D9B35A]" /> Intérêts investisseurs
        <span className="text-sm font-normal text-white/50">({items.length})</span>
      </h3>
      <div className="space-y-2">
        {items.map((it) => {
          const [label, cls] = STATUS[it.status] || STATUS.NEW;
          return (
            <div key={it.id} className="flex items-center justify-between gap-3 flex-wrap p-3 rounded-xl bg-white/[0.03] border border-white/[0.08]"
              data-testid={`interest-row-${it.id}`}>
              <div className="text-sm">
                <b className="text-white">{it.investor_name}</b>
                <span className="text-white/60"> ({it.investor_email})</span>
                <span className="text-white/60"> · souhaite financer </span>
                <b className="text-[#E9CF8E]">{it.operation_reference}</b>
                <div className="text-white/50 text-[11px]">{new Date(it.created_at).toLocaleString('fr-FR')}</div>
              </div>
              <div className="flex items-center gap-2">
                <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border ${cls}`}>{label}</span>
                {it.status === 'NEW' && (
                  <>
                    <Button size="sm" disabled={busy === it.id} onClick={() => decide(it, 'accept')}
                      data-testid={`interest-accept-${it.id}`}
                      className="h-8 bg-emerald-600 hover:bg-emerald-500 text-white">
                      <Check className="w-3.5 h-3.5 mr-1" /> Accepter
                    </Button>
                    <Button size="sm" variant="outline" disabled={busy === it.id} onClick={() => decide(it, 'decline')}
                      data-testid={`interest-decline-${it.id}`}
                      className="h-8 border-red-400/40 text-red-300 hover:bg-red-500/10">
                      <X className="w-3.5 h-3.5 mr-1" /> Décliner
                    </Button>
                  </>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
