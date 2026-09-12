import { useEffect, useState } from 'react';
import { CalendarClock, Loader2 } from 'lucide-react';
import { getAuthHeaders } from '../../services/http';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const fmtDate = (iso) => (iso ? new Date(iso).toLocaleDateString('fr-FR') : '—');

export const PromoExtensionLog = () => {
  const [items, setItems] = useState(null);

  useEffect(() => {
    fetch(`${API_URL}/api/promo/admin/extension-log`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => r.json())
      .then((d) => setItems(d.items || []))
      .catch(() => setItems([]));
  }, []);

  return (
    <div className="mt-8 rounded-xl border border-white/10 bg-white/[0.03] p-5" data-testid="promo-extension-log">
      <h3 className="flex items-center gap-2 text-sm font-bold text-white/90 mb-3">
        <CalendarClock className="w-4 h-4 text-[#D9B35A]" />
        Journal des prolongations de promo
      </h3>
      {items === null ? (
        <Loader2 className="w-5 h-5 animate-spin text-white/40" />
      ) : items.length === 0 ? (
        <p className="text-xs text-white/40">Aucune prolongation enregistrée pour le moment.</p>
      ) : (
        <table className="w-full text-xs">
          <thead>
            <tr className="text-left text-white/40 border-b border-white/10">
              <th className="py-2 pr-3">Date</th>
              <th className="py-2 pr-3">Produit</th>
              <th className="py-2 pr-3">Zones</th>
              <th className="py-2 pr-3">Ancienne fin</th>
              <th className="py-2 pr-3">Nouvelle fin</th>
              <th className="py-2">Source</th>
            </tr>
          </thead>
          <tbody>
            {items.map((it) => (
              <tr key={it.id} className="border-b border-white/5 text-white/75" data-testid={`promo-ext-row-${it.id}`}>
                <td className="py-2 pr-3">{fmtDate(it.extended_at)}</td>
                <td className="py-2 pr-3">{it.product_name}<span className="text-white/35"> · {it.sku}</span></td>
                <td className="py-2 pr-3">{it.zones_count}</td>
                <td className="py-2 pr-3">{fmtDate(it.old_end)}</td>
                <td className="py-2 pr-3 text-emerald-300 font-semibold">{fmtDate(it.new_end)}</td>
                <td className="py-2 text-white/50">{it.source === 'email_one_click' ? 'Email — un clic' : it.source}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};
