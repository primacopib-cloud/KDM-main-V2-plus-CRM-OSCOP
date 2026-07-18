import { useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import { Percent, Plus, Archive, Trash2, BarChart3 } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const inputCls = 'h-9 px-2 rounded-lg bg-white/60 border border-black/10 text-sm text-[#1F2A3A]';

const EMPTY = { name: '', promo_type: 'bonus_purchase', value_percent: '', scope_profile: 'all', scope_territory: 'ALL', scope_category: 'all', scope_action: 'all', starts_at: '', ends_at: '' };
const TERRITORIES = ['ALL', 'GUADELOUPE', 'MARTINIQUE', 'GUYANE', 'REUNION', 'MAYOTTE', 'SAINT-MARTIN'];

export const CreditPromotionsPanel = () => {
  const [promos, setPromos] = useState([]);
  const [form, setForm] = useState(EMPTY);
  const [categories, setCategories] = useState([]);

  const refresh = useCallback(async () => {
    const r = await fetch(`${API}/admin/credit-promotions?include_archived=true`, { credentials: 'include' });
    if (r.ok) setPromos((await r.json()).promotions || []);
  }, []);

  useEffect(() => {
    refresh();
    fetch(`${API}/taxonomy/categories`).then((r) => r.ok && r.json()).then((d) => d && setCategories(d.categories || []));
  }, [refresh]);

  const create = async () => {
    const r = await fetch(`${API}/admin/credit-promotions`, {
      method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...form,
        value_percent: parseFloat(form.value_percent),
        starts_at: form.starts_at ? `${form.starts_at}T00:00:00+00:00` : null,
        ends_at: form.ends_at ? `${form.ends_at}T23:59:59+00:00` : null,
        active: true,
      }),
    });
    const d = await r.json();
    if (r.ok) { toast.success('Promotion créée'); setForm(EMPTY); refresh(); }
    else toast.error(typeof d.detail === 'string' ? d.detail : 'Erreur');
  };

  const act = async (id, method, path = '') => {
    const r = await fetch(`${API}/admin/credit-promotions/${id}${path}`, { method, credentials: 'include' });
    if (r.ok) { toast.success('OK'); refresh(); }
  };

  return (
    <div className="glass-panel-soft rounded-[18px] p-5" data-testid="credit-promotions-panel">
      <h3 className="font-display text-lg mb-3 text-[#1F2A3A] flex items-center gap-2">
        <Percent size={15} className="text-emerald-600" /> Bonus & Réductions de crédits
      </h3>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-2 mb-3">
        <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
          placeholder="Nom de la promotion" data-testid="promo-name" className={`${inputCls} col-span-2 md:col-span-1`} />
        <select value={form.promo_type} onChange={(e) => setForm({ ...form, promo_type: e.target.value })} data-testid="promo-type" className={inputCls}>
          <option value="bonus_purchase">Bonus à l&apos;achat (%)</option>
          <option value="discount_action">Réduction sur consommation (%)</option>
        </select>
        <input type="number" min="1" max="100" value={form.value_percent}
          onChange={(e) => setForm({ ...form, value_percent: e.target.value })}
          placeholder="%" data-testid="promo-value" className={inputCls} />
        <select value={form.scope_profile} onChange={(e) => setForm({ ...form, scope_profile: e.target.value })} data-testid="promo-profile" className={inputCls}>
          <option value="all">Tous profils</option>
          <option value="vendor">Vendeurs</option>
          <option value="buyer">Acheteurs</option>
        </select>
        <select value={form.scope_territory} onChange={(e) => setForm({ ...form, scope_territory: e.target.value })} data-testid="promo-territory" className={inputCls}>
          {TERRITORIES.map((t) => <option key={t} value={t}>{t === 'ALL' ? 'Tous territoires' : t}</option>)}
        </select>
        <select value={form.scope_category} onChange={(e) => setForm({ ...form, scope_category: e.target.value })} data-testid="promo-category" className={inputCls}>
          <option value="all">Toutes catégories</option>
          {categories.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
        </select>
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] opacity-50 shrink-0">Du</span>
          <input type="date" value={form.starts_at} onChange={(e) => setForm({ ...form, starts_at: e.target.value })}
            data-testid="promo-starts-at" className={`${inputCls} flex-1 min-w-0`} title="Début de l'offre flash (optionnel)" />
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] opacity-50 shrink-0">Au</span>
          <input type="date" value={form.ends_at} onChange={(e) => setForm({ ...form, ends_at: e.target.value })}
            data-testid="promo-ends-at" className={`${inputCls} flex-1 min-w-0`} title="Fin de l'offre flash (optionnel)" />
        </div>
      </div>
      <button type="button" onClick={create} disabled={!form.name || !form.value_percent}
        data-testid="promo-create-btn"
        className="btn-gold h-9 px-4 rounded-lg text-sm font-semibold inline-flex items-center gap-1.5 disabled:opacity-40 mb-4">
        <Plus size={13} /> Créer la promotion
      </button>

      <div className="divide-y divide-black/5">
        {promos.map((p) => (
          <div key={p.id} className={`flex items-center justify-between gap-2 py-2 ${p.archived ? 'opacity-40' : ''}`} data-testid={`promo-row-${p.id}`}>
            <div className="min-w-0">
              <p className="text-sm font-medium text-[#1F2A3A] truncate">
                {p.name} — <span className="text-emerald-600 font-bold">{p.value_percent}%</span>
                {p.archived && <span className="text-[9px] uppercase ml-2 px-1.5 py-0.5 rounded bg-black/10">archivée</span>}
              </p>
              <p className="text-[11px] opacity-50">
                {p.promo_type === 'bonus_purchase' ? 'Bonus achat' : 'Réduction conso'} · {p.scope_profile} · {p.scope_territory} · {p.scope_category}
                {(p.starts_at || p.ends_at) && (
                  <span className="ml-1.5 px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-600 text-[10px]" data-testid={`promo-window-${p.id}`}>
                    ⏱ {p.starts_at ? p.starts_at.slice(0, 10) : '…'} → {p.ends_at ? p.ends_at.slice(0, 10) : '…'}
                  </span>
                )}
              </p>
            </div>
            <div className="flex gap-1 shrink-0">
              {!p.archived && (
                <button type="button" onClick={() => act(p.id, 'POST', '/archive')} data-testid={`promo-archive-${p.id}`}
                  title="Archiver" className="p-1.5 rounded-lg opacity-40 hover:opacity-100 hover:bg-amber-500/10 text-amber-600">
                  <Archive size={13} />
                </button>
              )}
              <button type="button" onClick={() => window.confirm('Supprimer cette promotion ?') && act(p.id, 'DELETE')} data-testid={`promo-delete-${p.id}`}
                title="Supprimer" className="p-1.5 rounded-lg opacity-40 hover:opacity-100 hover:bg-red-500/10 text-red-500">
                <Trash2 size={13} />
              </button>
            </div>
          </div>
        ))}
        {promos.length === 0 && <p className="text-sm opacity-50 py-3">Aucune promotion.</p>}
      </div>
    </div>
  );
};

export const CreditAnalyticsPanel = () => {
  const [data, setData] = useState(null);

  useEffect(() => {
    fetch(`${API}/admin/credit-analytics`, { credentials: 'include' })
      .then((r) => r.ok && r.json()).then((d) => d && setData(d));
  }, []);

  const Section = ({ title, rows }) => (
    <div>
      <p className="text-[11px] uppercase tracking-wider opacity-50 mb-1">{title}</p>
      {(rows || []).slice(0, 5).map((r) => (
        <div key={r.key} className="flex justify-between text-xs py-0.5">
          <span className="truncate text-[#1F2A3A]">{r.key}</span>
          <span className="font-semibold text-[#B8860B]">{r.credits} cr.</span>
        </div>
      ))}
      {(!rows || rows.length === 0) && <p className="text-xs opacity-40">—</p>}
    </div>
  );

  if (!data) return null;
  return (
    <div className="glass-panel-soft rounded-[18px] p-5" data-testid="credit-analytics-panel">
      <h3 className="font-display text-lg mb-3 text-[#1F2A3A] flex items-center gap-2">
        <BarChart3 size={15} className="text-[#5B9BD5]" /> Suivi des crédits
      </h3>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-4 text-center">
        {[
          ['Achetés', data.totals.purchased, '#6FA82E'],
          ['Consommés', data.totals.consumed, '#B8860B'],
          ['Remboursés', data.totals.refunded, '#5B9BD5'],
          ['Revenus', `${data.totals.revenue_eur} €`, '#5B2E8C'],
        ].map(([label, value, color]) => (
          <div key={label} className="rounded-xl bg-white/50 border border-black/5 p-2.5">
            <p className="text-lg font-bold" style={{ color }}>{value}</p>
            <p className="text-[10px] uppercase opacity-50">{label}</p>
          </div>
        ))}
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Section title="Par service" rows={data.by_service} />
        <Section title="Par vendeur" rows={data.by_vendor} />
        <Section title="Par territoire" rows={data.by_territory} />
        <Section title="Par catégorie" rows={data.by_category} />
      </div>
    </div>
  );
};
