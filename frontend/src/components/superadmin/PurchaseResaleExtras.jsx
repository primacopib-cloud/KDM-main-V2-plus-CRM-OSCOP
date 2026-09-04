import { useCallback, useEffect, useState } from 'react';
import { BarChart3, ScrollText, BellRing, Download } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';
import { Button } from '../ui/button';
import { Input } from '../ui/input';

const eur = (v) => `${Number(v || 0).toLocaleString('fr-FR')} €`;

export const MarginsChart = () => {
  const [ops, setOps] = useState([]);
  useEffect(() => {
    fetch(`${API}/admin/purchase-resale/operations`, { headers: getAuthHeaders() })
      .then((r) => r.json()).then((d) => setOps(d.operations || [])).catch(() => {});
  }, []);
  if (ops.length === 0) return null;
  const shown = ops.slice(0, 12);
  const max = Math.max(...shown.map((o) => Math.max(o.expected_margin_ex_vat || 0, o.realized_margin_ex_vat || 0, 1)));
  const byTerritory = {};
  ops.forEach((o) => {
    const t = o.territory_id || 'Non renseigné';
    byTerritory[t] = byTerritory[t] || { expected: 0, realized: 0, count: 0 };
    byTerritory[t].expected += o.expected_margin_ex_vat || 0;
    byTerritory[t].realized += o.realized_margin_ex_vat || 0;
    byTerritory[t].count += 1;
  });
  const territories = Object.entries(byTerritory).sort((a, b) => b[1].expected - a[1].expected);
  const tMax = Math.max(...territories.map(([, v]) => Math.max(v.expected, v.realized, 1)));
  return (
    <div className="glass-panel-soft rounded-[18px] p-4 mt-5" data-testid="margins-chart">
      <h3 className="text-lg font-bold text-white flex items-center gap-2 mb-1">
        <BarChart3 className="w-5 h-5 text-[#D9B35A]" /> Marges prévisionnelles vs réalisées
      </h3>
      <div className="flex gap-3 text-[10px] text-white/55 mb-3">
        <span><span className="inline-block w-2.5 h-2.5 rounded-sm bg-[#D9B35A] mr-1"></span>Prévisionnelle</span>
        <span><span className="inline-block w-2.5 h-2.5 rounded-sm bg-emerald-400 mr-1"></span>Réalisée</span>
      </div>
      <div className="space-y-2">
        {shown.map((o) => (
          <div key={o.id} data-testid={`margin-row-${o.reference}`}>
            <div className="flex justify-between text-[10px] text-white/60 mb-0.5">
              <span>{o.reference} · {o.client_name}</span>
              <span>{eur(o.expected_margin_ex_vat)} / {o.realized_margin_ex_vat != null ? eur(o.realized_margin_ex_vat) : '—'}</span>
            </div>
            <div className="h-2 bg-white/5 rounded overflow-hidden mb-0.5">
              <div className="h-full bg-[#D9B35A]" style={{ width: `${Math.max((o.expected_margin_ex_vat || 0) / max * 100, 0)}%` }}></div>
            </div>
            <div className="h-2 bg-white/5 rounded overflow-hidden">
              <div className="h-full bg-emerald-400" style={{ width: `${Math.max((o.realized_margin_ex_vat || 0) / max * 100, 0)}%` }}></div>
            </div>
          </div>
        ))}
      </div>
      <div className="flex items-center justify-between flex-wrap gap-2 mt-4 mb-2">
        <p className="text-xs font-semibold text-white/70 uppercase">Marges par territoire</p>
        <Button size="sm" data-testid="territory-margins-csv"
          className="h-6 text-[10px] bg-white/10 hover:bg-white/20 text-white"
          onClick={async () => {
            const r = await fetch(`${API}/admin/purchase-resale/margins-by-territory?format=csv`, { headers: getAuthHeaders() });
            const blob = await r.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url; a.download = 'marges-par-territoire.csv'; a.click();
            URL.revokeObjectURL(url);
          }}>
          <Download className="w-3 h-3 mr-1" /> Export CSV
        </Button>
      </div>
      <div className="space-y-2" data-testid="margins-by-territory">
        {territories.map(([t, v]) => (
          <div key={t} data-testid={`territory-margin-${t}`}>
            <div className="flex justify-between text-[10px] text-white/60 mb-0.5">
              <span>{t} ({v.count} op.)</span>
              <span>{eur(v.expected)} / {eur(v.realized)}</span>
            </div>
            <div className="h-2 bg-white/5 rounded overflow-hidden mb-0.5">
              <div className="h-full bg-[#D9B35A]" style={{ width: `${Math.max(v.expected / tMax * 100, 0)}%` }}></div>
            </div>
            <div className="h-2 bg-white/5 rounded overflow-hidden">
              <div className="h-full bg-emerald-400" style={{ width: `${Math.max(v.realized / tMax * 100, 0)}%` }}></div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export const DisputedOrdersPanel = () => {
  const [orders, setOrders] = useState(null);
  const load = useCallback(async () => {
    const res = await fetch(`${API}/oscop-checkout/disputed-orders`, { headers: getAuthHeaders() });
    if (res.ok) setOrders((await res.json()).orders);
  }, []);
  useEffect(() => { load(); }, [load]);

  const act = async (id, action) => {
    const res = await fetch(`${API}/oscop-checkout/orders/${id}/dispute-action`, {
      method: 'POST', headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify({ action }),
    });
    const json = await res.json();
    if (!res.ok) { toast.error(typeof json.detail === 'string' ? json.detail : 'Erreur'); return; }
    toast.success(action === 'remind' ? 'Relance manuelle envoyée — commande réactivée' : 'Commande annulée, client informé');
    load();
  };

  if (!orders || orders.length === 0) return null;
  return (
    <div className="glass-panel-soft rounded-[18px] p-4 mt-5" data-testid="disputed-orders-panel">
      <h3 className="text-lg font-bold text-white flex items-center gap-2 mb-2">
        <BellRing className="w-5 h-5 text-red-300" /> Commandes en litige ({orders.length})
      </h3>
      {orders.map((o) => (
        <div key={o.id} className="flex items-center justify-between gap-2 bg-red-500/10 border border-red-400/20 rounded px-2.5 py-2 mb-1 text-xs flex-wrap" data-testid={`disputed-${o.order_number}`}>
          <span className="text-white/85">{o.order_number} · {o.customer_name} ({o.customer_email}) · {eur((o.total_ttc_cents || 0) / 100)} TTC</span>
          <div className="flex gap-1.5">
            <Button size="sm" data-testid={`dispute-remind-${o.order_number}`}
              className="h-6 text-[10px] bg-white/10 hover:bg-white/20 text-white"
              onClick={() => act(o.id, 'remind')}>Relancer</Button>
            <Button size="sm" data-testid={`dispute-cancel-${o.order_number}`}
              className="h-6 text-[10px] bg-red-600/40 hover:bg-red-600/60 text-white"
              onClick={() => act(o.id, 'cancel')}>Annuler</Button>
          </div>
        </div>
      ))}
    </div>
  );
};

export const ReminderSettings = () => {
  const [s, setS] = useState(null);
  useEffect(() => {
    fetch(`${API}/oscop-checkout/reminder-settings`, { headers: getAuthHeaders() })
      .then((r) => r.json()).then(setS).catch(() => {});
  }, []);
  if (!s) return null;
  const save = async (updates) => {
    const body = { delay_hours: parseFloat(updates.delay_hours ?? s.delay_hours) || 48, enabled: updates.enabled ?? s.enabled };
    const res = await fetch(`${API}/oscop-checkout/reminder-settings`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json', ...getAuthHeaders() }, body: JSON.stringify(body),
    });
    if (res.ok) { setS(body); toast.success('Relance paiement mise à jour'); }
  };
  return (
    <div className="glass-panel-soft rounded-[18px] p-4 mt-5 flex items-center gap-3 flex-wrap" data-testid="reminder-settings">
      <BellRing className="w-5 h-5 text-[#D9B35A]" />
      <span className="text-sm font-semibold text-white">Relance automatique des factures O'SCOP impayées après</span>
      <Input defaultValue={s.delay_hours} data-testid="reminder-delay-input"
        onBlur={(e) => e.target.value !== String(s.delay_hours) && save({ delay_hours: e.target.value })}
        className="w-20 h-8 text-xs bg-white/5 border-white/15 text-white text-center" />
      <span className="text-sm text-white/60">heures</span>
      <label className="flex items-center gap-1.5 text-xs text-white/70 cursor-pointer ml-2">
        <input type="checkbox" checked={s.enabled} data-testid="reminder-enabled-check"
          onChange={(e) => save({ enabled: e.target.checked })} />
        Activée
      </label>
    </div>
  );
};

export const AuditRegisterPanel = () => {
  const [data, setData] = useState(null);
  const [action, setAction] = useState('');
  const [operation, setOperation] = useState('');

  const load = useCallback(async () => {
    const params = new URLSearchParams();
    if (action) params.set('action', action);
    if (operation) params.set('operation', operation);
    const res = await fetch(`${API}/admin/purchase-resale/audit-register?${params}`, { headers: getAuthHeaders() });
    if (res.ok) setData(await res.json());
  }, [action, operation]);
  useEffect(() => { load(); }, [load]);

  const exportCsv = async () => {
    const params = new URLSearchParams({ format: 'csv' });
    if (action) params.set('action', action);
    if (operation) params.set('operation', operation);
    const r = await fetch(`${API}/admin/purchase-resale/audit-register?${params}`, { headers: getAuthHeaders() });
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'journal-audit-achat-revente.csv'; a.click();
    URL.revokeObjectURL(url);
  };

  if (!data) return null;
  return (
    <div className="glass-panel-soft rounded-[18px] p-4 mt-5" data-testid="audit-register-panel">
      <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
        <h3 className="text-lg font-bold text-white flex items-center gap-2">
          <ScrollText className="w-5 h-5 text-[#D9B35A]" /> Journal d'audit achat-revente ({data.count})
        </h3>
        <div className="flex gap-1.5 flex-wrap">
          <select value={action} onChange={(e) => setAction(e.target.value)} data-testid="audit-action-filter"
            className="bg-white/5 border border-white/15 rounded px-2 py-1.5 text-xs text-white">
            <option value="" className="bg-[#2A1045]">Toutes actions</option>
            {data.actions.map((a) => <option key={a} value={a} className="bg-[#2A1045]">{a}</option>)}
          </select>
          <Input placeholder="Filtrer par référence" value={operation} data-testid="audit-op-filter"
            onChange={(e) => setOperation(e.target.value)} className="w-44 h-8 text-xs bg-white/5 border-white/15 text-white" />
          <Button size="sm" onClick={exportCsv} data-testid="audit-export-csv"
            className="h-8 text-xs bg-[#D9B35A] text-[#2A1045] hover:bg-[#F2D07A]">
            <Download className="w-3.5 h-3.5 mr-1" /> CSV
          </Button>
        </div>
      </div>
      <div className="max-h-72 overflow-y-auto">
        {data.rows.length === 0 && <p className="text-white/40 text-xs">Aucune entrée.</p>}
        {data.rows.map((r, i) => (
          <p key={i} className="text-[11px] text-white/60 py-0.5 border-b border-white/5">
            {r.date.replace('T', ' ')} — <b className="text-[#D9B35A]">{r.operation}</b> · <span className="text-white/85">{r.action}</span> · {r.par}
          </p>
        ))}
      </div>
    </div>
  );
};
