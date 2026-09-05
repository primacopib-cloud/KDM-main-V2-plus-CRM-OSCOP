import { useCallback, useEffect, useState } from 'react';
import { Plane } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';
import { Input } from '../ui/input';

const TIERS = [['lt45', '< 45 kg'], ['kg45', '45–100'], ['kg100', '100–300'], ['kg300', '300+']];

export const AirRatesPanel = () => {
  const [routes, setRoutes] = useState(null);

  const load = useCallback(async () => {
    const res = await fetch(`${API}/public/freight/air/routes`);
    if (res.ok) setRoutes((await res.json()).routes);
  }, []);
  useEffect(() => { load(); }, [load]);

  const save = async (route, body) => {
    const res = await fetch(`${API}/admin/freight/air-rates/${route.id}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify(body),
    });
    if (res.ok) { toast.success('Barème aérien mis à jour'); load(); } else toast.error('Échec');
  };

  if (!routes) return null;

  const cell = (r, val, onSave, testid) => (
    <td className="py-1.5 pr-2">
      <Input defaultValue={val} data-testid={testid}
        onBlur={(e) => e.target.value !== String(val) && onSave(parseFloat(String(e.target.value).replace(',', '.')))}
        className="w-16 h-7 text-xs bg-white/5 border-white/15 text-white" />
    </td>
  );

  return (
    <div className="glass-panel-soft rounded-[18px] p-4 mt-6" data-testid="air-rates-panel">
      <h3 className="text-lg font-bold text-white flex items-center gap-2 mb-3">
        <Plane className="w-5 h-5 text-[#D9B35A]" /> Barème fret aérien LOGI'SCOP (€/kg par palier)
      </h3>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-white/50 text-left">
              <th className="py-1.5 pr-2">Route</th>
              {TIERS.map(([, l]) => <th key={l} className="py-1.5 pr-2">{l}</th>)}
              <th className="py-1.5 pr-2">Min (€)</th>
              <th className="py-1.5 pr-2">Fuel %</th>
              <th className="py-1.5 pr-2">Sûreté €/kg</th>
              <th className="py-1.5">Transit (j)</th>
            </tr>
          </thead>
          <tbody>
            {routes.map((r) => (
              <tr key={r.id} className="border-t border-white/10">
                <td className="py-1.5 pr-2 text-white/80">{r.origin} ✈ {r.destination}</td>
                {TIERS.map(([k]) => cell(r, r.per_kg[k],
                  (v) => save(r, { per_kg: { ...r.per_kg, [k]: v || r.per_kg[k] } }), `air-rate-${r.id}-${k}`))}
                {cell(r, r.min_charge, (v) => save(r, { min_charge: v || r.min_charge }), `air-rate-${r.id}-min`)}
                {cell(r, r.fuel_rate, (v) => save(r, { fuel_rate: v || r.fuel_rate }), `air-rate-${r.id}-fuel`)}
                {cell(r, r.security_per_kg, (v) => save(r, { security_per_kg: v || r.security_per_kg }), `air-rate-${r.id}-sec`)}
                {cell(r, r.transit_days, (v) => save(r, { transit_days: Math.round(v) || r.transit_days }), `air-rate-${r.id}-transit`)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
