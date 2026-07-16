import {
  Calendar, Check, Clock, CreditCard, Loader2, MapPin,
} from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Checkbox } from '../ui/checkbox';
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '../ui/dialog';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../ui/select';
import { formatPrice, MIN_INSTALLMENT_CENTS } from './catalogUtils';


export const CheckoutDialog = ({
  cart, cartItemCount, cartTotal, checkoutOpen, setCheckoutOpen,
  pickupLocations, selectedPickup, setSelectedPickup, orderNotes, setOrderNotes,
  submittingOrder, handleSubmitOrder, useInstallment, setUseInstallment,
  installmentPlan, installmentLoading,
}) => (
      <Dialog open={checkoutOpen} onOpenChange={setCheckoutOpen}>
        <DialogContent className="bg-[#0a0d14] border-white/10 text-white sm:max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Finaliser la commande</DialogTitle>
            <DialogDescription className="text-white/60">
              Commande EXW - Enlèvement à votre charge
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            {/* Order summary */}
            <div className="p-4 rounded-xl bg-white/[0.04] border border-white/[0.08]">
              <p className="text-sm text-white/60 mb-2">Récapitulatif</p>
              <div className="flex justify-between items-center">
                <span>{cartItemCount} article{cartItemCount > 1 ? 's' : ''}</span>
                <span className="font-bold text-[#D9B35A]">{formatPrice(cartTotal)} HT</span>
              </div>
            </div>
            
            {/* Installment Payment Option */}
            {cartTotal >= MIN_INSTALLMENT_CENTS && (
              <div className={`p-4 rounded-xl border transition-all ${
                useInstallment 
                  ? 'bg-purple-500/10 border-purple-500/30' 
                  : 'bg-white/[0.02] border-white/[0.08]'
              }`}>
                <div className="flex items-start gap-3">
                  <Checkbox 
                    id="installment"
                    checked={useInstallment}
                    onCheckedChange={setUseInstallment}
                    className="mt-1 border-white/30 data-[state=checked]:bg-purple-500 data-[state=checked]:border-purple-500"
                  />
                  <div className="flex-1">
                    <Label htmlFor="installment" className="font-medium cursor-pointer flex items-center gap-2">
                      <Calendar className="w-4 h-4 text-purple-400" />
                      Paiement en 4× sans frais cachés
                    </Label>
                    <p className="text-xs text-white/50 mt-1">
                      À partir de 5 500€ HT. Frais: 20% HT + TVA 8,50%
                    </p>
                    
                    {installmentLoading && (
                      <div className="flex items-center gap-2 mt-3">
                        <Loader2 className="w-4 h-4 animate-spin text-purple-400" />
                        <span className="text-xs text-white/50">Calcul en cours...</span>
                      </div>
                    )}
                    
                    {useInstallment && installmentPlan && !installmentLoading && (
                      <div className="mt-3 pt-3 border-t border-white/[0.08] space-y-2">
                        <div className="grid grid-cols-2 gap-2 text-xs">
                          <div>
                            <span className="text-white/50">Montant HT</span>
                            <p className="font-medium">{installmentPlan.subtotal_ht_eur?.toFixed(2)}€</p>
                          </div>
                          <div>
                            <span className="text-white/50">TVA produits (8,50%)</span>
                            <p className="font-medium">{installmentPlan.product_tva_eur?.toFixed(2)}€</p>
                          </div>
                          <div>
                            <span className="text-white/50">Frais échelonnement (20%)</span>
                            <p className="font-medium">{installmentPlan.fees_ht_eur?.toFixed(2)}€</p>
                          </div>
                          <div>
                            <span className="text-white/50">TVA frais (8,50%)</span>
                            <p className="font-medium">{installmentPlan.fees_tva_eur?.toFixed(2)}€</p>
                          </div>
                        </div>
                        
                        <div className="pt-2 border-t border-white/[0.08]">
                          <div className="flex justify-between items-center mb-2">
                            <span className="text-sm font-medium text-purple-400">Total à payer en 4×</span>
                            <span className="text-lg font-bold text-purple-400">
                              {installmentPlan.total_with_fees_eur?.toFixed(2)}€
                            </span>
                          </div>
                          
                          <div className="space-y-1">
                            {installmentPlan.installments?.map((inst, idx) => (
                              <div key={idx} className="flex justify-between items-center text-xs bg-white/[0.02] p-2 rounded">
                                <span className="text-white/60">
                                  <Clock className="w-3 h-3 inline mr-1" />
                                  {inst.label}
                                </span>
                                <span className="font-medium">{inst.amount_eur?.toFixed(2)}€</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
            
            {/* Under minimum amount notice */}
            {cartTotal > 0 && cartTotal < MIN_INSTALLMENT_CENTS && (
              <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.08]">
                <p className="text-xs text-white/50">
                  <Calendar className="w-3 h-3 inline mr-1" />
                  Paiement en 4× disponible à partir de 5 500€ HT 
                  <span className="text-white/30 ml-1">
                    (il vous manque {formatPrice(MIN_INSTALLMENT_CENTS - cartTotal)})
                  </span>
                </p>
              </div>
            )}
            
            {/* Pickup location selector */}
            <div className="space-y-2">
              <label className="text-sm font-medium">Point d'enlèvement (EXW) *</label>
              <Select value={selectedPickup} onValueChange={setSelectedPickup}>
                <SelectTrigger className="w-full bg-white/[0.04] border-white/10">
                  <SelectValue placeholder="Sélectionner un point" />
                </SelectTrigger>
                <SelectContent>
                  {pickupLocations.map(loc => (
                    <SelectItem key={loc.id} value={loc.id}>
                      <div className="flex items-center gap-2">
                        <MapPin className="w-4 h-4 text-[#D4AF37]" />
                        <span>{loc.name} - {loc.city}</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {pickupLocations.find(l => l.id === selectedPickup) && (
                <p className="text-xs text-white/50">
                  {pickupLocations.find(l => l.id === selectedPickup)?.address}
                </p>
              )}
            </div>
            
            {/* Notes */}
            <div className="space-y-2">
              <label className="text-sm font-medium">Notes (optionnel)</label>
              <Input
                placeholder="Instructions particulières..."
                value={orderNotes}
                onChange={(e) => setOrderNotes(e.target.value)}
                className="bg-white/[0.04] border-white/10"
              />
            </div>
            
            {/* EXW Warning */}
            <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
              <p className="text-xs text-amber-400">
                <strong>Incoterm EXW :</strong> L'enlèvement, le transport et les formalités sont à votre charge.
              </p>
            </div>
          </div>
          
          <DialogFooter className="flex gap-3">
            <Button variant="outline" onClick={() => setCheckoutOpen(false)} className="border-white/10">
              Annuler
            </Button>
            <Button 
              onClick={handleSubmitOrder}
              disabled={!selectedPickup || submittingOrder}
              className={useInstallment ? "bg-purple-600 hover:bg-purple-700 text-white" : "bg-[#D9B35A] hover:bg-[#c9a34a] text-black"}
              data-testid="confirm-order-button"
            >
              {submittingOrder ? (
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
              ) : useInstallment ? (
                <Calendar className="w-4 h-4 mr-2" />
              ) : (
                <Check className="w-4 h-4 mr-2" />
              )}
              {useInstallment ? 'Commander en 4×' : 'Confirmer la commande'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
);
