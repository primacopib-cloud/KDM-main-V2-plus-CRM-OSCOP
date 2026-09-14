import { Check } from 'lucide-react';

const STATUS_ORDER = ['PAID', 'PREPARING', 'READY', 'FULFILLED'];

// Timeline visuelle de commande : payée → préparée → prête → retirée/livrée
export const OrderTimeline = ({ order }) => {
  if (!order || order.status === 'CANCELLED') return null;
  const isDelivery = order.fulfillment_type === 'DELIVERY';
  const steps = [
    { key: 'PAID', label: 'Payée' },
    { key: 'PREPARING', label: 'Préparée' },
    { key: 'READY', label: 'Prête' },
    { key: 'FULFILLED', label: isDelivery ? 'Livrée' : 'Retirée' },
  ];
  const idx = STATUS_ORDER.indexOf(order.status); // -1 pour DRAFT/PENDING_PAYMENT

  return (
    <div className="flex items-center mt-1.5" data-testid={`order-timeline-${order.id}`}>
      {steps.map((s, i) => {
        const done = i < idx || (i === idx && s.key === 'FULFILLED');
        const current = i === idx && s.key !== 'FULFILLED';
        return (
          <div key={s.key} className="flex items-center" style={{ flex: i < steps.length - 1 ? 1 : 'none' }}>
            <div className="flex flex-col items-center" style={{ width: 44 }}>
              <span
                data-testid={`timeline-step-${order.id}-${s.key}`}
                className={`w-4 h-4 rounded-full flex items-center justify-center border transition-colors ${
                  done ? 'bg-emerald-500/90 border-emerald-400' :
                  current ? 'bg-[#D9B35A] border-[#E9CF8E]' :
                  'bg-white/[0.05] border-white/15'}`}>
                {done && <Check className="w-2.5 h-2.5 text-black" strokeWidth={3.5} />}
                {current && <span className="w-1.5 h-1.5 rounded-full bg-black" />}
              </span>
              <span className={`text-[8px] mt-0.5 font-semibold uppercase tracking-wide ${
                done ? 'text-emerald-300' : current ? 'text-[#E9CF8E]' : 'text-white/30'}`}>
                {s.label}
              </span>
            </div>
            {i < steps.length - 1 && (
              <span className={`h-[2px] flex-1 -mt-3 rounded ${i < idx ? 'bg-emerald-500/70' : 'bg-white/10'}`} />
            )}
          </div>
        );
      })}
    </div>
  );
};
