import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Scale } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export const MissingLogisticsCard = ({ vendorId }) => {
  const navigate = useNavigate();
  const [data, setData] = useState(null);

  useEffect(() => {
    if (!vendorId) return;
    fetch(`${API}/api/vendor/missing-logistics/${vendorId}`, { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null))
      .then(setData)
      .catch(() => {});
  }, [vendorId]);

  if (!data || data.count === 0) return null;

  return (
    <div className="rounded-[14px] border border-amber-300 bg-amber-50 p-4" data-testid="missing-logistics-card">
      <div className="flex items-center gap-2 mb-2">
        <Scale className="w-4 h-4 text-amber-600" />
        <p className="text-sm font-bold text-amber-800">
          {data.count} produit{data.count > 1 ? 's' : ''} sans poids ou volume
        </p>
      </div>
      <p className="text-xs text-amber-700 mb-3">
        Sans ces données, le coût logistique n'est pas calculable et la garantie CREDI'SCOP (45 %) du
        Règlement à Réception ne s'applique pas à vos produits.
      </p>
      <div className="space-y-1.5">
        {data.items.slice(0, 20).map((p) => (
          <div key={p.id} className="flex items-center justify-between gap-2 bg-white/70 rounded-lg px-2.5 py-1.5"
            data-testid={`missing-logistics-item-${p.id}`}>
            <div className="min-w-0">
              <p className="text-xs font-semibold text-gray-800 truncate">{p.name}</p>
              <p className="text-[10px] text-gray-500">
                {p.sku} — manque : {p.missing.join(' + ')}
              </p>
            </div>
            <button type="button"
              onClick={() => navigate(`/vendor?tab=products&edit=${p.id}`)}
              data-testid={`missing-logistics-fix-${p.id}`}
              className="shrink-0 text-[11px] font-bold text-amber-700 border border-amber-400 rounded-md px-2 py-1 hover:bg-amber-100">
              Compléter
            </button>
          </div>
        ))}
      </div>
      {data.count > 20 && (
        <p className="text-[11px] text-amber-700/70 mt-2">… et {data.count - 20} autre(s) produit(s).</p>
      )}
    </div>
  );
};
