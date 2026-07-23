import { useCallback, useEffect, useState } from 'react';
import { TabsContent } from '../../ui/tabs';
import { CheckCircle2, FileDown } from 'lucide-react';
import { API, getAuthHeaders, getSessionToken } from '../../../services/http';
import { LogiscopSubscribeCard, downloadTransportPdf } from './LogiscopSubscribeCard';
import { TransportOrderForm } from './TransportOrderForm';
import { TransportOrdersList } from './TransportOrdersList';

export const BuyerTransportTab = () => {
  const [sub, setSub] = useState(null);
  const [orders, setOrders] = useState([]);
  const [invoicesByOt, setInvoicesByOt] = useState({});

  const authHeaders = () => ({ Authorization: `Bearer ${getSessionToken()}`, ...getAuthHeaders() });

  const load = useCallback(() => {
    fetch(`${API}/logiscop-transport/my-subscription`, { credentials: 'include', headers: authHeaders() })
      .then((r) => (r.ok ? r.json() : null)).then(setSub).catch(() => {});
    fetch(`${API}/logiscop-transport/orders`, { credentials: 'include', headers: authHeaders() })
      .then((r) => (r.ok ? r.json() : [])).then((d) => setOrders(Array.isArray(d) ? d : [])).catch(() => {});
    fetch(`${API}/logiscop-transport/invoices`, { credentials: 'include', headers: authHeaders() })
      .then((r) => (r.ok ? r.json() : []))
      .then((list) => {
        const map = {};
        (Array.isArray(list) ? list : []).forEach((i) => { map[i.ot_id] = i; });
        setInvoicesByOt(map);
      }).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const conv = sub?.convention;
  const signed = conv?.status === 'SIGNED';

  return (
    <TabsContent value="transport" className="space-y-4" data-testid="buyer-transport-tab">
      <p className="text-[11px] text-white/40">
        Transport routier LOGI'SCOP Mode D — convention d'adhésion-cadre tripartite V1.2 et Ordres de Transport
        nominatifs, limités aux zones couvertes par votre abonnement.
      </p>
      {sub && !signed && (
        <LogiscopSubscribeCard convention={conv} zones={sub.zones || []} onChanged={load} />
      )}
      {signed && (
        <div className="rounded-xl p-4 bg-emerald-500/[0.06] border border-emerald-500/25 flex flex-wrap items-center justify-between gap-2"
          data-testid="logiscop-active-banner">
          <p className="flex items-center gap-2 text-xs text-emerald-300">
            <CheckCircle2 size={14} />
            Convention <b>{conv.ref}</b> signée le {new Date(conv.signed_at).toLocaleDateString('fr-FR')} —
            zones : {conv.zones.join(', ')}
          </p>
          <button type="button" data-testid="logiscop-signed-pdf-btn"
            onClick={() => downloadTransportPdf(`/logiscop-transport/convention/${conv.id}/pdf`,
              `convention-logiscop-${conv.ref.replace(/\//g, '-')}.pdf`)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold bg-white/[0.06] text-white/75 hover:text-[#E9CF8E] border border-white/15">
            <FileDown size={12} /> Convention signée (PDF)
          </button>
        </div>
      )}
      {signed && <TransportOrderForm zones={conv.zones || []} onCreated={load} />}
      <TransportOrdersList orders={orders} invoicesByOt={invoicesByOt} onChanged={load} />
    </TabsContent>
  );
};
