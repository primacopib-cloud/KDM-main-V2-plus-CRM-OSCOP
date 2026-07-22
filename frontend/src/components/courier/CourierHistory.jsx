import { useEffect, useState } from 'react';
import { History, PenLine, ImageIcon } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const eur = (c) => `${((c || 0) / 100).toFixed(2)} €`;

export const CourierHistory = ({ token }) => {
  const [data, setData] = useState(null);

  useEffect(() => {
    fetch(`${API}/courier/history?token=${encodeURIComponent(token)}`)
      .then((r) => (r.ok ? r.json() : null)).then(setData).catch(() => {});
  }, [token]);

  if (!data) return null;
  return (
    <div className="rounded-2xl p-4 bg-white/[0.04] border border-white/10 mb-4 space-y-2" data-testid="courier-history">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold flex items-center gap-2">
          <History size={14} className="text-[#D9B35A]" /> Mes tournées passées
        </p>
        <span className="text-xs font-bold text-[#E9CF8E]" data-testid="courier-history-total">
          {data.count} livraison(s) · {eur(data.total_collected_cents)}
        </span>
      </div>
      {data.items.length === 0 ? (
        <p className="text-xs text-white/45" data-testid="courier-history-empty">Aucun encaissement enregistré à votre nom pour le moment.</p>
      ) : (
        <div className="space-y-1.5 max-h-64 overflow-y-auto">
          {data.items.map((o) => (
            <div key={o.id} className="flex items-center gap-2 text-xs py-1.5 border-b border-white/5 last:border-0" data-testid={`courier-history-${o.id}`}>
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-white/85 truncate">{o.order_number}</p>
                <p className="text-white/40">
                  {o.paid_at ? new Date(o.paid_at).toLocaleString('fr-FR') : ''}
                  {o.cod_signer_name ? ` · signé par ${o.cod_signer_name}` : ''}
                </p>
              </div>
              <span className="font-bold text-[#E9CF8E]">{eur(o.amount_paid_cents)}</span>
              {o.cod_signature_url && (
                <a href={`${API.replace('/api', '')}${o.cod_signature_url}`} target="_blank" rel="noreferrer"
                  className="p-1.5 rounded-lg bg-white/[0.06] border border-white/10 text-white/60 hover:text-white" title="Signature">
                  <PenLine size={12} />
                </a>
              )}
              {o.cod_photo_url && (
                <a href={`${API.replace('/api', '')}${o.cod_photo_url}`} target="_blank" rel="noreferrer"
                  className="p-1.5 rounded-lg bg-white/[0.06] border border-white/10 text-white/60 hover:text-white" title="Photo du colis">
                  <ImageIcon size={12} />
                </a>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
