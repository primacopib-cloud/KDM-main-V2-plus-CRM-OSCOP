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

export const StandardDeliverySection = ({
  deliveryType, quote, deliverySlots, selectedSlot, setSelectedSlot,
  deliveryAddress, setDeliveryAddress,
}) => (
  <>
      {/* DELIVERY - Address & Slot Selection */}
      {deliveryType === 'DELIVERY' && (
        <div className="space-y-4">
          {/* Quote Details */}
          {quote && (
            <div className="p-4 rounded-xl bg-[#D9B35A]/10 border border-[#D9B35A]/20">
              <h4 className="text-[#D9B35A] font-semibold mb-3 flex items-center gap-2">
                <Euro className="w-4 h-4" />
                Détail du tarif transport
              </h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between text-white/70">
                  <span>Base transport ({quote.zone_name})</span>
                  <span>{formatCurrency(quote.transport_base_cents)}</span>
                </div>
                <div className="flex justify-between text-white/70">
                  <span>Transport poids ({weightKg}kg)</span>
                  <span>{formatCurrency(quote.transport_weight_cents)}</span>
                </div>
                {quote.transport_volume_cents > 0 && (
                  <div className="flex justify-between text-white/70">
                    <span>Transport volume ({volumeM3}m³)</span>
                    <span>{formatCurrency(quote.transport_volume_cents)}</span>
                  </div>
                )}
                <div className="flex justify-between text-white/70">
                  <span>Préparation ({itemsCount} ligne(s))</span>
                  <span>{formatCurrency(quote.preparation_fees_cents)}</span>
                </div>
                {quote.slot_supplement_cents > 0 && (
                  <div className="flex justify-between text-white/70">
                    <span>Supplément créneau</span>
                    <span>{formatCurrency(quote.slot_supplement_cents)}</span>
                  </div>
                )}
                <div className="border-t border-white/10 pt-2 mt-2">
                  <div className="flex justify-between text-white/70">
                    <span>Sous-total HT</span>
                    <span>{formatCurrency(quote.subtotal_ht_cents)}</span>
                  </div>
                  <div className="flex justify-between text-white/70">
                    <span>TVA ({quote.tva_rate}%)</span>
                    <span>{formatCurrency(quote.tva_cents)}</span>
                  </div>
                  <div className="flex justify-between font-bold text-[#D9B35A] mt-1">
                    <span>Total TTC</span>
                    <span>{formatCurrency(quote.total_ttc_cents)}</span>
                  </div>
                </div>
                <p className="text-white/50 text-xs mt-2">
                  Facturé par: {quote.billing_entity} • {quote.estimated_delivery}
                </p>
              </div>
            </div>
          )}

          {/* Delivery Slot */}
          <div>
            <Label className="text-white mb-2 block">Créneau de livraison</Label>
            <Select value={selectedSlot} onValueChange={setSelectedSlot}>
              <SelectTrigger className="bg-white/[0.04] border-white/10 text-white">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {deliverySlots.map(slot => (
                  <SelectItem key={slot.id} value={slot.id}>
                    {slot.label} {slot.supplement_cents > 0 && `(+${formatCurrency(slot.supplement_cents)})`}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Delivery Address */}
          <div className="p-4 rounded-xl bg-white/[0.02] border border-white/10 space-y-4">
            <h4 className="text-white font-semibold flex items-center gap-2">
              <MapPin className="w-4 h-4 text-[#D9B35A]" />
              Adresse de livraison
            </h4>
            
            <div>
              <Label className="text-white/60 text-sm">Adresse</Label>
              <Input
                value={deliveryAddress.street}
                onChange={e => setDeliveryAddress({...deliveryAddress, street: e.target.value})}
                placeholder="Numéro et rue"
                className="mt-1 bg-white/[0.04] border-white/10 text-white"
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
                />
              </div>
              <div>
                <Label className="text-white/60 text-sm">Ville</Label>
                <Input
                  value={deliveryAddress.city}
                  onChange={e => setDeliveryAddress({...deliveryAddress, city: e.target.value})}
                  placeholder="Ville"
                  className="mt-1 bg-white/[0.04] border-white/10 text-white"
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
                />
              </div>
              <div>
                <Label className="text-white/60 text-sm">Téléphone</Label>
                <Input
                  value={deliveryAddress.contact_phone}
                  onChange={e => setDeliveryAddress({...deliveryAddress, contact_phone: e.target.value})}
                  placeholder="06XX XX XX XX"
                  className="mt-1 bg-white/[0.04] border-white/10 text-white"
                />
              </div>
            </div>
            
            <div>
              <Label className="text-white/60 text-sm">Instructions de livraison (optionnel)</Label>
              <Input
                value={deliveryAddress.instructions}
                onChange={e => setDeliveryAddress({...deliveryAddress, instructions: e.target.value})}
                placeholder="Code portail, étage, etc."
                className="mt-1 bg-white/[0.04] border-white/10 text-white"
              />
            </div>
          </div>
        </div>
      )}

  </>
);
