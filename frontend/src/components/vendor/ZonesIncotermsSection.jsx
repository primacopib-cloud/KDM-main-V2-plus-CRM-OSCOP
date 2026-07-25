import i18n from '@/i18n';
import { Lock, Ship } from 'lucide-react';
import { Button } from '../ui/button';
import { ZONES, INCOTERMS } from './vendorConstants';

// Section Zones de disponibilité + Incoterms par zone (formulaire produit vendeur)
export const ZonesIncotermsSection = ({ formData, allowance, isZoneLocked, handleZoneToggle, handleChange }) => {
  const toggleIncoterm = (zone, code) => {
    const current = formData.incoterms?.[zone] || [];
    const next = current.includes(code) ? current.filter((c) => c !== code) : [...current, code];
    const map = { ...(formData.incoterms || {}) };
    if (next.length) map[zone] = next; else delete map[zone];
    handleChange('incoterms', map);
  };

  return (
    <>
      {/* Zones */}
      <div className="space-y-4">
        <h3 className="font-semibold text-gray-900 flex items-center gap-2">
          {i18n.t('adm.zones_disponibilite_req')}
        </h3>
        {allowance && (
          <p className="text-xs text-gray-600" data-testid="zone-allowance-info">
            {formData.available_zones.length} / {allowance.count} zone(s) incluse(s) dans votre abonnement
            {' — '}
            <a href="/wallet" className="text-purple-600 underline" data-testid="zone-allowance-wallet-link">
              ajouter une zone additionnelle
            </a>
          </p>
        )}
        <div className="flex flex-wrap gap-2">
          {ZONES.map(zone => {
            const locked = isZoneLocked(zone);
            return (
              <Button
                key={zone}
                type="button"
                variant={formData.available_zones.includes(zone) ? "default" : "outline"}
                size="sm"
                onClick={() => handleZoneToggle(zone)}
                data-testid={`product-zone-${zone}`}
                className={
                  formData.available_zones.includes(zone)
                    ? "bg-purple-600 hover:bg-purple-700"
                    : locked ? "opacity-50 border-dashed" : ""
                }
              >
                {locked && <Lock className="w-3 h-3 mr-1" />}
                {zone}{locked ? ' — non incluse' : ''}
              </Button>
            );
          })}
        </div>
        {formData.available_zones.length === 0 && (
          <p className="text-sm text-red-500">{i18n.t('adm.selectionnez_au_moins_une_zone')}</p>
        )}
      </div>

      {/* Incoterms par zone */}
      {formData.available_zones.length > 0 && (
        <div className="space-y-3" data-testid="incoterms-section">
          <h3 className="font-semibold text-gray-900 flex items-center gap-2">
            <Ship className="w-4 h-4" /> Incoterms — conditions de livraison
          </h3>
          <p className="text-xs text-gray-600">
            Sélectionnez un ou plusieurs incoterms par zone (affichés aux acheteurs sur le catalogue). Optionnel.
          </p>
          <div className="space-y-2">
            {formData.available_zones.map((zone) => (
              <div key={zone} className="flex flex-wrap items-center gap-2 p-2 rounded-md border border-gray-200">
                <span className="text-xs font-bold w-28 shrink-0">{zone}</span>
                {INCOTERMS.map((inc) => {
                  const active = (formData.incoterms?.[zone] || []).includes(inc.code);
                  return (
                    <button
                      key={inc.code}
                      type="button"
                      title={inc.label}
                      onClick={() => toggleIncoterm(zone, inc.code)}
                      data-testid={`incoterm-${zone}-${inc.code}`}
                      className={`px-2.5 py-1 rounded-full text-xs font-semibold border transition-colors ${
                        active
                          ? 'bg-purple-600 text-white border-purple-600'
                          : 'bg-white text-gray-600 border-gray-300 hover:border-purple-400'
                      }`}
                    >
                      {inc.code}
                    </button>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  );
};
