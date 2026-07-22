import { useEffect, useRef, useState } from 'react';
import { Clock, X } from 'lucide-react';
import i18n from '@/i18n';
import { catalogAPI } from '../../services/api';

const RECENT_KEY = 'kdm_recent_searches';
const getRecents = () => {
  try { return JSON.parse(localStorage.getItem(RECENT_KEY) || '[]'); } catch { return []; }
};

export const addRecentSearch = (term) => {
  const t = (term || '').trim();
  if (t.length < 2) return;
  const list = [t, ...getRecents().filter((x) => x.toLowerCase() !== t.toLowerCase())].slice(0, 5);
  localStorage.setItem(RECENT_KEY, JSON.stringify(list));
};

const boxCls = 'absolute top-full left-0 right-0 mt-1 z-30 rounded-xl border border-[#D9B35A]/30 bg-[#2A1045] shadow-xl overflow-hidden';

export const SearchSuggest = ({ term, onPick, focused }) => {
  const [items, setItems] = useState([]);
  const [, setVersion] = useState(0);
  const picked = useRef('');

  useEffect(() => {
    const q = (term || '').trim();
    if (q.length < 2 || q === picked.current) { setItems([]); return undefined; }
    const t = setTimeout(() => {
      catalogAPI.suggest(q, (i18n.language || 'fr').slice(0, 2))
        .then((d) => setItems(d.suggestions || []))
        .catch(() => setItems([]));
    }, 250);
    return () => clearTimeout(t);
  }, [term]);

  const pick = (label) => {
    addRecentSearch(label);
    picked.current = label;
    setItems([]);
    setVersion((v) => v + 1);
    onPick(label);
  };

  const short = (term || '').trim().length < 2;
  const recents = short && focused ? getRecents() : [];

  if (short && focused && recents.length > 0) {
    return (
      <div className={boxCls} data-testid="catalog-recent-searches">
        <div className="flex items-center justify-between px-3 py-1.5 text-[10px] uppercase tracking-wide text-white/40">
          {i18n.t('catalog.recent_searches')}
          <button type="button" data-testid="recent-searches-clear" title="Effacer"
            onMouseDown={(e) => { e.preventDefault(); localStorage.removeItem(RECENT_KEY); setVersion((v) => v + 1); }}
            className="hover:text-white transition-colors">
            <X size={12} />
          </button>
        </div>
        {recents.map((r, i) => (
          <button key={r} type="button" data-testid={`recent-item-${i}`}
            onMouseDown={(e) => { e.preventDefault(); pick(r); }}
            className="w-full text-left px-3 py-2 text-sm text-white/85 hover:bg-white/[0.08] transition-colors flex items-center gap-2">
            <Clock size={12} className="text-[#D9B35A]/70" /> {r}
          </button>
        ))}
      </div>
    );
  }

  if (short || !items.length) return null;
  return (
    <div className={boxCls} data-testid="catalog-search-suggest">
      {items.map((s) => (
        <button
          key={s.id} type="button" data-testid={`suggest-item-${s.id}`}
          onMouseDown={(e) => { e.preventDefault(); pick(s.label); }}
          className="w-full text-left px-3 py-2 text-sm text-white/85 hover:bg-white/[0.08] transition-colors"
        >
          {s.label}
        </button>
      ))}
    </div>
  );
};
