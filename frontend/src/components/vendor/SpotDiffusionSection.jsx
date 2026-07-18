import { useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import { CalendarClock, Loader2 } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const SpotDiffusionSection = ({ vendorId, productId }) => {
  const [options, setOptions] = useState([]);
  const [current, setCurrent] = useState(null);
  const [booking, setBooking] = useState('');

  const refresh = useCallback(async () => {
    const [gRes, dRes] = await Promise.all([
      fetch(`${API}/diffusion-grid`),
      fetch(`${API}/vendor/diffusion/${vendorId}`),
    ]);
    if (gRes.ok) setOptions((await gRes.json()).options || []);
    if (dRes.ok) {
      const diffs = ((await dRes.json()).diffusions || [])
        .filter((d) => d.product_id === productId && d.status !== 'EXPIRED');
      setCurrent(diffs.sort((a, b) => (a.ends_at < b.ends_at ? 1 : -1))[0] || null);
    }
  }, [vendorId, productId]);

  useEffect(() => { refresh(); }, [refresh]);

  const book = async (option) => {
    if (!window.confirm(`Diffuser ce spot en galerie pendant ${option.label} pour ${option.price_credits} crédits coopératifs ?`)) return;
    setBooking(option.id);
    try {
      const r = await fetch(`${API}/vendor/diffusion/${vendorId}/${productId}/book`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ grid_id: option.id }),
      });
      const d = await r.json();
      if (r.ok) { toast.success(`Diffusion réservée (${option.label}) — solde : ${d.credits_left} cc`); refresh(); }
      else toast.error(d.detail || 'Erreur de réservation');
    } finally {
      setBooking('');
    }
  };

  if (!options.length) return null;

  return (
    <div className="mt-3 rounded-xl p-3" data-testid="spot-diffusion-section"
      style={{ background: 'rgba(217,179,90,0.07)', border: '1px solid rgba(217,179,90,0.3)' }}>
      <p className="text-xs font-semibold text-[#B8860B] flex items-center gap-1.5 mb-1">
        <CalendarClock size={13} /> Diffusion en galerie KDMARCHÉ
      </p>
      {current ? (
        <p className="text-[11px] text-emerald-700 mb-2" data-testid="spot-diffusion-status">
          ✓ Diffusion {current.status === 'ACTIVE' ? 'active' : 'programmée'} jusqu&apos;au{' '}
          {new Date(current.ends_at).toLocaleString('fr-FR')} — prolongez avec une option ci-dessous.
        </p>
      ) : (
        <p className="text-[11px] text-gray-500 mb-2" data-testid="spot-diffusion-status">
          Ce spot n&apos;est pas diffusé en galerie. Choisissez une durée (paiement en crédits coopératifs) :
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        {options.map((o) => (
          <button key={o.id} type="button" onClick={() => book(o)} disabled={!!booking}
            data-testid={`spot-diffusion-book-${o.id}`}
            className="h-8 px-3 rounded-lg text-xs font-medium border border-[#D9B35A]/50 text-[#B8860B] hover:bg-[#D9B35A]/10 inline-flex items-center gap-1.5 disabled:opacity-40">
            {booking === o.id ? <Loader2 size={11} className="animate-spin" /> : null}
            {o.label} · {o.price_credits} cc
          </button>
        ))}
      </div>
    </div>
  );
};
