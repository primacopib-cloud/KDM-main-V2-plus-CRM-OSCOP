import { useEffect, useState } from 'react';
import { Coins, Image as ImageIcon, Type } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const AIUsagePanel = () => {
  const [data, setData] = useState(null);

  useEffect(() => {
    fetch(`${API}/admin/ai-usage`, { credentials: 'include' })
      .then((r) => r.json()).then(setData).catch(() => {});
  }, []);

  if (!data || !data.current?.items?.length) return null;
  const { current, previous } = data;

  return (
    <div className="glass-panel-soft rounded-[18px] p-5" data-testid="ai-usage-panel">
      <div className="flex items-center gap-3 flex-wrap mb-3">
        <h3 className="font-display text-base text-white flex items-center gap-2">
          <Coins size={15} style={{ color: '#D9B35A' }} /> Consommation IA — {current.month}
        </h3>
        <span className="px-2 py-0.5 rounded bg-[#D9B35A]/15 text-[#E9CF8E] text-xs font-bold" data-testid="ai-usage-total">
          ≈ {current.total_cost_eur.toFixed(2)} € · {current.total_count} génération(s)
        </span>
        {previous.total_count > 0 && (
          <span className="text-[10px] text-white/40">mois précédent : ≈ {previous.total_cost_eur.toFixed(2)} € ({previous.total_count})</span>
        )}
      </div>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-2">
        {current.items.map((i) => (
          <div key={i.kind} className="p-2.5 rounded-xl bg-white/[0.04] border border-white/10 flex items-center gap-2.5" data-testid={`ai-usage-${i.kind}`}>
            {i.is_image ? <ImageIcon size={14} className="text-purple-300 flex-shrink-0" /> : <Type size={14} className="text-blue-300 flex-shrink-0" />}
            <div className="min-w-0">
              <p className="text-xs text-white truncate">{i.label}</p>
              <p className="text-[10px] text-white/45">{i.count} génération(s) · ≈ {i.cost_eur.toFixed(2)} €</p>
            </div>
          </div>
        ))}
      </div>
      <p className="mt-2 text-[10px] text-white/30">Estimation indicative basée sur des coûts unitaires moyens (image ≈ 0,04 €, texte ≈ 0,01 €). Le solde exact est visible sur votre Universal Key Emergent.</p>
    </div>
  );
};
