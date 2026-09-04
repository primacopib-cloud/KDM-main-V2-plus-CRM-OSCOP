import { useCallback, useEffect, useState } from 'react';
import { Loader2, ShieldAlert, Plus } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Badge } from '../ui/badge';

const eur = (v) => `${Number(v || 0).toLocaleString('fr-FR')} €`;

export const FogedomPanel = ({ operations }) => {
  const [data, setData] = useState(null);
  const [form, setForm] = useState({ operation_id: '', requested_amount: '', purpose: 'EXPERTISE', description: '' });

  const load = useCallback(async () => {
    const res = await fetch(`${API}/admin/fogedom/decisions`, { headers: getAuthHeaders() });
    if (res.ok) setData(await res.json());
  }, []);
  useEffect(() => { load(); }, [load]);

  const call = async (url, method, body, okMsg) => {
    const res = await fetch(url, { method, headers: { 'Content-Type': 'application/json', ...getAuthHeaders() }, body: JSON.stringify(body) });
    const json = await res.json();
    if (!res.ok) { toast.error(typeof json.detail === 'string' ? json.detail : 'Erreur'); return; }
    toast.success(okMsg);
    load();
  };

  if (!data) return <div className="py-6 text-center"><Loader2 className="w-5 h-5 animate-spin text-[#D9B35A] mx-auto" /></div>;

  return (
    <div className="glass-panel-soft rounded-[18px] p-4 mt-5" data-testid="fogedom-panel">
      <h3 className="text-lg font-bold text-white flex items-center gap-2 mb-1">
        <ShieldAlert className="w-5 h-5 text-[#D9B35A]" /> FOGEDOM-SCIC — Registre des décisions d'appui
      </h3>
      <p className="text-amber-200/85 text-xs mb-3 p-2 rounded bg-amber-500/10 border border-amber-400/25" data-testid="fogedom-disclaimer">
        {data.disclaimer}
      </p>

      <div className="flex flex-wrap gap-1.5 mb-3">
        <select value={form.operation_id} onChange={(e) => setForm({ ...form, operation_id: e.target.value })}
          data-testid="fogedom-op-select" className="bg-white/5 border border-white/15 rounded px-2 py-1.5 text-xs text-white max-w-[200px]">
          <option value="" className="bg-[#2A1045]">— opération —</option>
          {(operations || []).map((o) => <option key={o.id} value={o.id} className="bg-[#2A1045]">{o.reference}</option>)}
        </select>
        <select value={form.purpose} onChange={(e) => setForm({ ...form, purpose: e.target.value })}
          data-testid="fogedom-purpose-select" className="bg-white/5 border border-white/15 rounded px-2 py-1.5 text-xs text-white">
          {data.purposes.map((p) => <option key={p} className="bg-[#2A1045]">{p}</option>)}
        </select>
        <Input placeholder="Montant demandé €" value={form.requested_amount} data-testid="fogedom-amount"
          onChange={(e) => setForm({ ...form, requested_amount: e.target.value })} className="w-36 h-8 text-xs bg-white/5 border-white/15 text-white" />
        <Input placeholder="Description" value={form.description} data-testid="fogedom-description"
          onChange={(e) => setForm({ ...form, description: e.target.value })} className="flex-1 min-w-[160px] h-8 text-xs bg-white/5 border-white/15 text-white" />
        <Button size="sm" data-testid="fogedom-create"
          className="bg-[#D9B35A] text-[#2A1045] hover:bg-[#F2D07A] h-8"
          onClick={() => call(`${API}/admin/fogedom/decisions`, 'POST',
            { ...form, requested_amount: parseFloat(String(form.requested_amount).replace(',', '.')) || 0 }, 'Demande enregistrée')}>
          <Plus className="w-4 h-4" />
        </Button>
      </div>

      {data.decisions.length === 0 && <p className="text-white/40 text-xs">Aucune décision au registre.</p>}
      {data.decisions.map((d) => (
        <div key={d.id} className="p-2.5 rounded bg-white/5 mb-1.5 text-xs" data-testid={`fogedom-decision-${d.id}`}>
          <div className="flex items-center justify-between flex-wrap gap-2">
            <span className="text-white/85">{d.operation_reference} · {d.purpose} · demandé {eur(d.requested_amount)}
              {d.approved_amount ? ` · approuvé ${eur(d.approved_amount)}` : ''}</span>
            <div className="flex items-center gap-1.5">
              <Badge className={`border-0 text-[9px] ${d.status === 'APPROVED' ? 'bg-emerald-500/20 text-emerald-300' : d.status === 'REJECTED' ? 'bg-red-500/20 text-red-300' : 'bg-white/10 text-white/60'}`}>
                {d.status}
              </Badge>
              {d.status === 'PENDING' && (
                <>
                  <Button size="sm" data-testid={`fogedom-approve-${d.id}`} className="h-6 text-[10px] bg-emerald-600/40 hover:bg-emerald-600/60 text-white"
                    onClick={() => call(`${API}/admin/fogedom/decisions/${d.id}`, 'PATCH',
                      { status: 'APPROVED', approved_amount: d.requested_amount, available_resources_checked: true }, 'Appui approuvé (ressources vérifiées)')}>
                    Approuver
                  </Button>
                  <Button size="sm" data-testid={`fogedom-reject-${d.id}`} className="h-6 text-[10px] bg-red-600/30 hover:bg-red-600/50 text-white"
                    onClick={() => call(`${API}/admin/fogedom/decisions/${d.id}`, 'PATCH', { status: 'REJECTED' }, 'Demande rejetée')}>
                    Rejeter
                  </Button>
                </>
              )}
            </div>
          </div>
          {d.description && <p className="text-white/45 mt-1">{d.description}</p>}
        </div>
      ))}
    </div>
  );
};
