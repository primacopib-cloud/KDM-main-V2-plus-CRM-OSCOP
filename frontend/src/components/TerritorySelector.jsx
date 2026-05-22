import React from 'react';
import { Globe2 } from 'lucide-react';

/**
 * Sélecteur de territoire DOM pour les vues admin / catalogue.
 * Persiste dans localStorage (`kdm_territory`) et émet `onChange(code|null)`.
 *
 * `territories` = [{code, name, center, zoom}, ...] (depuis /api/lolodrive/territories)
 */
export default function TerritorySelector({
  territories = [],
  value,
  onChange,
  showAll = true,
  className = '',
  testId = 'territory-selector',
}) {
  const handle = (code) => {
    if (code) {
      try { localStorage.setItem('kdm_territory', code); } catch (_) {}
    } else {
      try { localStorage.removeItem('kdm_territory'); } catch (_) {}
    }
    onChange?.(code);
  };

  return (
    <div className={`flex flex-wrap items-center gap-2 ${className}`} data-testid={testId}>
      <span className="text-xs text-white/40 inline-flex items-center gap-1.5 mr-1">
        <Globe2 className="w-3.5 h-3.5" /> Territoire
      </span>
      {showAll && (
        <button
          onClick={() => handle(null)}
          data-testid={`${testId}-all`}
          className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-all ${
            !value
              ? 'bg-[#D9B35A] text-black border-[#D9B35A]'
              : 'bg-white/[0.04] text-white/70 border-white/10 hover:bg-white/[0.08]'
          }`}
        >
          Tous
        </button>
      )}
      {territories.map((t) => (
        <button
          key={t.code}
          onClick={() => handle(t.code)}
          data-testid={`${testId}-${t.code}`}
          className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-all ${
            value === t.code
              ? 'bg-[#D9B35A] text-black border-[#D9B35A]'
              : 'bg-white/[0.04] text-white/70 border-white/10 hover:bg-white/[0.08]'
          }`}
        >
          {t.name}
        </button>
      ))}
    </div>
  );
}

export function getInitialTerritory() {
  try { return localStorage.getItem('kdm_territory'); } catch (_) { return null; }
}
