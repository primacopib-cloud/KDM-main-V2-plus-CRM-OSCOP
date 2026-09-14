import { useEffect, useState } from 'react';
import { Zap } from 'lucide-react';
import { toast } from 'sonner';
import { lolodriveAPI } from '../../services/api';

const LABELS = { 1: 'Très lent', 2: 'Lent', 3: 'Correct', 4: 'Rapide', 5: 'Express !' };

// Mini-note de fluidité du créneau juste après un retrait
export const SlotRatingPrompt = () => {
  const [pending, setPending] = useState([]);
  const [hover, setHover] = useState(0);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    lolodriveAPI.slotRatingPending()
      .then((d) => setPending(d.pending || []))
      .catch(() => {});
  }, []);

  if (!pending.length) return null;
  const cur = pending[0];

  const rate = async (n) => {
    setBusy(true);
    try {
      await lolodriveAPI.submitSlotRating(cur.order_id, n);
      toast.success('Merci ! Votre note aide le relais à fluidifier ses créneaux ⚡');
      setPending(pending.slice(1));
      setHover(0);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mb-6 rounded-2xl border border-emerald-400/30 p-4"
      style={{ background: 'linear-gradient(90deg, rgba(16,185,129,0.10), rgba(255,255,255,0.02))' }}
      data-testid="slot-rating-prompt">
      <p className="text-sm font-bold text-white">
        Votre retrait a-t-il été rapide{cur.point_name ? ` chez ${cur.point_name}` : ''} ?
      </p>
      <p className="text-[11px] text-white/45 mb-2.5">
        Commande {cur.order_number} · {cur.pickup_slot_label} — une note en 1 clic pour mesurer la fluidité des créneaux.
      </p>
      <div className="flex items-center gap-1.5" data-testid="slot-rating-zaps">
        {[1, 2, 3, 4, 5].map((n) => (
          <button key={n} type="button" disabled={busy} onClick={() => rate(n)}
            onMouseEnter={() => setHover(n)} onMouseLeave={() => setHover(0)}
            data-testid={`slot-rating-${n}`}
            className="transition-transform hover:scale-125 disabled:opacity-50">
            <Zap className={`w-6 h-6 ${hover >= n ? 'fill-emerald-400 text-emerald-400' : 'text-white/25'}`} />
          </button>
        ))}
        <span className="text-[11px] text-emerald-300/80 ml-2 min-w-[70px]">{hover ? LABELS[hover] : ''}</span>
      </div>
    </div>
  );
};
