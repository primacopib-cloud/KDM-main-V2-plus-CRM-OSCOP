import { useEffect, useState } from 'react';
import { BellRing } from 'lucide-react';
import { toast } from 'sonner';
import i18n from '@/i18n';
import { API, getAuthHeaders } from '../../services/http';

const EVENTS = ['auction_new_live', 'auction_ending'];
const VALUES = ['both', 'inapp', 'email', 'none'];

// Choix des canaux (cloche/email) pour les alertes nouveau lot et fin imminente
export const AuctionAlertPrefs = () => {
  const [prefs, setPrefs] = useState(null);

  useEffect(() => {
    fetch(`${API}/prefs/notifications`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => d && setPrefs(d.prefs))
      .catch(() => {});
  }, []);

  const save = async (event, value) => {
    const next = { ...prefs, [event]: value };
    setPrefs(next);
    const res = await fetch(`${API}/prefs/notifications`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      credentials: 'include', body: JSON.stringify({ prefs: { [event]: value } }),
    });
    if (res.ok) toast.success('✓');
    else toast.error('Erreur');
  };

  if (!prefs) return null;
  return (
    <div className="mb-5 rounded-2xl bg-white/[0.04] border border-white/10 p-4" data-testid="auction-alert-prefs">
      <p className="text-xs font-bold text-[#E9CF8E] flex items-center gap-1.5 mb-3">
        <BellRing className="w-3.5 h-3.5" /> {i18n.t('auction.prefs_title')}
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        {EVENTS.map((ev) => (
          <div key={ev} className="flex flex-wrap items-center gap-2" data-testid={`alert-pref-row-${ev}`}>
            <span className="text-xs text-white/75 w-full sm:w-auto sm:min-w-[130px]">
              {i18n.t(`auction.prefs_${ev}`)}
            </span>
            <div className="flex gap-1">
              {VALUES.map((v) => (
                <button key={v} type="button" onClick={() => save(ev, v)}
                  data-testid={`alert-pref-${ev}-${v}`}
                  className={`px-2.5 py-1 rounded-full text-[11px] font-semibold border transition-colors ${
                    (prefs[ev] || 'both') === v
                      ? 'bg-[#D9B35A] text-[#2A1045] on-gold border-[#D9B35A]'
                      : 'bg-white/[0.05] text-white/65 border-white/15 hover:bg-white/10'}`}>
                  {i18n.t(`auction.prefs_val_${v}`)}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
