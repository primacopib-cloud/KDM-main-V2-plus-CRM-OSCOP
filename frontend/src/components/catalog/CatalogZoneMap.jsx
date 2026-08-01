import { useState } from 'react';
import { Map, ChevronDown, ChevronUp } from 'lucide-react';
import i18n from '@/i18n';
import { TerritoryMap } from '../landing/TerritoryMap';

// Sélecteur de zone par carte interactive (catalogue), repliable
export const CatalogZoneMap = ({ selectedZone, onZoneSelect }) => {
  const [open, setOpen] = useState(false);
  return (
    <div className="mb-6">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        data-testid="catalog-map-toggle"
        className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium border transition-all ${
          open
            ? 'bg-[#D9B35A]/20 text-[#D9B35A] border-[#D9B35A]/30'
            : 'bg-white/[0.04] text-white/60 hover:text-white border-white/[0.08]'
        }`}
      >
        <Map className="w-4 h-4" />
        {i18n.t('catalog.choisir_zone_carte', 'Choisir ma zone sur la carte')}
        {open ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
      </button>
      {open && (
        <div className="mt-4">
          <TerritoryMap zone={selectedZone === 'ALL' ? '' : selectedZone}
            onSelect={(c) => onZoneSelect(c || 'ALL')} showAll />
        </div>
      )}
    </div>
  );
};
