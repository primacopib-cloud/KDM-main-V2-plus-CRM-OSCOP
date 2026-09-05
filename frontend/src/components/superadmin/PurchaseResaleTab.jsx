import { useCallback, useEffect, useState } from 'react';
import { Loader2, Plus, Repeat, AlertTriangle, Truck } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { OperationFormDialog } from './purchase-resale/OperationFormDialog';
import { OperationDetail } from './purchase-resale/OperationDetail';
import { PrintSectionButton } from '../PrintSectionButton';
import { Operation360 } from './purchase-resale/Operation360';

const eur = (v) => `${Number(v || 0).toLocaleString('fr-FR', { minimumFractionDigits: 2 })} €`;

const STATUS_COLORS = {
  DRAFT: 'bg-white/10 text-white/70',
  INVESTOR_COMMITTED: 'bg-emerald-500/20 text-emerald-300',
  SUPPLIER_PAID: 'bg-sky-500/20 text-sky-300',
  CLIENT_PAID: 'bg-emerald-500/20 text-emerald-300',
  CLOSED: 'bg-white/15 text-white/60',
  CANCELLED: 'bg-red-500/20 text-red-300',
  DISPUTED: 'bg-red-500/20 text-red-300',
};

export const PurchaseResaleTab = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [formOpen, setFormOpen] = useState(false);
  const [selected, setSelected] = useState(null);
  const [view360, setView360] = useState(null);

  const load = useCallback(async () => {
    try {
      const res = await fetch(`${API}/admin/purchase-resale/operations`, { headers: getAuthHeaders() });
      if (!res.ok) throw new Error('Chargement impossible');
      setData(await res.json());
    } catch (e) {
      toast.error(String(e.message || e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) return <div className="flex justify-center py-16"><Loader2 className="w-6 h-6 animate-spin text-[#D9B35A]" /></div>;

  const ops = data?.operations || [];

  return (
    <div className="space-y-5" data-testid="purchase-resale-tab" data-print-section>
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Repeat className="w-5 h-5 text-[#D9B35A]" />
            Achat-Revente O'SCOP
          </h2>
          <p className="text-white/60 text-sm mt-1">
            Opérations où O'SCOP achète, revend, facture et encaisse — logistique LOGI'SCOP intégrée.
          </p>
        </div>
        <Button onClick={() => setFormOpen(true)} data-testid="new-operation-btn"
          className="bg-[#D9B35A] text-[#2A1045] hover:bg-[#F2D07A] font-semibold">
          <Plus className="w-4 h-4 mr-1" /> Nouvelle opération
        </Button>
        <PrintSectionButton />
      </div>

      <div className="rounded-[14px] p-3 border border-sky-400/25 bg-sky-500/10 flex gap-2 items-start">
        <Truck className="w-4 h-4 text-sky-300 shrink-0 mt-0.5" />
        <p className="text-sky-100/85 text-xs">{data?.logiscop_notice}</p>
      </div>

      {ops.length === 0 ? (
        <div className="glass-panel-soft rounded-[22px] p-10 text-center text-white/50" data-testid="no-operations">
          Aucune opération d'achat-revente. Créez la première.
        </div>
      ) : (
        <div className="space-y-2">
          {ops.map((op) => (
            <div key={op.id}>
              <button
                type="button"
                onClick={() => setSelected(selected === op.id ? null : op.id)}
                data-testid={`operation-row-${op.reference}`}
                className="w-full text-left glass-panel-soft rounded-[16px] p-4 hover:bg-white/5 transition-colors"
              >
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <div className="flex items-center gap-3">
                    <span className="font-semibold text-white/90">{op.reference}</span>
                    <Badge className={`${STATUS_COLORS[op.status] || 'bg-purple-500/20 text-purple-200'} border-0 text-[10px]`}>
                      {op.status}
                    </Badge>
                    {op.logistics_mode !== 'CUSTOMER_HANDLED' && (
                      <Badge className="bg-sky-500/15 text-sky-300 border-0 text-[10px]">LOGI'SCOP</Badge>
                    )}
                    {op.blockers?.length > 0 && (
                      <span className="inline-flex items-center gap-1 text-amber-300 text-[11px]">
                        <AlertTriangle className="w-3 h-3" /> {op.blockers.length} blocage(s)
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-4 text-xs text-white/60">
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); setView360(op.id); }}
                      data-testid={`view360-btn-${op.reference}`}
                      className="px-2 py-0.5 rounded bg-white/10 hover:bg-white/20 text-white/80 text-[10px] font-semibold"
                    >
                      Vue 360°
                    </button>
                    <span>{op.client_name}</span>
                    <span>Achat {eur(op.purchase_amount_ex_vat)}</span>
                    <span>Revente {eur(op.resale_total_ex_vat)}</span>
                    <span className={op.expected_margin_ex_vat >= 0 ? 'text-emerald-300' : 'text-red-300'}>
                      Marge {eur(op.expected_margin_ex_vat)} ({op.expected_margin_rate}%)
                    </span>
                  </div>
                </div>
              </button>
              {selected === op.id && (
                <OperationDetail operationId={op.id} meta={data} onChanged={load} />
              )}
            </div>
          ))}
        </div>
      )}

      <OperationFormDialog open={formOpen} onClose={() => setFormOpen(false)} onCreated={load} />
      {view360 && <Operation360 operationId={view360} onClose={() => setView360(null)} />}
    </div>
  );
};
