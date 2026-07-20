import { useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import { ShoppingBag, Search, Save, Ban, CheckCircle2 } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const BuyersTab = () => {
  const [buyers, setBuyers] = useState([]);
  const [q, setQ] = useState('');
  const [credits, setCredits] = useState({});

  const refresh = useCallback(async () => {
    const r = await fetch(`${API}/admin/buyers${q ? `?q=${encodeURIComponent(q)}` : ''}`, { credentials: 'include' });
    if (r.ok) setBuyers((await r.json()).buyers || []);
  }, [q]);

  useEffect(() => { refresh(); }, [refresh]);

  const saveCredits = async (b) => {
    const value = parseInt(credits[b.id], 10);
    const r = await fetch(`${API}/admin/buyers/${b.id}/credits`, {
      method: 'PATCH', credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ credits: value }),
    });
    if (r.ok) { toast.success(`Crédits mis à jour : ${value}`); refresh(); }
    else toast.error('Erreur mise à jour crédits');
  };

  const toggleSuspend = async (b) => {
    const r = await fetch(`${API}/admin/buyers/${b.id}/suspend`, {
      method: 'PATCH', credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ suspended: !b.suspended }),
    });
    if (r.ok) { toast.success(b.suspended ? 'Compte réactivé' : 'Compte suspendu'); refresh(); }
  };

  return (
    <div className="space-y-6" data-testid="buyers-tab">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <ShoppingBag className="w-5 h-5 text-[#D9B35A]" /> Gestion de l&apos;Espace Acheteur
          </h2>
          <p className="text-sm text-white/55 mt-1">Comptes acheteurs B2B : crédits, commandes, suspension. Organisations complètes via Admin Orgs.</p>
        </div>
        <div className="relative">
          <Search size={14} className="absolute left-3 top-3 text-white/40" />
          <input
            value={q} onChange={(e) => setQ(e.target.value)}
            placeholder="Rechercher un acheteur…"
            data-testid="buyers-search-input"
            className="h-10 pl-9 pr-3 rounded-lg bg-white/[0.06] border border-white/15 text-sm text-white placeholder:text-white/35 w-64"
          />
        </div>
      </div>

      <div className="glass-panel-soft rounded-[18px] p-5 overflow-x-auto" data-testid="buyers-list">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-[11px] uppercase tracking-wider text-white/50 text-left border-b border-white/10">
              <th className="py-2 pr-3">Acheteur</th>
              <th className="py-2 pr-3">Société</th>
              <th className="py-2 pr-3 text-right">Commandes</th>
              <th className="py-2 pr-3 text-right">Crédits</th>
              <th className="py-2 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {buyers.map((b) => (
              <tr key={b.id} className={`border-b border-white/[0.06] ${b.suspended ? 'opacity-50' : ''}`} data-testid={`buyer-row-${b.id}`}>
                <td className="py-2.5 pr-3">
                  <p className="font-medium text-white">{b.contact_name || '—'}</p>
                  <p className="text-xs text-white/45">{b.email}</p>
                </td>
                <td className="py-2.5 pr-3 text-white/85">{b.company_name || '—'}</td>
                <td className="py-2.5 pr-3 text-right text-white/85">{b.orders_count}</td>
                <td className="py-2.5 pr-3 text-right">
                  <input
                    type="number" min="0"
                    value={credits[b.id] ?? b.credits ?? 0}
                    onChange={(e) => setCredits({ ...credits, [b.id]: e.target.value })}
                    data-testid={`buyer-credits-${b.id}`}
                    className="h-8 w-24 px-2 rounded-lg bg-white/[0.06] border border-[#D9B35A]/30 text-sm text-right font-bold text-[#E9CF8E]"
                  />
                </td>
                <td className="py-2.5 text-right whitespace-nowrap">
                  <button type="button" onClick={() => saveCredits(b)} data-testid={`buyer-save-credits-${b.id}`}
                    title="Enregistrer les crédits"
                    className="p-1.5 rounded-lg bg-[#D9B35A]/20 border border-[#D9B35A]/40 text-[#E9CF8E] hover:bg-[#D9B35A]/35 transition-colors">
                    <Save size={14} />
                  </button>
                  <button type="button" onClick={() => toggleSuspend(b)} data-testid={`buyer-suspend-${b.id}`}
                    title={b.suspended ? 'Réactiver' : 'Suspendre'}
                    className={`p-1.5 rounded-lg ml-1 border transition-colors ${b.suspended ? 'bg-emerald-500/10 border-emerald-500/25 text-emerald-400 hover:bg-emerald-500/20' : 'bg-red-500/10 border-red-500/25 text-red-400 hover:bg-red-500/20'}`}>
                    {b.suspended ? <CheckCircle2 size={14} /> : <Ban size={14} />}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {buyers.length === 0 && <p className="text-sm text-white/45 text-center py-6">Aucun acheteur trouvé.</p>}
      </div>
    </div>
  );
};
