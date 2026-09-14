import { useEffect, useState } from 'react';
import { Flame } from 'lucide-react';
import { lolodriveAPI } from '../../services/api';
import { SectionCard } from '../LolodriveLayout';

const DAYS = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'];

const cellStyle = (count, max) => {
  if (!count) return { background: 'rgba(255,255,255,0.03)', color: 'rgba(255,255,255,0.25)' };
  const t = max ? count / max : 0;
  return {
    background: `rgba(217,179,90,${0.12 + t * 0.65})`,
    color: t > 0.55 ? '#1a1206' : '#F3E9D2',
    fontWeight: 700,
  };
};

// Heatmap d'affluence : commandes servies par jour de semaine × créneau (3 mois)
export const AffluenceHeatmap = () => {
  const [data, setData] = useState(null);
  const [days, setDays] = useState(90);

  useEffect(() => {
    lolodriveAPI.managerAffluence(days).then(setData).catch(() => setData(null));
  }, [days]);

  if (!data) return null;
  const get = (wd, sid) => data.cells.find((c) => c.weekday === wd && c.slot_id === sid)?.count || 0;
  const peak = data.cells.reduce((a, c) => (c.count > (a?.count || 0) ? c : a), null);
  const peakLabel = peak && peak.count > 0
    ? `${DAYS[peak.weekday]} · ${data.slots.find((s) => s.id === peak.slot_id)?.label || peak.slot_id} (${peak.count} commandes)`
    : null;

  return (
    <SectionCard
      title={<span className="inline-flex items-center gap-2"><Flame className="w-4 h-4 text-[#D9B35A]" />Affluence — heures et jours de pointe</span>}
      data-testid="affluence-heatmap">
      <div className="flex items-center justify-between flex-wrap gap-2 mb-3" data-testid="affluence-header">
        <p className="text-[11px] text-white/50">
          {data.total} commande(s) servies depuis le {data.since} — relais {data.point.name}
        </p>
        <div className="flex gap-1">
          {[30, 90, 180].map((d) => (
            <button key={d} type="button" onClick={() => setDays(d)} data-testid={`affluence-range-${d}`}
              className={`px-2.5 h-7 rounded-full text-[11px] font-bold border transition-colors ${
                days === d ? 'bg-[#D9B35A]/25 border-[#D9B35A]/60 text-[#E9CF8E]' : 'bg-white/[0.04] border-white/10 text-white/50 hover:text-white'}`}>
              {d} j
            </button>
          ))}
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-center text-xs border-separate" style={{ borderSpacing: 3 }}>
          <thead>
            <tr>
              <th className="text-left text-[10px] text-white/45 font-bold px-2">Créneau</th>
              {DAYS.map((d) => <th key={d} className="text-[10px] text-white/45 font-bold px-2">{d}</th>)}
            </tr>
          </thead>
          <tbody>
            {data.slots.map((slot) => (
              <tr key={slot.id}>
                <td className="text-left text-[11px] text-white/60 font-semibold px-2 whitespace-nowrap">{slot.label}</td>
                {DAYS.map((_, wd) => {
                  const n = get(wd, slot.id);
                  return (
                    <td key={wd} data-testid={`affluence-cell-${wd}-${slot.id}`}
                      className="rounded-md py-2.5 px-2 text-xs" style={cellStyle(n, data.max)}>
                      {n || '·'}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {peakLabel && (
        <p className="text-[11px] text-white/55 mt-2" data-testid="affluence-peak">
          Créneau le plus chargé : <strong className="text-[#E9CF8E]">{peakLabel}</strong> — ajustez vos capacités en conséquence.
        </p>
      )}
    </SectionCard>
  );
};
