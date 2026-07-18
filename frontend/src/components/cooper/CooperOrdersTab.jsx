import { useState, useEffect, useCallback } from 'react';
import { Loader2, Truck } from 'lucide-react';
import { toast } from 'sonner';
import { apiCall } from '../../services/http';

const NEXT_STATUS = {
  PENDING: ['CONFIRMED', 'CANCELED'],
  CONFIRMED: ['PROCESSING', 'CANCELED'],
  PROCESSING: ['READY_FOR_PICKUP'],
  READY_FOR_PICKUP: ['PICKED_UP'],
  PICKED_UP: ['INVOICED'],
  INVOICED: ['PAID'],
};

const STATUS_LABELS = {
  PENDING: 'En attente', CONFIRMED: 'Confirmée', PROCESSING: 'En préparation',
  READY_FOR_PICKUP: 'Prête (retrait)', PICKED_UP: 'Retirée', INVOICED: 'Facturée',
  PAID: 'Payée', CANCELED: 'Annulée', DRAFT: 'Brouillon',
};

export const CooperOrdersTab = () => {
  const [orders, setOrders] = useState(null);
  const [carriers, setCarriers] = useState([]);

  const load = useCallback(() => {
    Promise.all([
      apiCall('/cooper/carriers').catch(() => ({ carriers: [] })),
      fetch(`${process.env.REACT_APP_BACKEND_URL}/api/v2/orders/admin/all?limit=50`, { credentials: 'include' }).then((r) => r.ok ? r.json() : Promise.reject(new Error('Accès refusé'))),
    ]).then(([c, o]) => {
      setCarriers(c.carriers.filter((x) => x.is_active));
      setOrders(o);
    }).catch((e) => {
      toast.error(e.message || 'Erreur de chargement');
      setOrders([]);
    });
  }, []);

  useEffect(() => { load(); }, [load]);

  const updateStatus = async (orderId, status) => {
    try {
      const r = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/v2/orders/admin/${orderId}/status?new_status=${status}`, {
        method: 'POST', credentials: 'include',
      });
      if (!r.ok) throw new Error((await r.json()).detail || 'Erreur');
      toast.success(`Commande passée à « ${STATUS_LABELS[status] || status} »`);
      load();
    } catch (e) {
      toast.error(e.message);
    }
  };

  const assignCarrier = async (orderId, carrierId) => {
    if (!carrierId) return;
    try {
      const res = await apiCall(`/cooper/orders/${orderId}/assign-carrier`, { method: 'POST', body: JSON.stringify({ carrier_id: carrierId }) });
      toast.success(`Transporteur « ${res.carrier} » assigné`);
      load();
    } catch (e) {
      toast.error(e.message || 'Erreur');
    }
  };

  if (orders === null) return <div className="flex justify-center py-10"><Loader2 className="w-6 h-6 animate-spin text-[#6FA82E]" /></div>;

  return (
    <div className="space-y-3" data-testid="cooper-orders-tab">
      {carriers.length === 0 && (
        <p className="text-xs opacity-60 px-1">Aucun transporteur LOGI'SCOP actif — demandez au super admin d'en ajouter (onglet Conventions).</p>
      )}
      {orders.length === 0 ? (
        <div className="glass-panel-soft rounded-[18px] p-8 text-center text-sm opacity-60" data-testid="cooper-orders-empty">Aucune commande.</div>
      ) : orders.map((o) => (
        <div key={o.id} className="glass-panel-soft rounded-[18px] p-4" data-testid={`cooper-order-${o.id}`}>
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex-1 min-w-[200px]">
              <p className="font-mono text-xs opacity-60">{o.order_number || o.id}</p>
              <p className="text-sm font-medium">
                {((o.total_ttc_cents || 0) / 100).toFixed(2)} € TTC · {o.items_count || o.items?.length || 0} article(s) · {o.zone_code}
              </p>
              <p className="text-xs opacity-60">
                {new Date(o.created_at).toLocaleString('fr-FR')}
                {o.carrier?.name && <span className="ml-2 text-[#B8860B] font-semibold"><Truck className="w-3 h-3 inline mr-1" />{o.carrier.name}</span>}
              </p>
            </div>
            <span className="text-[10px] uppercase font-bold px-2.5 py-1 rounded-full bg-black/5">{STATUS_LABELS[o.status] || o.status}</span>
            <div className="flex gap-2 items-center flex-wrap">
              {(NEXT_STATUS[o.status] || []).map((s) => (
                <button key={s} onClick={() => updateStatus(o.id, s)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-semibold border transition-colors ${s === 'CANCELED' ? 'text-red-600 border-red-500/30 hover:bg-red-500/10' : 'text-[#4d7a1c] border-[#6FA82E]/40 bg-[#6FA82E]/10 hover:bg-[#6FA82E]/20'}`}
                  data-testid={`cooper-order-status-${o.id}-${s}`}>
                  → {STATUS_LABELS[s] || s}
                </button>
              ))}
              {carriers.length > 0 && (
                <select defaultValue="" onChange={(e) => assignCarrier(o.id, e.target.value)}
                  className="h-8 px-2 rounded-xl border border-black/10 bg-white text-xs"
                  data-testid={`cooper-order-carrier-${o.id}`}>
                  <option value="" disabled>{o.carrier?.name ? 'Changer transporteur' : "Assigner transporteur LOGI'SCOP"}</option>
                  {carriers.map((c) => <option key={c.id} value={c.id}>{c.name} ({c.territory})</option>)}
                </select>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};
