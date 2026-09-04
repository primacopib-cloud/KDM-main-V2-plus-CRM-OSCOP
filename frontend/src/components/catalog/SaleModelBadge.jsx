import { useState } from 'react';
import { ChevronDown, Scale } from 'lucide-react';

export const SALE_MODEL_INFO = {
  OSCOP_DIRECT_RESALE: {
    badge: "VENDU ET FACTURÉ PAR O'SCOP",
    cls: 'bg-amber-500/15 text-amber-300 border-amber-400/40',
    roles: [
      ['Vendeur', "O'SCOP"],
      ['Facturation', "O'SCOP"],
      ['Encaissement', "O'SCOP"],
      ['SAV / garanties', "O'SCOP"],
      ['Services coopératifs', "O'SCOP"],
    ],
    note: "O'SCOP achète, revend, facture et encaisse. O'SCOP assume la responsabilité de vendeur.",
  },
  PARTNER_DIRECT_SALE: {
    badge: 'VENDU ET FACTURÉ PAR LE PARTENAIRE',
    cls: 'bg-sky-500/15 text-sky-300 border-sky-400/40',
    roles: [
      ['Vendeur', 'Le partenaire vendeur'],
      ['Facturation', 'Le partenaire vendeur'],
      ['Encaissement', 'Le partenaire vendeur'],
      ['SAV / garanties', 'Le partenaire vendeur'],
      ['Services coopératifs', "O'SCOP"],
    ],
    note: "Le partenaire vend, facture et encaisse. O'SCOP assure uniquement les services coopératifs prévus.",
  },
};

export const SaleModelBadge = ({ product }) => {
  const [open, setOpen] = useState(false);
  const sm = product?.sale_model || 'PARTNER_DIRECT_SALE';
  const info = SALE_MODEL_INFO[sm] || SALE_MODEL_INFO.PARTNER_DIRECT_SALE;
  const sellerName = sm === 'PARTNER_DIRECT_SALE' && product?.seller_name ? product.seller_name : null;
  return (
    <div className="mb-2">
      <button
        type="button"
        onClick={(e) => { e.stopPropagation(); setOpen(!open); }}
        data-testid={`sale-model-badge-${product?.sku || product?.id}`}
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded border text-[9px] font-semibold tracking-wide ${info.cls}`}
      >
        <Scale className="w-2.5 h-2.5" />
        {sellerName ? `VENDU ET FACTURÉ PAR ${sellerName.toUpperCase()}` : info.badge}
        <ChevronDown className={`w-2.5 h-2.5 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div
          data-testid={`sale-model-roles-${product?.sku || product?.id}`}
          className="mt-1.5 p-2 rounded-lg bg-black/40 border border-white/10 text-[10px] space-y-1"
          onClick={(e) => e.stopPropagation()}
        >
          <p className="font-semibold text-white/80 uppercase tracking-wide text-[9px]">Répartition des rôles</p>
          {info.roles.map(([k, v]) => (
            <div key={k} className="flex justify-between gap-2">
              <span className="text-white/50">{k}</span>
              <span className="text-white/85 text-right">{sellerName && v === 'Le partenaire vendeur' ? sellerName : v}</span>
            </div>
          ))}
          <p className="text-white/45 pt-1 border-t border-white/10">{info.note}</p>
        </div>
      )}
    </div>
  );
};
