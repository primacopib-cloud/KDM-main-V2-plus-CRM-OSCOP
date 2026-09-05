import { useCallback, useEffect, useState } from 'react';
import { Loader2, Truck, Package, ClipboardCheck, Plus } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../services/http';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { MessagesNavLink } from '../components/MessagesNavLink';
import { Badge } from '../components/ui/badge';
import Header from '../components/Header';

const eur = (v) => `${Number(v || 0).toLocaleString('fr-FR')} €`;

const Section = ({ opId, meta, onChanged }) => {
  const [detail, setDetail] = useState(null);
  const [shp, setShp] = useState({ origin: '', destination: '', transport_mode: 'MARITIME', carrier_name: '' });
  const [wh, setWh] = useState({ location: '', movement: 'IN', quantity: '' });
  const [pod, setPod] = useState({ received_by: '', reference: '' });

  const load = useCallback(async () => {
    const res = await fetch(`${API}/admin/logiscop-ops/operations/${opId}`, { headers: getAuthHeaders() });
    if (res.ok) setDetail(await res.json());
  }, [opId]);
  useEffect(() => { load(); }, [load]);

  const post = async (url, body, okMsg) => {
    const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json', ...getAuthHeaders() }, body: JSON.stringify(body) });
    const json = await res.json();
    if (!res.ok) { toast.error(typeof json.detail === 'string' ? json.detail : 'Erreur'); return; }
    toast.success(okMsg);
    await load();
    onChanged();
  };

  if (!detail) return <div className="p-4"><Loader2 className="w-4 h-4 animate-spin text-[#D9B35A]" /></div>;

  return (
    <div className="mx-1 mb-3 p-4 rounded-[14px] bg-black/25 border border-white/10 grid md:grid-cols-3 gap-4" data-testid={`logiscop-detail-${detail.operation.reference}`}>
      <div>
        <p className="text-[11px] font-semibold text-white/70 uppercase mb-1.5 flex items-center gap-1"><Truck className="w-3.5 h-3.5" /> Expéditions</p>
        {detail.shipments.map((s) => (
          <div key={s.id} className="p-2 rounded bg-white/5 mb-1.5 text-[11px]">
            <div className="flex justify-between text-white/85"><span>{s.shipment_number}</span><Badge className="bg-sky-500/15 text-sky-300 border-0 text-[9px]">{s.status}</Badge></div>
            <p className="text-white/50">{s.origin} → {s.destination} · {s.transport_mode}{s.carrier_name ? ` · ${s.carrier_name}` : ''}</p>
            {s.milestones.map((m) => <p key={m.id} className="text-white/45">• {m.milestone} — {m.created_at.slice(0, 16).replace('T', ' ')}</p>)}
            <div className="flex gap-1 mt-1">
              <select id={`ms-${s.id}`} data-testid={`milestone-select-${s.shipment_number}`}
                className="flex-1 bg-white/5 border border-white/15 rounded px-1.5 py-1 text-[10px] text-white">
                {meta.logistics_statuses.map((st) => <option key={st} className="bg-[#2A1045]">{st}</option>)}
              </select>
              <Button size="sm" data-testid={`milestone-add-${s.shipment_number}`} className="h-6 text-[10px] bg-white/10 hover:bg-white/20 text-white"
                onClick={() => post(`${API}/admin/logiscop-ops/shipments/${s.id}/milestones`,
                  { milestone: document.getElementById(`ms-${s.id}`).value }, 'Jalon enregistré')}>
                Jalon
              </Button>
            </div>
          </div>
        ))}
        <div className="space-y-1 mt-2">
          <Input placeholder="Origine" value={shp.origin} data-testid="shipment-origin" onChange={(e) => setShp({ ...shp, origin: e.target.value })} className="bg-white/5 border-white/15 text-white h-7 text-xs" />
          <Input placeholder="Destination" value={shp.destination} data-testid="shipment-destination" onChange={(e) => setShp({ ...shp, destination: e.target.value })} className="bg-white/5 border-white/15 text-white h-7 text-xs" />
          <div className="flex gap-1">
            <select value={shp.transport_mode} onChange={(e) => setShp({ ...shp, transport_mode: e.target.value })}
              data-testid="shipment-mode" className="flex-1 bg-white/5 border border-white/15 rounded px-2 py-1 text-xs text-white">
              {meta.transport_modes.map((m) => <option key={m} className="bg-[#2A1045]">{m}</option>)}
            </select>
            <Input placeholder="Transporteur" value={shp.carrier_name} onChange={(e) => setShp({ ...shp, carrier_name: e.target.value })} className="flex-1 bg-white/5 border-white/15 text-white h-7 text-xs" />
          </div>
          <Button size="sm" data-testid="shipment-create" className="w-full h-7 text-xs bg-white/10 hover:bg-white/20 text-white"
            onClick={() => post(`${API}/admin/logiscop-ops/operations/${opId}/shipments`, shp, 'Expédition créée')}>
            <Plus className="w-3 h-3 mr-1" /> Créer une expédition
          </Button>
        </div>
      </div>

      <div>
        <p className="text-[11px] font-semibold text-white/70 uppercase mb-1.5 flex items-center gap-1"><Package className="w-3.5 h-3.5" /> Stockage</p>
        {detail.warehouse.map((w) => (
          <p key={w.id} className="text-[11px] text-white/60 mb-1">
            {w.movement === 'IN' ? '⬇' : '⬆'} {w.quantity} — {w.location} · {w.created_at.slice(0, 10)}
          </p>
        ))}
        <div className="space-y-1 mt-2">
          <Input placeholder="Entrepôt / lieu" value={wh.location} data-testid="warehouse-location" onChange={(e) => setWh({ ...wh, location: e.target.value })} className="bg-white/5 border-white/15 text-white h-7 text-xs" />
          <div className="flex gap-1">
            <select value={wh.movement} onChange={(e) => setWh({ ...wh, movement: e.target.value })}
              data-testid="warehouse-movement" className="bg-white/5 border border-white/15 rounded px-2 py-1 text-xs text-white">
              <option className="bg-[#2A1045]" value="IN">Entrée</option>
              <option className="bg-[#2A1045]" value="OUT">Sortie</option>
            </select>
            <Input placeholder="Quantité" value={wh.quantity} data-testid="warehouse-qty" onChange={(e) => setWh({ ...wh, quantity: e.target.value })} className="flex-1 bg-white/5 border-white/15 text-white h-7 text-xs" />
          </div>
          <Button size="sm" data-testid="warehouse-add" className="w-full h-7 text-xs bg-white/10 hover:bg-white/20 text-white"
            onClick={() => post(`${API}/admin/logiscop-ops/operations/${opId}/warehouse`,
              { ...wh, quantity: parseFloat(wh.quantity) || 0 }, 'Mouvement enregistré')}>
            Enregistrer le mouvement
          </Button>
        </div>
      </div>

      <div>
        <p className="text-[11px] font-semibold text-white/70 uppercase mb-1.5 flex items-center gap-1"><ClipboardCheck className="w-3.5 h-3.5" /> Preuves de livraison</p>
        {detail.pods.map((p) => (
          <p key={p.id} className="text-[11px] text-emerald-300/85 mb-1">✓ {p.pod_number} — reçu par {p.received_by}</p>
        ))}
        {detail.shipments.length > 0 && (
          <div className="space-y-1 mt-2">
            <Input placeholder="Reçu par (nom)" value={pod.received_by} data-testid="pod-received-by" onChange={(e) => setPod({ ...pod, received_by: e.target.value })} className="bg-white/5 border-white/15 text-white h-7 text-xs" />
            <Input placeholder="Référence BL" value={pod.reference} data-testid="pod-reference" onChange={(e) => setPod({ ...pod, reference: e.target.value })} className="bg-white/5 border-white/15 text-white h-7 text-xs" />
            <Button size="sm" data-testid="pod-validate" className="w-full h-7 text-xs bg-emerald-600/40 hover:bg-emerald-600/60 text-white"
              onClick={() => post(`${API}/admin/logiscop-ops/shipments/${detail.shipments[detail.shipments.length - 1].id}/pod`, pod, 'POD validée')}>
              Valider la preuve de livraison
            </Button>
          </div>
        )}
      </div>
    </div>
  );
};

export default function LogiscopSpacePage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [selected, setSelected] = useState(null);

  const load = useCallback(async () => {
    const res = await fetch(`${API}/admin/logiscop-ops/operations`, { headers: getAuthHeaders() });
    if (!res.ok) { setError(res.status); return; }
    setData(await res.json());
  }, []);
  useEffect(() => { load(); }, [load]);

  return (
    <div className="min-h-screen text-white" style={{ background: 'linear-gradient(180deg, #2A1045 0%, #451F6B 55%, #2A1045 100%)' }}>
      <Header />
      <main className="max-w-[1200px] mx-auto px-5 py-10" data-testid="logiscop-space-page">
        <h1 className="text-3xl font-bold tracking-tight mb-1 flex items-center gap-2">
          <Truck className="w-7 h-7 text-[#D9B35A]" /> Espace LOGI'SCOP
          <MessagesNavLink withLabel />
        </h1>
        {data && <p className="text-sky-200/75 text-xs mb-6 p-2.5 rounded bg-sky-500/10 border border-sky-400/20">{data.notice}</p>}
        {error && <p className="text-amber-300 text-sm">Accès réservé aux opérateurs LOGI'SCOP — connectez-vous avec un compte autorisé.</p>}
        {!data && !error && <Loader2 className="w-6 h-6 animate-spin text-[#D9B35A]" />}
        {data && data.operations.length === 0 && (
          <p className="text-white/50" data-testid="logiscop-no-operations">Aucune opération avec logistique LOGI'SCOP.</p>
        )}
        {data && data.operations.map((op) => (
          <div key={op.id} className="mb-2">
            <button type="button" onClick={() => setSelected(selected === op.id ? null : op.id)}
              data-testid={`logiscop-op-${op.reference}`}
              className="w-full text-left glass-panel-soft rounded-[16px] p-4 hover:bg-white/5 transition-colors">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <div className="flex items-center gap-3">
                  <span className="font-semibold text-white/90">{op.reference}</span>
                  <Badge className="bg-sky-500/15 text-sky-300 border-0 text-[10px]">{op.logistics_status}</Badge>
                  <span className="text-xs text-white/50">{op.logistics_mode}</span>
                </div>
                <div className="text-xs text-white/60 flex gap-4">
                  <span>Budget {eur(op.logistics_budget_ex_vat)}</span>
                  <span>Externes {eur(op.logistics_external_paid_amount)}</span>
                  <span>Alloc. interne {eur(op.logiscop_internal_allocated_amount)}</span>
                  <span>{op.shipments_count} exp. · {op.pods_count} POD</span>
                </div>
              </div>
            </button>
            {selected === op.id && <Section opId={op.id} meta={data} onChanged={load} />}
          </div>
        ))}
      </main>
    </div>
  );
}
