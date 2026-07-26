import { useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import { Percent, Plus, Archive, Trash2, BarChart3, Send } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const inputCls = 'h-9 px-2 rounded-lg bg-white/[0.06] border border-white/15 text-sm text-white placeholder:text-white/35';

const EMPTY = { name: '', promo_type: 'bonus_purchase', value_percent: '', scope_profile: 'all', scope_territory: 'ALL', scope_category: 'all', scope_action: 'all', scope_product_type: '', scope_brand: '', scope_relay: 'all', min_quantity: '', audience: 'all', audience_emails: '', countdown_enabled: false, countdown_pages: [], starts_at: '', ends_at: '' };
const COUNTDOWN_PAGES = [['landing', 'Accueil'], ['catalog', 'Catalogue'], ['pass', 'Page PASS'], ['kdmarche', 'KDMARCHÉ']];
const TERRITORIES = ['ALL', 'GUADELOUPE', 'MARTINIQUE', 'GUYANE', 'REUNION', 'MAYOTTE', 'SAINT-MARTIN'];

export const CreditPromotionsPanel = () => {
  const [promos, setPromos] = useState([]);
  const [form, setForm] = useState(EMPTY);
  const [categories, setCategories] = useState([]);
  const [relays, setRelays] = useState([]);

  const refresh = useCallback(async () => {
    const r = await fetch(`${API}/admin/credit-promotions?include_archived=true`, { credentials: 'include' });
    if (r.ok) setPromos((await r.json()).promotions || []);
  }, []);

  useEffect(() => {
    refresh();
    fetch(`${API}/taxonomy/categories`).then((r) => r.ok && r.json()).then((d) => d && setCategories(d.categories || []));
    fetch(`${API}/lolodrive/lolo-points`).then((r) => r.ok && r.json()).then((d) => d && setRelays(d.points || []));
  }, [refresh]);

  const create = async () => {
    const r = await fetch(`${API}/admin/credit-promotions`, {
      method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...form,
        value_percent: parseFloat(form.value_percent),
        scope_product_type: form.scope_product_type.trim() || 'all',
        min_quantity: parseInt(form.min_quantity, 10) || 0,
        audience_emails: form.audience === 'emails'
          ? form.audience_emails.split(/[\n,;]+/).map((e) => e.trim()).filter(Boolean)
          : [],
        starts_at: form.starts_at ? `${form.starts_at}T00:00:00+00:00` : null,
        ends_at: form.ends_at ? `${form.ends_at}T23:59:59+00:00` : null,
        active: true,
      }),
    });
    const d = await r.json();
    if (r.ok) { toast.success('Promotion créée'); setForm(EMPTY); refresh(); }
    else toast.error(typeof d.detail === 'string' ? d.detail : 'Erreur');
  };

  const sendCampaign = async (id) => {
    if (!window.confirm('Envoyer cette promotion par email aux destinataires édités ?')) return;
    const r = await fetch(`${API}/admin/credit-promotions/${id}/send-campaign`, { method: 'POST', credentials: 'include' });
    const d = await r.json();
    if (r.ok) { toast.success(`Campagne envoyée à ${d.sent}/${d.total} destinataire(s)`); refresh(); }
    else toast.error(typeof d.detail === 'string' ? d.detail : 'Envoi impossible');
  };

  const act = async (id, method, path = '') => {
    const r = await fetch(`${API}/admin/credit-promotions/${id}${path}`, { method, credentials: 'include' });
    if (r.ok) { toast.success('OK'); refresh(); }
  };

  return (
    <div className="glass-panel-soft rounded-[18px] p-5" data-testid="credit-promotions-panel">
      <h3 className="font-display text-lg mb-3 text-white flex items-center gap-2">
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
          <option value="vendor">Vendeur Pro</option>
          <option value="buyer">Acheteur Pro</option>
          <option value="pass">Bénéficiaire PASS LOLODRIVE</option>
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
        <input value={form.scope_product_type} onChange={(e) => setForm({ ...form, scope_product_type: e.target.value })}
          placeholder="Type de produit (optionnel)" data-testid="promo-product-type" className={inputCls} />
        <input value={form.scope_brand} onChange={(e) => setForm({ ...form, scope_brand: e.target.value })}
          placeholder="Marque (optionnel)" data-testid="promo-brand" className={inputCls} />
        <input type="number" min="0" value={form.min_quantity} onChange={(e) => setForm({ ...form, min_quantity: e.target.value })}
          placeholder="Quantité min. (optionnel)" data-testid="promo-min-qty" className={inputCls} />
        <select value={form.scope_relay} onChange={(e) => setForm({ ...form, scope_relay: e.target.value })} data-testid="promo-relay" className={inputCls}>
          <option value="all">Tous relais LOLODRIVE</option>
          {relays.map((r) => <option key={r.id || r.name} value={r.name}>{r.name}</option>)}
        </select>
        <select value={form.audience} onChange={(e) => setForm({ ...form, audience: e.target.value })} data-testid="promo-audience" className={inputCls}>
          <option value="all">Destinée à tous</option>
          <option value="emails">Emails ciblés (campagne)</option>
        </select>
        <label className="flex items-center gap-2 text-xs text-white/70">
          <input type="checkbox" checked={form.countdown_enabled}
            onChange={(e) => setForm({ ...form, countdown_enabled: e.target.checked })} data-testid="promo-countdown-toggle" />
          Compte à rebours affiché
        </label>
      </div>
      {form.audience === 'emails' && (
        <textarea value={form.audience_emails} onChange={(e) => setForm({ ...form, audience_emails: e.target.value })}
          placeholder="Emails destinataires (un par ligne ou séparés par des virgules)"
          data-testid="promo-emails" rows={2}
          className="w-full mb-3 px-2 py-1.5 rounded-lg bg-white/[0.06] border border-white/15 text-sm text-white placeholder:text-white/35" />
      )}
      {form.countdown_enabled && (
        <div className="flex flex-wrap items-center gap-3 mb-3 text-xs text-white/70" data-testid="promo-countdown-pages">
          <span className="text-[10px] uppercase opacity-50">Bannière sur :</span>
          {COUNTDOWN_PAGES.map(([value, label]) => (
            <label key={value} className="flex items-center gap-1.5">
              <input type="checkbox" checked={form.countdown_pages.includes(value)}
                onChange={(e) => setForm({
                  ...form,
                  countdown_pages: e.target.checked
                    ? [...form.countdown_pages, value]
                    : form.countdown_pages.filter((p) => p !== value),
                })} data-testid={`promo-page-${value}`} />
              {label}
            </label>
          ))}
        </div>
      )}
      <button type="button" onClick={create} disabled={!form.name || !form.value_percent}
        data-testid="promo-create-btn"
        className="btn-gold h-9 px-4 rounded-lg text-sm font-semibold inline-flex items-center gap-1.5 disabled:opacity-40 mb-4">
        <Plus size={13} /> Créer la promotion
      </button>

      <div className="divide-y divide-white/[0.06]">
        {promos.map((p) => (
          <div key={p.id} className={`flex items-center justify-between gap-2 py-2 ${p.archived ? 'opacity-40' : ''}`} data-testid={`promo-row-${p.id}`}>
            <div className="min-w-0">
              <p className="text-sm font-medium text-white truncate">
                {p.name} — <span className="text-emerald-600 font-bold">{p.value_percent}%</span>
                {p.archived && <span className="text-[9px] uppercase ml-2 px-1.5 py-0.5 rounded bg-white/10 text-white/60">archivée</span>}
              </p>
              <p className="text-[11px] opacity-50">
                {p.promo_type === 'bonus_purchase' ? 'Bonus achat' : 'Réduction conso'} · {{ all: 'Tous profils', vendor: 'Vendeur Pro', buyer: 'Acheteur Pro', pass: 'PASS LOLODRIVE' }[p.scope_profile] || p.scope_profile} · {p.scope_territory} · {p.scope_category}
                {p.scope_product_type && p.scope_product_type !== 'all' && ` · type: ${p.scope_product_type}`}
                {p.scope_brand && ` · marque: ${p.scope_brand}`}
                {p.scope_relay && p.scope_relay !== 'all' && ` · relais: ${p.scope_relay}`}
                {p.min_quantity > 0 && ` · qté min: ${p.min_quantity}`}
                {p.audience === 'emails' && ` · 📧 ${(p.audience_emails || []).length} destinataire(s)${p.campaign_sent_at ? ` (envoyée ${p.campaign_sent_at.slice(0, 10)})` : ''}`}
                {p.countdown_enabled && ` · ⏱ countdown: ${(p.countdown_pages || []).join(', ')}`}
                {(p.starts_at || p.ends_at) && (
                  <span className="ml-1.5 px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-600 text-[10px]" data-testid={`promo-window-${p.id}`}>
                    ⏱ {p.starts_at ? p.starts_at.slice(0, 10) : '…'} → {p.ends_at ? p.ends_at.slice(0, 10) : '…'}
                  </span>
                )}
              </p>
            </div>
            <div className="flex gap-1 shrink-0">
              {!p.archived && p.audience === 'emails' && (p.audience_emails || []).length > 0 && (
                <button type="button" onClick={() => sendCampaign(p.id)} data-testid={`promo-send-${p.id}`}
                  title="Envoyer la campagne email" className="p-1.5 rounded-lg opacity-40 hover:opacity-100 hover:bg-blue-500/10 text-blue-400">
                  <Send size={13} />
                </button>
              )}
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
          <span className="truncate text-white">{r.key}</span>
          <span className="font-semibold text-[#E9CF8E]">{r.credits} cr.</span>
        </div>
      ))}
      {(!rows || rows.length === 0) && <p className="text-xs opacity-40">—</p>}
    </div>
  );

  if (!data) return null;
  return (
    <div className="glass-panel-soft rounded-[18px] p-5" data-testid="credit-analytics-panel">
      <h3 className="font-display text-lg mb-3 text-white flex items-center gap-2">
        <BarChart3 size={15} className="text-[#5B9BD5]" /> Suivi des crédits
      </h3>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-4 text-center">
        {[
          ['Achetés', data.totals.purchased, '#8CC63E'],
          ['Consommés', data.totals.consumed, '#E9CF8E'],
          ['Remboursés', data.totals.refunded, '#5B9BD5'],
          ['Revenus', `${data.totals.revenue_eur} €`, '#CDB4F0'],
        ].map(([label, value, color]) => (
          <div key={label} className="rounded-xl bg-white/[0.06] border border-white/10 p-2.5">
            <p className="text-lg font-bold" style={{ color }}>{value}</p>
            <p className="text-[10px] uppercase text-white/60">{label}</p>
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
