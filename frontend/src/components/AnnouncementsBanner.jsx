import { useEffect, useState } from 'react';
import { Megaphone, X } from 'lucide-react';
import { API } from '../services/http';

export const AnnouncementsBanner = ({ space = 'all' }) => {
  const [items, setItems] = useState([]);
  const [hidden, setHidden] = useState([]);

  useEffect(() => {
    fetch(`${API}/announcements?space=${space}`)
      .then((r) => (r.ok ? r.json() : { items: [] }))
      .then((d) => {
        const list = d.items || [];
        setItems(list);
        list.slice(0, 3).forEach((a) => fetch(`${API}/announcements/${a.id}/view`, { method: 'POST' }).catch(() => {}));
      })
      .catch(() => {});
  }, [space]);

  const visible = items.filter((a) => !hidden.includes(a.id)).slice(0, 3);
  if (!visible.length) return null;
  return (
    <div className="space-y-2 mb-4" data-testid="announcements-banner">
      {visible.map((a) => {
        const urgent = a.priority === 'urgente';
        return (
          <div key={a.id} className="rounded-xl p-3 flex items-start gap-3"
            data-testid={`announcement-${a.id}`}
            style={{ background: urgent ? 'rgba(230,68,50,0.12)' : 'rgba(217,179,90,0.10)',
                     border: `1px solid ${urgent ? 'rgba(230,68,50,0.45)' : 'rgba(217,179,90,0.35)'}` }}>
            <Megaphone className={`w-4 h-4 mt-0.5 shrink-0 ${urgent ? 'text-[#E64432]' : 'text-[#D9B35A]'}`} />
            <div className="flex-1 min-w-0">
              <p className="text-xs font-bold text-white flex items-center gap-2">
                {a.title}
                {urgent && <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-[#E64432]/20 text-[#E64432]">URGENTE</span>}
              </p>
              <p className="text-[11px] text-white/65 mt-0.5 whitespace-pre-wrap">{a.body}</p>
            </div>
            <button type="button" onClick={() => setHidden([...hidden, a.id])} className="text-white/40 hover:text-white/80">
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        );
      })}
    </div>
  );
};
