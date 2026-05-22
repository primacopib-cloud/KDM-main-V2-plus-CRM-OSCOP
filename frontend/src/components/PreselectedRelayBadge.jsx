import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { MapPin, X, Edit3 } from 'lucide-react';

/**
 * Badge "Relais sélectionné" — preuve de conversion visible.
 *
 * Affiche le relais pré-sélectionné lu depuis localStorage `kdm_preselected_point`
 * avec deux actions : modifier (retour à la carte) ou supprimer (clear localStorage).
 *
 * Si aucun relais pré-sélectionné, le composant ne rend rien (return null).
 *
 * Props:
 *   - className: classes Tailwind additionnelles
 *   - testId: data-testid (default 'preselected-relay-badge')
 *   - onClear: callback appelé après suppression (utile pour ré-render parent)
 */
export default function PreselectedRelayBadge({ className = '', testId = 'preselected-relay-badge', onClear }) {
  const [point, setPoint] = useState(null);

  useEffect(() => {
    try {
      const raw = localStorage.getItem('kdm_preselected_point');
      if (raw) setPoint(JSON.parse(raw));
    } catch (_) {
      setPoint(null);
    }
  }, []);

  if (!point) return null;

  const clear = () => {
    try { localStorage.removeItem('kdm_preselected_point'); } catch (_) {}
    setPoint(null);
    onClear?.();
  };

  return (
    <div
      data-testid={testId}
      className={`flex items-center gap-3 rounded-[14px] px-4 py-3 border border-or-metallise/30 ${className}`}
      style={{ background: 'linear-gradient(90deg, rgba(212,175,55,0.10), rgba(108,76,142,0.10))' }}
    >
      <div className="rounded-full p-2 flex-shrink-0" style={{ background: 'rgba(212,175,55,0.18)' }}>
        <MapPin className="w-4 h-4 text-or-metallise" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-[10px] uppercase tracking-wider text-or-metallise font-semibold">Relais sélectionné</div>
        <div className="text-sm font-medium truncate" data-testid={`${testId}-name`}>{point.name || point.code}</div>
        <div className="text-[11px] text-white/40 font-mono">{point.code} · {point.territory}</div>
      </div>
      <Link to="/#reseau-lolodrive" className="text-xs text-violet-premium hover:text-or-metallise inline-flex items-center gap-1 px-2 py-1 rounded-md hover:bg-white/[0.04] transition-colors" data-testid={`${testId}-edit`}>
        <Edit3 className="w-3 h-3" /> Modifier
      </Link>
      <button
        type="button"
        onClick={clear}
        data-testid={`${testId}-clear`}
        className="text-white/40 hover:text-rose-magenta hover:bg-white/[0.06] rounded-md p-1.5 transition-colors"
        aria-label="Retirer la sélection"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}
