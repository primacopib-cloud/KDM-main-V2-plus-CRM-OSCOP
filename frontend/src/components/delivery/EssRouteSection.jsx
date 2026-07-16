import i18n from '@/i18n';
import React from 'react';
import {
  Truck, MapPin, Package, Clock, ChevronRight, Check,
  Building2, AlertCircle, Phone, Calendar, Euro, Leaf, Route
} from 'lucide-react';
import { Label } from '../ui/label';
import { Input } from '../ui/input';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '../ui/select';
import { Checkbox } from '../ui/checkbox';
import { formatCurrency } from './deliveryUtils';

export const EssRouteSection = ({
  deliveryType, essQuote, essDisclaimer, availableTours, selectedTour, setSelectedTour,
  deliveryAddress, setDeliveryAddress, essTermsAccepted, setEssTermsAccepted,
}) => (
  <>
      {/* ESS ROUTE - Tour Selection & Address */}
      {deliveryType === 'ESS_ROUTE' && (
        <div className="space-y-4">
          {/* ESS Quote Details */}
          {essQuote && (
            <div className="p-4 rounded-xl bg-[#10B981]/10 border border-[#10B981]/20">
              <h4 className="text-[#10B981] font-semibold mb-3 flex items-center gap-2">
                <Route className="w-4 h-4" />
                Détail tarif Tournées ESS
              </h4>
              <div className="space-y-2 text-sm">
                {essQuote.lines?.map((line, idx) => (
                  <div key={idx} className="flex justify-between text-white/70">
                    <span>{line.label}</span>
                    <span>{formatCurrency(line.amount_ht_cents)}</span>
                  </div>
                ))}
                <div className="border-t border-white/10 pt-2 mt-2">
                  <div className="flex justify-between text-white/70">
                    <span>Sous-total HT</span>
                    <span>{formatCurrency(essQuote.subtotal_ht_cents)}</span>
                  </div>
                  <div className="flex justify-between text-white/70">
                    <span>TVA ({essQuote.vat_rate}%)</span>
                    <span>{formatCurrency(essQuote.vat_cents)}</span>
                  </div>
                  <div className="flex justify-between font-bold text-[#10B981] mt-1">
                    <span>Total TTC</span>
                    <span>{formatCurrency(essQuote.total_ttc_cents)}</span>
                  </div>
                </div>
                
                {/* ESS Benefits */}
                <div className="flex items-center gap-4 pt-2 mt-2 border-t border-white/10">
                  {essQuote.savings_vs_standard_cents > 0 && (
                    <span className="text-xs bg-[#10B981]/20 text-[#10B981] px-2 py-1 rounded">
                      Économie: {formatCurrency(essQuote.savings_vs_standard_cents)}
                    </span>
                  )}
                  <span className="text-xs text-white/50 flex items-center gap-1">
                    <Leaf className="w-3 h-3" /> {essQuote.eco_benefit}
                  </span>
                </div>
                
                <p className="text-white/50 text-xs mt-2">
                  Devis: {essQuote.quote_id} • {essQuote.estimated_delivery}
                </p>
              </div>
            </div>
          )}

          {/* Tour Selection */}
          <div>
            <Label className="text-white mb-2 block">Tournée de livraison</Label>
            <Select value={selectedTour} onValueChange={setSelectedTour}>
              <SelectTrigger className="bg-white/[0.04] border-white/10 text-white" data-testid="ess-tour-select">
                <SelectValue placeholder="Sélectionner une tournée" />
              </SelectTrigger>
              <SelectContent>
                {availableTours.filter(t => t.status === 'open').map(tour => (
                  <SelectItem key={tour.tour_id} value={tour.tour_id}>
                    <div className="flex items-center gap-2">
                      <span>{new Date(tour.date).toLocaleDateString(i18n.language, { weekday: 'short', day: 'numeric', month: 'short' })}</span>
                      <span className="text-white/50">•</span>
                      <span>{tour.window_start}-{tour.window_end}</span>
                      <span className="text-xs text-white/40">({tour.available} places)</span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            
            {availableTours.length === 0 && (
              <p className="text-white/50 text-sm mt-2">
                Aucune tournée disponible pour cette zone actuellement.
              </p>
            )}
          </div>

          {/* ESS Delivery Address */}
          <div className="p-4 rounded-xl bg-white/[0.02] border border-white/10 space-y-4">
            <h4 className="text-white font-semibold flex items-center gap-2">
              <MapPin className="w-4 h-4 text-[#10B981]" />
              Adresse de livraison (Tournée ESS)
            </h4>
            
            <div>
              <Label className="text-white/60 text-sm">Adresse</Label>
              <Input
                value={deliveryAddress.street}
                onChange={e => setDeliveryAddress({...deliveryAddress, street: e.target.value})}
                placeholder="Numéro et rue"
                className="mt-1 bg-white/[0.04] border-white/10 text-white"
                data-testid="ess-address-street"
              />
            </div>
            
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-white/60 text-sm">Code postal</Label>
                <Input
                  value={deliveryAddress.postal_code}
                  onChange={e => setDeliveryAddress({...deliveryAddress, postal_code: e.target.value})}
                  placeholder="97XXX"
                  className="mt-1 bg-white/[0.04] border-white/10 text-white"
                  data-testid="ess-address-postal"
                />
              </div>
              <div>
                <Label className="text-white/60 text-sm">Ville</Label>
                <Input
                  value={deliveryAddress.city}
                  onChange={e => setDeliveryAddress({...deliveryAddress, city: e.target.value})}
                  placeholder="Ville"
                  className="mt-1 bg-white/[0.04] border-white/10 text-white"
                  data-testid="ess-address-city"
                />
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-white/60 text-sm">Nom du contact</Label>
                <Input
                  value={deliveryAddress.contact_name}
                  onChange={e => setDeliveryAddress({...deliveryAddress, contact_name: e.target.value})}
                  placeholder="Nom complet"
                  className="mt-1 bg-white/[0.04] border-white/10 text-white"
                  data-testid="ess-contact-name"
                />
              </div>
              <div>
                <Label className="text-white/60 text-sm">Téléphone</Label>
                <Input
                  value={deliveryAddress.contact_phone}
                  onChange={e => setDeliveryAddress({...deliveryAddress, contact_phone: e.target.value})}
                  placeholder="06XX XX XX XX"
                  className="mt-1 bg-white/[0.04] border-white/10 text-white"
                  data-testid="ess-contact-phone"
                />
              </div>
            </div>
          </div>

          {/* ESS Terms Acceptance */}
          <div className="flex items-start gap-3 p-4 rounded-xl bg-[#10B981]/5 border border-[#10B981]/20">
            <Checkbox
              id="ess-terms"
              checked={essTermsAccepted}
              onCheckedChange={setEssTermsAccepted}
              className="mt-1"
              data-testid="ess-terms-checkbox"
            />
            <label htmlFor="ess-terms" className="text-sm text-white/70 cursor-pointer">
              {essDisclaimer?.short || "La livraison en Tournées ESS est une tournée mutualisée planifiée, destinée à réduire les coûts et l'empreinte carbone. Elle implique une fenêtre de livraison et des règles d'accès équitables et traçables."}
              {' '}
              <a href="/legal/annexe-ess-route" target="_blank" className="text-[#10B981] hover:underline">
                Voir l&apos;annexe complète
              </a>
            </label>
          </div>
        </div>
      )}

  </>
);
