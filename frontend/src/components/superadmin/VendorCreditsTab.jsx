import { useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import { Coins, Save, Plus, Sparkles } from 'lucide-react';
import { CreditPromotionsPanel, CreditAnalyticsPanel } from './CreditPromotionsPanel';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const inputCls = 'h-9 px-2 rounded-lg bg-white/60 border border-black/10 text-sm text-right text-[#1F2A3A]';

export const VendorCreditsTab = () => {
  const [pricing, setPricing] = useState([]);
  const [vendors, setVendors] = useState([]);
  const [edits, setEdits] = useState({});
  const [grants, setGrants] = useState({});

  const refresh = useCallback(async () => {
    const [pR, vR] = await Promise.all([
      fetch(`${API}/admin/credit-pricing`, { credentials: 'include' }),
      fetch(`${API}/admin/vendors-credits`, { credentials: 'include' }),
    ]);
    if (pR.ok) setPricing((await pR.json()).pricing || []);
    if (vR.ok) setVendors((await vR.json()).vendors || []);
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const savePrice = async (p) => {
    const cost = parseInt(edits[p.action], 10);
    const r = await fetch(`${API}/admin/credit-pricing`, {
      method: 'PUT', credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: p.action, cost }),
    });
    if (r.ok) { toast.success(`${p.label} : ${cost} crédits`); refresh(); }
    else toast.error('Erreur mise à jour du barème');
  };

  const grant = async (v) => {
    const amount = parseInt(grants[v.id], 10);
    if (!amount) return;
    const r = await fetch(`${API}/admin/vendors/${v.id}/credits`, {
      method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ amount }),
    });
    const data = await r.json();
    if (r.ok) { toast.success(`Nouveau solde : ${data.credits} crédits`); setGrants({ ...grants, [v.id]: '' }); refresh(); }
    else toast.error('Erreur attribution');
  };

  return (
    <div className="space-y-6" data-testid="vendor-credits-tab">
      <div>
        <h2 className="text-xl font-bold text-[#1F2A3A] flex items-center gap-2">
          <Coins className="w-5 h-5 text-[#D9B35A]" /> Crédits vendeurs & Studio IA
        </h2>
        <p className="text-sm opacity-60 mt-1">Barème de consommation (fiches, photos, IA) et attribution de crédits aux vendeurs.</p>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <div className="glass-panel-soft rounded-[18px] p-5" data-testid="credit-pricing-panel">
          <h3 className="font-display text-lg mb-3 text-[#1F2A3A] flex items-center gap-2">
            <Sparkles size={15} className="text-purple-600" /> Barème (crédits par action)
          </h3>
          <div className="divide-y divide-black/5">
            {pricing.map((p) => (
              <div key={p.action} className="flex items-center justify-between gap-2 py-2" data-testid={`pricing-row-${p.action}`}>
                <span className="text-sm text-[#1F2A3A]">{p.label}</span>
                <div className="flex items-center gap-1.5">
                  <input type="number" min="0" value={edits[p.action] ?? p.cost}
                    onChange={(e) => setEdits({ ...edits, [p.action]: e.target.value })}
                    data-testid={`pricing-input-${p.action}`} className={`${inputCls} w-20`} />
                  <button type="button" onClick={() => savePrice(p)} data-testid={`pricing-save-${p.action}`}
                    className="p-1.5 rounded-lg opacity-50 hover:opacity-100 hover:bg-[#D9B35A]/15 text-[#B8860B]">
                    <Save size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="glass-panel-soft rounded-[18px] p-5" data-testid="vendors-credits-panel">
          <h3 className="font-display text-lg mb-3 text-[#1F2A3A]">Soldes vendeurs</h3>
          <div className="divide-y divide-black/5">
            {vendors.map((v) => (
              <div key={v.id} className="flex items-center justify-between gap-2 py-2" data-testid={`vendor-credits-row-${v.id}`}>
                <div className="min-w-0">
                  <p className="text-sm font-medium text-[#1F2A3A] truncate">{v.company_name || v.id}</p>
                  <p className="text-xs opacity-50">{v.email || '—'}</p>
                </div>
                <div className="flex items-center gap-1.5 shrink-0">
                  <span className="text-sm font-bold text-[#B8860B]" data-testid={`vendor-balance-${v.id}`}>{v.credits ?? 0}</span>
                  <input type="number" placeholder="+/-" value={grants[v.id] ?? ''}
                    onChange={(e) => setGrants({ ...grants, [v.id]: e.target.value })}
                    data-testid={`vendor-grant-input-${v.id}`} className={`${inputCls} w-20`} />
                  <button type="button" onClick={() => grant(v)} data-testid={`vendor-grant-btn-${v.id}`}
                    className="p-1.5 rounded-lg opacity-50 hover:opacity-100 hover:bg-emerald-500/10 text-emerald-600">
                    <Plus size={14} />
                  </button>
                </div>
              </div>
            ))}
            {vendors.length === 0 && <p className="text-sm opacity-50 py-3">Aucun vendeur.</p>}
          </div>
        </div>
      </div>

      <CreditAnalyticsPanel />
      <CreditPromotionsPanel />
    </div>
  );
};
