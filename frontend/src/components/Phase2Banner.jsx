import React from 'react';
import { Link } from 'react-router-dom';
import { Construction, ArrowRight } from 'lucide-react';

/**
 * Banner indicating this module is a Phase 2 light version,
 * displayed below the main page title.
 */
export default function Phase2Banner({ module }) {
  return (
    <div
      data-testid="phase2-banner"
      className="mb-6 rounded-2xl border border-amber-400/30 bg-amber-400/[0.04] p-4 flex flex-wrap items-center gap-3"
    >
      <Construction className="w-5 h-5 text-amber-400 shrink-0" />
      <div className="flex-1 min-w-0 text-xs sm:text-sm">
        <div className="font-semibold text-amber-300">
          {module} — Version Phase 2 légère
        </div>
        <div className="text-white/50 text-xs">
          MVP itération 1 : lecture + CRUD basique. Itération 2 ajoutera workflows complets,
          notifications dédiées et reporting avancé.
        </div>
      </div>
      <Link
        to="/lolodrive"
        className="text-xs text-amber-300 hover:text-amber-200 flex items-center gap-1 shrink-0"
      >
        Dashboard <ArrowRight className="w-3 h-3" />
      </Link>
    </div>
  );
}
