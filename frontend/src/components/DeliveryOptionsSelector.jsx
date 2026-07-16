import React, { useState, useEffect } from 'react';
import {
  Truck, MapPin, Package, Clock, ChevronRight, Check,
  Building2, AlertCircle, Phone, Calendar, Euro, Leaf, Route
} from 'lucide-react';
import { Button } from './ui/button';
import { Label } from './ui/label';
import { Input } from './ui/input';
import { RadioGroup, RadioGroupItem } from './ui/radio-group';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from './ui/select';
import { Checkbox } from './ui/checkbox';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Format currency
const formatCurrency = (cents) => {
  return new Intl.NumberFormat('fr-FR', {
    style: 'currency',
    currency: 'EUR'
  }).format(cents / 100);
};

export default function DeliveryOptionsSelector({
  zoneCode,
  weightKg,
  volumeM3,
  itemsCount,
  onOptionChange,
  initialOption = null
}) {
  const [deliveryType, setDeliveryType] = useState(initialOption?.type || 'EXW');
  const [pickupLocations, setPickupLocations] = useState([]);
  const [selectedPickup, setSelectedPickup] = useState(initialOption?.pickup_location_id || '');
  const [deliverySlots, setDeliverySlots] = useState([]);
  const [selectedSlot, setSelectedSlot] = useState(initialOption?.slot || 'AM');
  const [quote, setQuote] = useState(null);
  const [essQuote, setEssQuote] = useState(null);
  const [essDisclaimer, setEssDisclaimer] = useState(null);
  const [availableTours, setAvailableTours] = useState([]);
  const [selectedTour, setSelectedTour] = useState(initialOption?.tour_id || '');
  const [loadingQuote, setLoadingQuote] = useState(false);
  const [termsAccepted, setTermsAccepted] = useState(initialOption?.terms_accepted || false);
  const [essTermsAccepted, setEssTermsAccepted] = useState(initialOption?.ess_terms_accepted || false);
  
  // Delivery address fields
  const [deliveryAddress, setDeliveryAddress] = useState(initialOption?.delivery_address || {
    street: '',
    city: '',
    postal_code: '',
    contact_name: '',
    contact_phone: '',
    instructions: ''
  });

  // Load pickup locations
  useEffect(() => {
    const fetchPickupLocations = async () => {
      try {
        const response = await fetch(`${API_URL}/api/logiscop/pickup-locations?zone_code=${zoneCode}`);
        if (response.ok) {
          const data = await response.json();
          setPickupLocations(data);
          if (data.length > 0 && !selectedPickup) {
            setSelectedPickup(data[0].id);
          }
        }
      } catch (error) {
        console.error('Error fetching pickup locations:', error);
      }
    };
    
    if (zoneCode) {
      fetchPickupLocations();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [zoneCode]);

  // Load delivery slots
  useEffect(() => {
    const fetchSlots = async () => {
      try {
        const response = await fetch(`${API_URL}/api/logiscop/delivery-slots?zone_code=${zoneCode}`);
        if (response.ok) {
          const data = await response.json();
          setDeliverySlots(data.slots || []);
        }
      } catch (error) {
        console.error('Error fetching delivery slots:', error);
      }
    };
    fetchSlots();
  }, [zoneCode]);

  // Load ESS Route tours and disclaimer
  useEffect(() => {
    const fetchEssData = async () => {
      if (!zoneCode) return;
      
      try {
        // Fetch available tours
        const toursResponse = await fetch(`${API_URL}/api/ess/tours?zone_code=${zoneCode}&days_ahead=14`);
        if (toursResponse.ok) {
          const data = await toursResponse.json();
          setAvailableTours(data.tours || []);
          // Auto-select first available tour
          if (data.tours?.length > 0 && !selectedTour) {
            const openTours = data.tours.filter(t => t.status === 'open');
            if (openTours.length > 0) {
              setSelectedTour(openTours[0].tour_id);
            }
          }
        }
        
        // Fetch ESS disclaimer
        const disclaimerResponse = await fetch(`${API_URL}/api/ess/disclaimer`);
        if (disclaimerResponse.ok) {
          const data = await disclaimerResponse.json();
          setEssDisclaimer(data);
        }
      } catch (error) {
        console.error('Error fetching ESS data:', error);
      }
    };
    fetchEssData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [zoneCode]);

  // Calculate quote for delivery
  useEffect(() => {
    const fetchQuote = async () => {
      if (deliveryType !== 'DELIVERY' || !zoneCode || !weightKg) return;
      
      setLoadingQuote(true);
      try {
        const response = await fetch(`${API_URL}/api/logiscop/quote`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            zone_code: zoneCode,
            weight_kg: weightKg,
            volume_m3: volumeM3 || 0,
            items_count: itemsCount,
            delivery_type: 'standard',
            slot: selectedSlot
          })
        });
        
        if (response.ok) {
          const data = await response.json();
          setQuote(data);
        }
      } catch (error) {
        console.error('Error fetching quote:', error);
      } finally {
        setLoadingQuote(false);
      }
    };
    
    fetchQuote();
  }, [deliveryType, zoneCode, weightKg, volumeM3, itemsCount, selectedSlot]);

  // Calculate ESS Route quote
  useEffect(() => {
    const fetchEssQuote = async () => {
      if (deliveryType !== 'ESS_ROUTE' || !zoneCode || !weightKg) return;
      
      setLoadingQuote(true);
      try {
        const selectedTourData = availableTours.find(t => t.tour_id === selectedTour);
        const response = await fetch(`${API_URL}/api/ess/quote`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            zone_code: zoneCode,
            weight_kg: weightKg,
            cartons: itemsCount || 1,
            delivery_address: deliveryAddress,
            delivery_window: selectedTourData ? {
              start: selectedTourData.window_start,
              end: selectedTourData.window_end
            } : null,
            tour_id: selectedTour || null
          })
        });
        
        if (response.ok) {
          const data = await response.json();
          setEssQuote(data);
        }
      } catch (error) {
        console.error('Error fetching ESS quote:', error);
      } finally {
        setLoadingQuote(false);
      }
    };
    
    fetchEssQuote();
  }, [deliveryType, zoneCode, weightKg, itemsCount, selectedTour, deliveryAddress, availableTours]);

  // Notify parent of changes
  useEffect(() => {
    let optionLabel, optionDescription, activeQuote;
    
    if (deliveryType === 'EXW') {
      optionLabel = 'Retrait EXW LOGI\'SCOP';
      optionDescription = 'Retrait gratuit au point LOGI\'SCOP';
      activeQuote = null;
    } else if (deliveryType === 'ESS_ROUTE') {
      optionLabel = 'Tournées ESS (mutualisées)';
      optionDescription = essQuote 
        ? `Livraison mutualisée - ${formatCurrency(essQuote.total_ttc_cents)}`
        : 'Livraison mutualisée économique et écologique';
      activeQuote = essQuote;
    } else {
      optionLabel = 'Livraison LOGI\'SCOP';
      optionDescription = `Livraison à domicile - ${formatCurrency(quote?.total_ttc_cents || 0)}`;
      activeQuote = quote;
    }
    
    const option = {
      type: deliveryType,
      label: optionLabel,
      description: optionDescription,
      delivery_mode: deliveryType === 'ESS_ROUTE' ? 'ESS_ROUTE' : 'DIRECT',
      pickup_location_id: deliveryType === 'EXW' ? selectedPickup : null,
      delivery_address: deliveryType !== 'EXW' ? deliveryAddress : null,
      slot: deliveryType === 'DELIVERY' ? selectedSlot : null,
      tour_id: deliveryType === 'ESS_ROUTE' ? selectedTour : null,
      quote: activeQuote,
      terms_accepted: termsAccepted,
      ess_terms_accepted: deliveryType === 'ESS_ROUTE' ? essTermsAccepted : undefined
    };
    onOptionChange(option);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [deliveryType, selectedPickup, deliveryAddress, selectedSlot, selectedTour, quote, essQuote, termsAccepted, essTermsAccepted]);

  const selectedLocation = pickupLocations.find(loc => loc.id === selectedPickup);

  return (
    <div className="space-y-6">
      {/* Delivery Type Selection */}
      <div>
        <Label className="text-white mb-3 block">Mode de livraison</Label>
        <RadioGroup 
          value={deliveryType} 
          onValueChange={setDeliveryType}
          className="grid grid-cols-1 gap-4"
        >
          {/* EXW Option */}
          <label
            className={`relative flex flex-col p-4 rounded-xl border-2 cursor-pointer transition-all ${
              deliveryType === 'EXW'
                ? 'border-[#D4AF37] bg-[#D4AF37]/10'
                : 'border-white/10 bg-white/[0.02] hover:border-white/20'
            }`}
            data-testid="delivery-option-exw"
          >
            <RadioGroupItem value="EXW" className="sr-only" />
            <div className="flex items-start gap-3">
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                deliveryType === 'EXW' ? 'bg-[#D4AF37]/20' : 'bg-white/[0.06]'
              }`}>
                <MapPin className={`w-5 h-5 ${deliveryType === 'EXW' ? 'text-[#D4AF37]' : 'text-white/60'}`} />
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <span className={`font-semibold ${deliveryType === 'EXW' ? 'text-[#D4AF37]' : 'text-white'}`}>
                    Retrait EXW LOGI&apos;SCOP
                  </span>
                  <span className="text-[#D4AF37] font-bold">GRATUIT</span>
                </div>
                <p className="text-white/60 text-sm mt-1">
                  Retrait au point LOGI&apos;SCOP de votre zone
                </p>
              </div>
              {deliveryType === 'EXW' && (
                <Check className="w-5 h-5 text-[#D4AF37] absolute top-3 right-3" />
              )}
            </div>
          </label>

          {/* ESS Route Option (Tournées Mutualisées) */}
          <label
            className={`relative flex flex-col p-4 rounded-xl border-2 cursor-pointer transition-all ${
              deliveryType === 'ESS_ROUTE'
                ? 'border-[#10B981] bg-[#10B981]/10'
                : 'border-white/10 bg-white/[0.02] hover:border-white/20'
            }`}
            data-testid="delivery-option-ess-route"
          >
            <RadioGroupItem value="ESS_ROUTE" className="sr-only" />
            <div className="flex items-start gap-3">
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                deliveryType === 'ESS_ROUTE' ? 'bg-[#10B981]/20' : 'bg-white/[0.06]'
              }`}>
                <Route className={`w-5 h-5 ${deliveryType === 'ESS_ROUTE' ? 'text-[#10B981]' : 'text-white/60'}`} />
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <span className={`font-semibold ${deliveryType === 'ESS_ROUTE' ? 'text-[#10B981]' : 'text-white'}`}>
                    Tournées ESS (mutualisées)
                  </span>
                  <div className="flex items-center gap-2">
                    {essQuote?.savings_vs_standard_cents > 0 && (
                      <span className="text-xs bg-[#10B981]/20 text-[#10B981] px-2 py-0.5 rounded-full">
                        -{Math.round(essQuote.savings_vs_standard_cents / (essQuote.subtotal_ht_cents + essQuote.savings_vs_standard_cents) * 100)}%
                      </span>
                    )}
                    {essQuote && (
                      <span className="text-[#10B981] font-bold">
                        {formatCurrency(essQuote.total_ttc_cents)}
                      </span>
                    )}
                  </div>
                </div>
                <p className="text-white/60 text-sm mt-1">
                  Livraison économique et écologique via tournées planifiées
                </p>
                <div className="flex items-center gap-3 mt-2 text-xs text-white/50">
                  <span className="flex items-center gap-1"><Leaf className="w-3 h-3 text-[#10B981]" /> Éco-responsable</span>
                  <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> Fenêtre planifiée</span>
                </div>
              </div>
              {deliveryType === 'ESS_ROUTE' && (
                <Check className="w-5 h-5 text-[#10B981] absolute top-3 right-3" />
              )}
            </div>
          </label>

          {/* Standard Delivery Option */}
          <label
            className={`relative flex flex-col p-4 rounded-xl border-2 cursor-pointer transition-all ${
              deliveryType === 'DELIVERY'
                ? 'border-[#D9B35A] bg-[#D9B35A]/10'
                : 'border-white/10 bg-white/[0.02] hover:border-white/20'
            }`}
            data-testid="delivery-option-delivery"
          >
            <RadioGroupItem value="DELIVERY" className="sr-only" />
            <div className="flex items-start gap-3">
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                deliveryType === 'DELIVERY' ? 'bg-[#D9B35A]/20' : 'bg-white/[0.06]'
              }`}>
                <Truck className={`w-5 h-5 ${deliveryType === 'DELIVERY' ? 'text-[#D9B35A]' : 'text-white/60'}`} />
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <span className={`font-semibold ${deliveryType === 'DELIVERY' ? 'text-[#D9B35A]' : 'text-white'}`}>
                    Livraison LOGI&apos;SCOP (directe)
                  </span>
                  {quote && (
                    <span className="text-[#D9B35A] font-bold">
                      {formatCurrency(quote.total_ttc_cents)}
                    </span>
                  )}
                </div>
                <p className="text-white/60 text-sm mt-1">
                  Livraison à votre adresse - créneau à la carte
                </p>
              </div>
              {deliveryType === 'DELIVERY' && (
                <Check className="w-5 h-5 text-[#D9B35A] absolute top-3 right-3" />
              )}
            </div>
          </label>
        </RadioGroup>
      </div>

      {/* EXW - Pickup Location Selection */}
      {deliveryType === 'EXW' && pickupLocations.length > 0 && (
        <div className="p-4 rounded-xl bg-white/[0.02] border border-white/10">
          <Label className="text-white mb-3 block">Point de retrait</Label>
          <Select value={selectedPickup} onValueChange={setSelectedPickup}>
            <SelectTrigger className="bg-white/[0.04] border-white/10 text-white">
              <SelectValue placeholder="Sélectionner un point" />
            </SelectTrigger>
            <SelectContent>
              {pickupLocations.map(location => (
                <SelectItem key={location.id} value={location.id}>
                  {location.name} - {location.city}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {selectedLocation && (
            <div className="mt-4 p-3 rounded-lg bg-[#D4AF37]/10 border border-[#D4AF37]/20">
              <div className="flex items-start gap-3">
                <Building2 className="w-5 h-5 text-[#D4AF37] flex-shrink-0 mt-0.5" />
                <div className="text-sm">
                  <p className="font-semibold text-[#D4AF37]">{selectedLocation.name}</p>
                  <p className="text-white/70 mt-1">{selectedLocation.address}</p>
                  <p className="text-white/70">{selectedLocation.postal_code} {selectedLocation.city}</p>
                  {selectedLocation.phone && (
                    <p className="text-white/60 mt-2 flex items-center gap-1">
                      <Phone className="w-3 h-3" /> {selectedLocation.phone}
                    </p>
                  )}
                  <p className="text-white/60 flex items-center gap-1">
                    <Clock className="w-3 h-3" /> {selectedLocation.opening_hours}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

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
                      <span>{new Date(tour.date).toLocaleDateString('fr-FR', { weekday: 'short', day: 'numeric', month: 'short' })}</span>
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

      {/* Terms Acceptance */}
      <div className="flex items-start gap-3 p-4 rounded-xl bg-white/[0.02] border border-white/10">
        <Checkbox
          id="terms"
          checked={termsAccepted}
          onCheckedChange={setTermsAccepted}
          className="mt-1"
        />
        <label htmlFor="terms" className="text-sm text-white/70 cursor-pointer">
          J&apos;accepte les{' '}
          <a href="/legal/cg-oscop" target="_blank" className="text-[#D9B35A] hover:underline">
            Conditions Générales de Transport LOGI&apos;SCOP
          </a>
          {' '}et reconnais que les frais de transport sont facturés séparément par LOGI&apos;SCOP.
        </label>
      </div>

      {/* Info Banner */}
      <div className="flex items-start gap-3 p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
        <AlertCircle className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
        <div className="text-sm text-blue-300">
          <p className="font-medium">Facturation séparée</p>
          <p className="text-blue-300/70 mt-1">
            Les marchandises sont facturées par <strong>KDMARCHE</strong>. 
            {deliveryType === 'DELIVERY' && (
              <> Le transport est facturé séparément par <strong>LOGI&apos;SCOP</strong>.</>
            )}
          </p>
        </div>
      </div>
    </div>
  );
}
