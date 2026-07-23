import { useEffect, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { PiggyBank } from 'lucide-react';
import { API, getAuthHeaders } from '../../services/http';

const eur = (c) => ((c || 0) / 100).toLocaleString('fr-FR', { minimumFractionDigits: 2 }) + ' €';
const MONTH_LABELS = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin', 'Juil', 'Août', 'Sep', 'Oct', 'Nov', 'Déc'];

export const RcrStatsWidget = () => {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    fetch(`${API}/convention/admin/rcr-stats?months=6`, { credentials: 'include', headers: getAuthHeaders() })
      .then((r) => (r.ok ? r.json() : null)).then(setStats).catch(() => {});
  }, []);

  if (!stats) return null;

  const data = stats.months.map((m) => ({
    name: `${MONTH_LABELS[parseInt(m.month.slice(5), 10) - 1]} ${m.month.slice(2, 4)}`,
    Constitué: m.constitue_cents / 100,
    Remboursé: m.rembourse_cents / 100,
  }));

  return (
    <div className="rounded-xl p-4 mb-8" style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(217,179,90,0.25)' }}
      data-testid="rcr-stats-widget">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
        <p className="flex items-center gap-2 text-sm font-semibold text-white/85">
          <PiggyBank className="w-4 h-4 text-[#D9B35A]" /> RCR FOGEDOM — évolution mensuelle
        </p>
        <span className="text-[11px] text-white/50">
          6 mois : constitué <b className="text-[#E9CF8E]">{eur(stats.total_constitue_cents)}</b> · remboursé <b className="text-[#93C5FD]">{eur(stats.total_rembourse_cents)}</b>
        </span>
      </div>
      <div style={{ width: '100%', height: 190 }}>
        <ResponsiveContainer>
          <BarChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
            <XAxis dataKey="name" stroke="rgba(255,255,255,0.35)" fontSize={11} tickLine={false} axisLine={false} />
            <YAxis stroke="rgba(255,255,255,0.35)" fontSize={10} tickLine={false} axisLine={false}
              tickFormatter={(v) => `${v} €`} width={56} />
            <Tooltip
              formatter={(v, name) => [`${Number(v).toLocaleString('fr-FR', { minimumFractionDigits: 2 })} €`, name]}
              contentStyle={{ background: '#141824', border: '1px solid rgba(217,179,90,0.35)', borderRadius: 8, fontSize: 12 }}
              labelStyle={{ color: 'rgba(255,255,255,0.7)' }} cursor={{ fill: 'rgba(255,255,255,0.04)' }} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Bar dataKey="Constitué" fill="#D9B35A" radius={[3, 3, 0, 0]} maxBarSize={26} />
            <Bar dataKey="Remboursé" fill="#60A5FA" radius={[3, 3, 0, 0]} maxBarSize={26} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
