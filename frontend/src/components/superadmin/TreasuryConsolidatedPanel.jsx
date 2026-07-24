import { useEffect, useState } from 'react';
import { Landmark } from 'lucide-react';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { API, getAuthHeaders } from '../../services/http';

const eur = (c) => `${((c || 0) / 100).toFixed(2).replace('.', ',')} €`;

const TreasuryHistoryChart = ({ history }) => {
  const data = (history || []).map((m) => ({
    mois: m.month,
    'Cumul': +(m.cumulative_cents / 100).toFixed(2),
    'Transport': +(m.transport_cents / 100).toFixed(2),
    'Adhésions': +(m.memberships_cents / 100).toFixed(2),
    'RCR net': +(m.rcr_net_cents / 100).toFixed(2),
  }));
  if (!data.length) return null;
  return (
    <div className="mt-3" data-testid="treasury-history-chart">
      <p className="text-[10px] font-semibold text-white/50 mb-1">Évolution mensuelle de la trésorerie consolidée (€)</p>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
          <XAxis dataKey="mois" tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 10 }} />
          <YAxis tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 10 }} />
          <Tooltip contentStyle={{ background: '#2A1045', border: '1px solid rgba(217,179,90,0.4)', borderRadius: 10, fontSize: 11 }}
            labelStyle={{ color: '#E9CF8E' }} />
          <Line type="monotone" dataKey="Cumul" stroke="#D9B35A" strokeWidth={2.5} dot={{ r: 3 }} />
          <Line type="monotone" dataKey="Transport" stroke="#93C5FD" strokeWidth={1.5} dot={false} strokeDasharray="4 3" />
          <Line type="monotone" dataKey="Adhésions" stroke="#7BC94E" strokeWidth={1.5} dot={false} strokeDasharray="4 3" />
          <Line type="monotone" dataKey="RCR net" stroke="#F0ABFC" strokeWidth={1.5} dot={false} strokeDasharray="4 3" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export const TreasuryConsolidatedPanel = () => {
  const [data, setData] = useState(null);

  useEffect(() => {
    fetch(`${API}/admin/treasury/consolidated`, { credentials: 'include', headers: getAuthHeaders() })
      .then((r) => (r.ok ? r.json() : null)).then(setData).catch(() => {});
  }, []);

  if (!data) return null;
  const { transport, memberships, rcr, buckets } = data;
  return (
    <div className="glass-panel-soft rounded-[14px] p-3" data-testid="treasury-consolidated-panel">
      <p className="text-[11px] font-semibold text-[#D9B35A] mb-2 flex items-center gap-1.5">
        <Landmark className="w-3.5 h-3.5" /> Trésorerie consolidée — RCR · Transport LOGI'SCOP · Adhésions
      </p>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 mb-3">
        {[
          { label: 'RCR détenue (FOGEDOM)', v: eur(rcr.held_cents), c: '#E9CF8E' },
          { label: `Encours transport (${transport.unpaid_count} fact.)`, v: eur(transport.outstanding_cents), c: '#93C5FD' },
          { label: `dont échu (+30 j)`, v: eur(transport.overdue_cents), c: '#F87171' },
          { label: `Adhésions / mois (${memberships.active_count} actifs)`, v: eur(memberships.mrr_cents), c: '#7BC94E' },
        ].map((k) => (
          <div key={k.label} className="rounded-lg p-2 bg-white/[0.04] border border-white/[0.08]">
            <p className="text-[10px] text-white/50">{k.label}</p>
            <p className="text-sm font-bold" style={{ color: k.c }}>{k.v}</p>
          </div>
        ))}
      </div>
      <table className="w-full text-[11px]" data-testid="treasury-projection-table">
        <thead><tr className="text-white/45 text-left">
          <th className="pb-1.5">Projection</th>
          <th className="text-right pb-1.5">Encaissements transport</th>
          <th className="text-right pb-1.5">Adhésions attendues</th>
          <th className="text-right pb-1.5">Sorties RCR prévues</th>
          <th className="text-right pb-1.5">Net période</th>
          <th className="text-right pb-1.5">Net cumulé</th>
        </tr></thead>
        <tbody>
          {buckets.map((b) => (
            <tr key={b.label} className="border-t border-white/5 text-white/75">
              <td className="py-1.5 font-semibold">{b.label}</td>
              <td className="text-right text-[#93C5FD]">{eur(b.transport_in_cents)}</td>
              <td className="text-right text-[#7BC94E]">{eur(b.memberships_in_cents)}</td>
              <td className="text-right text-[#F0ABFC]">-{eur(b.rcr_out_cents)}</td>
              <td className={`text-right font-semibold ${b.net_cents < 0 ? 'text-red-400' : ''}`}>{eur(b.net_cents)}</td>
              <td className={`text-right font-bold ${b.cumulative_cents < 0 ? 'text-red-400' : 'text-[#E9CF8E]'}`}>{eur(b.cumulative_cents)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="text-[9px] text-white/35 mt-1.5">
        Encaissements transport nets d'avoirs (échéance = émission + 30 j, l'échu est attendu sous 30 j) ·
        adhésions = renouvellements mensuels des membres actifs · sorties RCR = remboursements à expiration + délai réglementaire.
      </p>
      <TreasuryHistoryChart history={data.history} />
    </div>
  );
};
