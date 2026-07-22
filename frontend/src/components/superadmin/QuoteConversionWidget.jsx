import { useEffect, useState } from 'react';
import { TrendingUp } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const QuoteConversionWidget = () => {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    fetch(`${API}/admin/quotes/stats`, { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null)).then(setStats).catch(() => {});
  }, []);

  if (!stats || !stats.total) return null;
  return (
    <div className="glass-panel-soft rounded-[18px] p-4" data-testid="quote-conversion-widget">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[#D9B35A]/15 border border-[#D9B35A]/30 flex items-center justify-center">
            <TrendingUp size={18} className="text-[#E9CF8E]" />
          </div>
          <div>
            <p className="text-xs text-white/50">Conversion des devis</p>
            <p className="text-xl font-bold text-white" data-testid="quote-conversion-rate">
              {stats.conversion_rate}%
              <span className="text-xs font-normal text-white/45"> · {stats.converted} converti(s) sur {stats.total} reçu(s)</span>
            </p>
          </div>
        </div>
        <div className="flex gap-2 flex-wrap text-[10px] font-bold">
          <span className="px-2 py-1 rounded-full" style={{ color: '#60A5FA', background: '#60A5FA1a' }}>{stats.pending} Nouveau</span>
          <span className="px-2 py-1 rounded-full" style={{ color: '#FBBF24', background: '#FBBF241a' }}>{stats.contacted} Contacté</span>
          <span className="px-2 py-1 rounded-full" style={{ color: '#7BC94E', background: '#7BC94E1a' }}>{stats.converted} Converti</span>
          <span className="px-2 py-1 rounded-full" style={{ color: '#F87171', background: '#F871711a' }}>{stats.lost} Perdu</span>
        </div>
      </div>
      <div className="mt-3 h-2 rounded-full bg-white/[0.06] overflow-hidden flex">
        <div style={{ width: `${(stats.converted / stats.total) * 100}%`, background: '#7BC94E' }} />
        <div style={{ width: `${(stats.contacted / stats.total) * 100}%`, background: '#FBBF24' }} />
        <div style={{ width: `${(stats.pending / stats.total) * 100}%`, background: '#60A5FA' }} />
        <div style={{ width: `${(stats.lost / stats.total) * 100}%`, background: '#F87171' }} />
      </div>
    </div>
  );
};
