import { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import i18n from '@/i18n';

export const SALE_MODEL_INFO = {
  OSCOP_DIRECT_RESALE: {
    badgeKey: 'sold_by_oscop',
    cls: 'bg-amber-500/15 text-amber-300 border-amber-400/40',
    logo: '/logos/oscop.webp',
    logoAlt: "O'SCOP — Objectif SCOP Outremer",
    noteKey: 'note_oscop',
    roles: [
      ['role_vendor', "O'SCOP"], ['role_billing', "O'SCOP"], ['role_cash', "O'SCOP"],
      ['role_sav', "O'SCOP"], ['role_coop', "O'SCOP"],
    ],
  },
  PARTNER_DIRECT_SALE: {
    badgeKey: 'sold_by_partner',
    cls: 'bg-sky-500/15 text-sky-300 border-sky-400/40',
    logo: '/logos/kdmarche-pro-gold.webp',
    logoAlt: 'KDMARCHÉ Pro',
    noteKey: 'note_partner',
    roles: [
      ['role_vendor', 'partner'], ['role_billing', 'partner'], ['role_cash', 'partner'],
      ['role_sav', 'partner'], ['role_coop', "O'SCOP"],
    ],
  },
};

export const SaleModelBadge = ({ product }) => {
  const [open, setOpen] = useState(false);
  const sm = product?.sale_model || 'PARTNER_DIRECT_SALE';
  const info = SALE_MODEL_INFO[sm] || SALE_MODEL_INFO.PARTNER_DIRECT_SALE;
  const sellerName = sm === 'PARTNER_DIRECT_SALE' && product?.seller_name ? product.seller_name : null;
  const partnerLabel = i18n.t('catalog.the_partner');
  return (
    <div className="mb-2">
      <button
        type="button"
        onClick={(e) => { e.stopPropagation(); setOpen(!open); }}
        data-testid={`sale-model-badge-${product?.sku || product?.id}`}
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded border text-[9px] font-semibold tracking-wide ${info.cls}`}
      >
        <span className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-white overflow-hidden shrink-0">
          <img src={info.logo} alt={info.logoAlt} className="no-logo-chip w-3 h-3 object-contain"
            data-testid={`sale-model-logo-${product?.sku || product?.id}`} />
        </span>
        {sellerName ? i18n.t('catalog.sold_by_name', { name: sellerName.toUpperCase() }) : i18n.t(`catalog.${info.badgeKey}`)}
        <ChevronDown className={`w-2.5 h-2.5 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div
          data-testid={`sale-model-roles-${product?.sku || product?.id}`}
          className="mt-1.5 p-2 rounded-lg bg-black/40 border border-white/10 text-[10px] space-y-1"
          onClick={(e) => e.stopPropagation()}
        >
          <p className="font-semibold text-white/80 uppercase tracking-wide text-[9px]">{i18n.t('catalog.roles_split')}</p>
          {info.roles.map(([k, v]) => (
            <div key={k} className="flex justify-between gap-2">
              <span className="text-white/50">{i18n.t(`catalog.${k}`)}</span>
              <span className="text-white/85 text-right">{v === 'partner' ? (sellerName || partnerLabel) : v}</span>
            </div>
          ))}
          <p className="text-white/45 pt-1 border-t border-white/10">{i18n.t(`catalog.${info.noteKey}`)}</p>
        </div>
      )}
    </div>
  );
};
