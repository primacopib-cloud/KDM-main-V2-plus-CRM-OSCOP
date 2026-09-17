import { useEffect, useState } from 'react';
import { ScrollText } from 'lucide-react';
import { API, getAuthHeaders } from '../../../services/http';

const fmt = (iso) => (iso ? new Date(iso).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' }) : '—');

// Archive des conventions cadre POP'S signées (superadmin)
export const AdminConventionsCard = () => {
  const [items, setItems] = useState([]);
  useEffect(() => {
    fetch(`${API}/admin/detaillant/conventions`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => (r.ok ? r.json() : { conventions: [] }))
      .then((d) => setItems(d.conventions || [])).catch(() => {});
  }, []);
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4" data-testid="admin-conventions-card">
      <h3 className="text-sm font-bold text-[#E9CF8E] mb-3 flex items-center gap-2">
        <ScrollText className="w-4 h-4" /> Conventions cadre signées ({items.length})
      </h3>
      {items.length === 0 ? (
        <p className="text-xs text-white/40" data-testid="admin-conventions-empty">Aucune convention signée.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead><tr className="text-white/45 text-left">
              <th className="pr-2 pb-1">Boutique POP'S</th><th className="pr-2">Localité</th>
              <th className="pr-2">Signataire</th><th className="pr-2">Signée le</th><th>Version</th>
            </tr></thead>
            <tbody>
              {items.map((c) => (
                <tr key={c.user_id} className="border-t border-white/[0.06] text-white/70"
                  data-testid={`convention-row-${c.user_id}`}>
                  <td className="pr-2 py-1.5 font-bold text-white/85">{c.company_name}</td>
                  <td className="pr-2">{c.locality || '—'}{c.country_code ? ` (${c.country_code})` : ''}</td>
                  <td className="pr-2">{c.signer_name}</td>
                  <td className="pr-2">{fmt(c.signed_at)}</td>
                  <td>{c.version}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
