import { useEffect, useState } from 'react';
import { ChevronDown, ChevronUp, Flame, TrendingUp } from 'lucide-react';
import { lolodriveAPI } from '../../services/api';
import { PRODUCT_TAGS } from '../lolodrive/ProductTagBadge';

const fmt = (c) => `${(c / 100).toFixed(2)} €`;
const MEDALS = ['🥇', '🥈', '🥉'];

// Super admin : bilan des ventes par étiquette promo — pour piloter les prochaines campagnes
export const PromoStatsPanel = () => {
  const [open, setOpen] = useState(false);
  const [days, setDays] = useState(30);
  const [data, setData] = useState(null);

  useEffect(() => {
    if (open) lolodriveAPI.adminPromoStats(days).then(setData).catch(() => {});
  }, [open, days]);

  const label = (tag) => PRODUCT_TAGS.find((t) => t.value === tag)?.label || tag;
  return (
    <div className="mt-6 rounded-2xl bg-white/[0.025] border border-white/[0.07] p-5" data-testid="promo-stats-panel">
      <button type="button" onClick={() => setOpen(!open)} data-testid="promo-stats-toggle"
        className="w-full flex flex-wrap items-center justify-between gap-3 text-left">
        <div className="font-semibold flex items-center gap-2">
          <Flame className="w-4 h-4 text-red-400" /> Bilan des promos — quelles étiquettes font vendre ?
          <span className="text-xs text-white/40 font-normal">(ventes Drive + comptoir des produits étiquetés)</span>
        </div>
        {open ? <ChevronUp className="w-4 h-4 text-white/40" /> : <ChevronDown className="w-4 h-4 text-white/40" />}
      </button>
      {open && (
        <div className="mt-3">
          <div className="flex flex-wrap items-center gap-1.5 mb-3">
            {[7, 30, 90].map((d) => (
              <button key={d} type="button" onClick={() => setDays(d)} data-testid={`promo-stats-days-${d}`}
                className={`px-2.5 py-1 rounded-lg text-[10px] font-bold border ${days === d
                  ? 'text-black bg-[#D9B35A] border-[#D9B35A]'
                  : 'text-white/60 bg-white/[0.04] border-white/10 hover:border-white/25'}`}>
                {d} jours
              </button>
            ))}
            {data && (
              <span className="ml-2 text-[11px] text-white/45" data-testid="promo-stats-summary">
                <TrendingUp className="inline w-3 h-3 mr-1 text-emerald-300" />
                {data.total_qty} article(s) vendus sous étiquette · <b className="text-emerald-300">{fmt(data.total_revenue_cents)}</b> de CA
              </span>
            )}
          </div>
          {data && data.tags.length === 0 && (
            <p className="text-xs text-white/40 py-4 text-center" data-testid="promo-stats-empty">
              Aucune vente de produit étiqueté sur cette période — les ventes sont comptées à partir de la pose des étiquettes.
            </p>
          )}
          {data && data.tags.map((t, i) => (
            <div key={t.tag} className="mb-3 rounded-xl border border-white/[0.07] bg-white/[0.02] p-3" data-testid={`promo-stats-tag-${t.tag}`}>
              <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                <span className="text-sm font-bold text-red-300">{MEDALS[i] || '•'} {label(t.tag)}</span>
                <span className="text-[11px] text-white/50">
                  {t.qty} vendu(s) · {t.orders} commande(s) · <b className="text-emerald-300">{fmt(t.revenue_cents)}</b>
                </span>
              </div>
              <div className="space-y-1">
                {t.products.slice(0, 8).map((p) => (
                  <div key={p.sku} className="flex items-center justify-between text-[11px]" data-testid={`promo-stats-row-${t.tag}-${p.sku}`}>
                    <span className="truncate text-white/70">{p.name}</span>
                    <span className="flex items-center gap-3 shrink-0 ml-3 font-mono">
                      {p.accel != null ? (
                        <span data-testid={`promo-accel-${t.tag}-${p.sku}`} title={`${p.qty} vendus en promo vs ${p.base_qty} hors promo sur la période`}
                          className={`px-1.5 py-0.5 rounded text-[9px] font-bold border ${p.accel >= 1.5
                            ? 'text-emerald-300 bg-emerald-400/10 border-emerald-400/30'
                            : p.accel >= 0.8 ? 'text-white/50 bg-white/[0.04] border-white/15'
                              : 'text-amber-300 bg-amber-400/10 border-amber-400/30'}`}>
                          {p.accel >= 1.5 ? '🚀 ' : ''}×{p.accel} vs habitude
                        </span>
                      ) : (
                        <span data-testid={`promo-accel-${t.tag}-${p.sku}`}
                          className="px-1.5 py-0.5 rounded text-[9px] text-white/30 bg-white/[0.03] border border-white/10">
                          pas de vente hors promo
                        </span>
                      )}
                      <span className="text-white/40">×{p.qty}</span>
                      <span className="w-20 text-right text-emerald-300">{fmt(p.revenue_cents)}</span>
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
