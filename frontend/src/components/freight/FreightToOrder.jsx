import { useEffect, useState } from 'react';
import { PackagePlus, Loader2, Lock } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';
import { Button } from '../ui/button';
import { ordersAPIV2 } from '../../services/api';

export const getStoredUser = () => {
  try { return JSON.parse(localStorage.getItem('user') || 'null'); } catch { return null; }
};

export const canUseFreight = (u) =>
  !!u && (u.is_admin || ['admin', 'superadmin', 'buyer'].includes(u.role));

export const FreightAccessGate = () => (
  <div className="max-w-[560px] mx-auto my-16 glass-panel-soft rounded-[22px] p-8 text-center" data-testid="freight-access-gate">
    <Lock className="w-8 h-8 text-[#D9B35A] mx-auto mb-3" />
    <h2 className="text-lg font-bold text-white mb-2">Accès réservé</h2>
    <p className="text-white/70 text-sm mb-4">
      Le calculateur de fret maritime LOGI'SCOP est accessible exclusivement aux acheteurs
      professionnels et à l'administration O'SCOP.
    </p>
    <a href="/connexion" className="on-gold inline-flex items-center px-4 py-2.5 rounded-[12px] bg-[#D9B35A] hover:bg-[#F2D07A] text-sm font-bold">
      Se connecter
    </a>
  </div>
);

export const FreightToOrder = ({ quote }) => {
  const [orders, setOrders] = useState([]);
  const [orderId, setOrderId] = useState('');
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    ordersAPIV2.list(undefined, 0, 25)
      .then((d) => setOrders(Array.isArray(d) ? d : d.orders || []))
      .catch(() => {});
  }, []);

  const attach = async () => {
    if (!orderId) return;
    setBusy(true);
    try {
      const res = await fetch(`${API}/freight/attach-to-order`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        credentials: 'include',
        body: JSON.stringify({ order_id: orderId, quote }),
      });
      const d = await res.json();
      if (!res.ok) throw new Error(d.detail || 'Erreur');
      setDone(true);
      toast.success('Devis fret intégré à la commande ✓');
    } catch (e) {
      toast.error(String(e.message || e));
    } finally {
      setBusy(false);
    }
  };

  if (orders.length === 0) return null;
  return (
    <div className="mt-3 pt-3 border-t border-white/10" data-testid="freight-to-order">
      <p className="text-[11px] font-semibold text-white/60 uppercase mb-2">Intégrer ce devis à ma commande</p>
      <div className="flex gap-2 flex-wrap items-center">
        <select value={orderId} onChange={(e) => { setOrderId(e.target.value); setDone(false); }}
          data-testid="freight-order-select"
          className="flex-1 min-w-[180px] h-9 px-2 rounded-lg bg-white/[0.06] border border-white/15 text-sm text-white">
          <option value="">— choisir une commande —</option>
          {orders.map((o) => (
            <option key={o.id} value={o.id}>{o.order_number} · {(o.total_cents / 100).toLocaleString('fr-FR')} €</option>
          ))}
        </select>
        <Button onClick={attach} disabled={busy || !orderId || done} data-testid="freight-attach-btn"
          className={done ? 'h-9 bg-emerald-600 text-white' : 'on-gold h-9 bg-[#D9B35A] hover:bg-[#F2D07A] font-semibold'}>
          {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <PackagePlus className="w-4 h-4 mr-1" />}
          {done ? 'Intégré ✓' : 'Intégrer à la commande'}
        </Button>
      </div>
    </div>
  );
};
