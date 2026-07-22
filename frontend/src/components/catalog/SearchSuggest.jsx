import { useEffect, useRef, useState } from 'react';
import i18n from '@/i18n';
import { catalogAPI } from '../../services/api';

export const SearchSuggest = ({ term, onPick }) => {
  const [items, setItems] = useState([]);
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

  if (!items.length) return null;
  return (
    <div
      className="absolute top-full left-0 right-0 mt-1 z-30 rounded-xl border border-[#D9B35A]/30 bg-[#2A1045] shadow-xl overflow-hidden"
      data-testid="catalog-search-suggest"
    >
      {items.map((s) => (
        <button
          key={s.id} type="button" data-testid={`suggest-item-${s.id}`}
          onMouseDown={(e) => { e.preventDefault(); picked.current = s.label; setItems([]); onPick(s.label); }}
          className="w-full text-left px-3 py-2 text-sm text-white/85 hover:bg-white/[0.08] transition-colors"
        >
          {s.label}
        </button>
      ))}
    </div>
  );
};
