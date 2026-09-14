import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { PackageCheck, ArrowRight } from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';
import { lolodriveAPI } from '../../services/api';
import { OrderTimeline } from './OrderTimeline';

const ACTIVE = ['PAID', 'PREPARING', 'READY'];

// Widget d'accueil : prochaine commande à retirer avec sa timeline
export const NextPickupWidget = () => {
  const [order, setOrder] = useState(null);
  const [pointName, setPointName] = useState('');

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const res = await lolodriveAPI.myOrders();
        const list = (res.orders || [])
          .filter((o) => ACTIVE.includes(o.status))
          .sort((a, b) => String(a.pickup_date || '9999').localeCompare(String(b.pickup_date || '9999')));
        if (!mounted || !list.length) return;
        const next = list[0];
        setOrder(next);
        const pid = next.lolo_point_id || next.reference_point_id;
        if (pid) {
          const pts = await lolodriveAPI.listLoloPoints().catch(() => null);
          const p = (pts?.points || []).find((x) => x.id === pid);
          if (mounted && p) setPointName(p.name);
        }
      } catch {
        /* visiteur ou non connecté : pas de widget */
      }
    })();
    return () => { mounted = false; };
  }, []);

  if (!order) return null;
  const ready = order.status === 'READY';
  const when = order.pickup_date
    ? new Date(`${order.pickup_date}T12:00:00`).toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' })
    : null;

  return (
    <div className={`mb-4 rounded-2xl border p-4 ${ready ? 'border-emerald-400/50' : 'border-[#D9B35A]/30'}`}
      style={{ background: ready
        ? 'linear-gradient(90deg, rgba(16,185,129,0.14), rgba(255,255,255,0.02))'
        : 'linear-gradient(90deg, rgba(217,179,90,0.10), rgba(255,255,255,0.02))' }}
      data-testid="next-pickup-widget">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-bold text-white flex items-center gap-2">
            <PackageCheck className={`w-4 h-4 ${ready ? 'text-emerald-300' : 'text-[#D9B35A]'}`} />
            {ready ? 'Votre commande est prête !' : 'Prochaine commande à retirer'}
          </p>
          <p className="text-[11px] text-white/55 mt-0.5" data-testid="next-pickup-detail">
            <span className="font-mono text-white/75">{order.order_number}</span>
            {when && <> · {when}</>}
            {order.pickup_slot_label && <> · {order.pickup_slot_label}</>}
            {pointName && <> · relais <span className="text-[#E9CF8E]">{pointName}</span></>}
          </p>
          <div className="mt-1">
            <OrderTimeline order={order} />
          </div>
        </div>
        <div className="flex flex-col items-center gap-1.5 shrink-0">
          {ready && (
            <div className="p-2 rounded-xl bg-white" data-testid="next-pickup-qr">
              <QRCodeSVG value={order.order_number} size={72} level="M" fgColor="#111111" bgColor="#ffffff" />
              <p className="text-[8px] font-bold text-black/60 text-center mt-1 uppercase">QR retrait</p>
            </div>
          )}
          <Link to="/espace-pass" data-testid="next-pickup-link"
            className="inline-flex items-center gap-1 text-xs font-bold text-[#E9CF8E] hover:text-white border border-[#D9B35A]/40 rounded-full px-3 h-8">
            Gérer <ArrowRight className="w-3 h-3" />
          </Link>
        </div>
      </div>
      {ready && (
        <p className="text-[11px] font-semibold text-emerald-300 mt-2" data-testid="next-pickup-ready">
          Présentez-vous au relais avec votre numéro de commande ou faites scanner le QR.
        </p>
      )}
    </div>
  );
};
