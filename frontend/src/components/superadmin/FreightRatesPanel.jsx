import { useCallback, useEffect, useState } from 'react';
import { Ship } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';
import { Input } from '../ui/input';

export const FreightRatesPanel = () => {
  const [routes, setRoutes] = useState(null);

  const load = useCallback(async () => {
    const res = await fetch(`${API}/public/freight/routes`);
    if (res.ok) setRoutes((await res.json()).routes);
  }, []);
  useEffect(() => { load(); }, [load]);

  const save = async (route, field, value, container) => {
    const body = {};
    if (container) body.base_prices = { ...route.base_prices, [container]: parseFloat(value) || route.base_prices[container] };
    else if (field === 'baf_rate') body.baf_rate = parseFloat(value) || route.baf_rate;
    else if (field === 'transit_days') body.transit_days = parseInt(value, 10) || route.transit_days;
    const res = await fetch(`${API}/admin/freight/routes/${route.id}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify(body),
    });
    if (res.ok) { toast.success('Barème mis à jour'); load(); } else toast.error('Échec');
  };

  if (!routes) return null;

  return (
    <div className="glass-panel-soft rounded-[18px] p-4 mt-6" data-testid="freight-rates-panel">
      <h3 className="text-lg font-bold text-white flex items-center gap-2 mb-3">
        <Ship className="w-5 h-5 text-[#D9B35A]" /> Barème fret maritime LOGI'SCOP
      </h3>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-white/50 text-left">
              <th className="py-1.5 pr-2">Route</th>
              {['20DV', '40DV', '40HC', 'LCL'].map((c) => <th key={c} className="py-1.5 pr-2">{c} (€)</th>)}
              <th className="py-1.5 pr-2">BAF %</th>
              <th className="py-1.5">Transit (j)</th>
            </tr>
          </thead>
          <tbody>
            {routes.map((r) => (
              <tr key={r.id} className="border-t border-white/10">
                <td className="py-1.5 pr-2 text-white/80">{r.origin} → {r.destination}</td>
                {['20DV', '40DV', '40HC', 'LCL'].map((c) => (
                  <td key={c} className="py-1.5 pr-2">
                    <Input defaultValue={r.base_prices[c]} data-testid={`rate-${r.id}-${c}`}
                      onBlur={(e) => e.target.value !== String(r.base_prices[c]) && save(r, null, e.target.value, c)}
                      className="w-20 h-7 text-xs bg-white/5 border-white/15 text-white" />
                  </td>
                ))}
                <td className="py-1.5 pr-2">
                  <Input defaultValue={r.baf_rate} data-testid={`rate-${r.id}-baf`}
                    onBlur={(e) => e.target.value !== String(r.baf_rate) && save(r, 'baf_rate', e.target.value)}
                    className="w-16 h-7 text-xs bg-white/5 border-white/15 text-white" />
                </td>
                <td className="py-1.5">
                  <Input defaultValue={r.transit_days} data-testid={`rate-${r.id}-transit`}
                    onBlur={(e) => e.target.value !== String(r.transit_days) && save(r, 'transit_days', e.target.value)}
                    className="w-16 h-7 text-xs bg-white/5 border-white/15 text-white" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
