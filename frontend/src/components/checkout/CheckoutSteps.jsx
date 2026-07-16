import React from 'react';
import { Link } from 'react-router-dom';
import {
  Package, MapPin, CreditCard, FileText, CheckCircle2, ArrowLeft,
  Truck, Calendar, Building2, RefreshCw, Shield, FileSignature, ChevronRight,
  Download, Loader2, Lock, AlertCircle
} from 'lucide-react';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Checkbox } from '../ui/checkbox';
import { Label } from '../ui/label';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '../ui/select';
import DynamicOrderForm from '../DynamicOrderForm';
import DeliveryOptionsSelector from '../DeliveryOptionsSelector';
import { formatCurrency } from './checkoutUtils';

export const ReviewStep = ({ currentStep, cart }) => (
  <>
            {/* Step 0: Review - Cart Summary */}
            {currentStep === 0 && (
              <div className="glass-panel-soft rounded-[18px] p-6">
                <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                  <Package className="w-5 h-5 text-[#D9B35A]" />
                  Récapitulatif de la commande
                </h3>
                
                {/* Cart Items */}
                <div className="space-y-3 mb-6">
                  {cart?.items?.map((item, index) => (
                    <div 
                      key={index}
                      className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] border border-white/[0.05]"
                    >
                      <div>
                        <p className="text-white font-medium">{item.product_name}</p>
                        <p className="text-xs text-white/50">SKU: {item.product_sku}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-white">{item.quantity} x {formatCurrency(item.price_ht_cents)}</p>
                        <p className="text-[#D9B35A] font-semibold">{formatCurrency(item.line_total_ht_cents)}</p>
                      </div>
                    </div>
                  ))}
                </div>
                
                <div className="border-t border-white/10 pt-4">
                  <div className="flex justify-between text-white/70 mb-2">
                    <span>Sous-total produits HT</span>
                    <span>{formatCurrency(cart?.subtotal_ht_cents || 0)}</span>
                  </div>
                  <div className="flex justify-between text-white font-semibold">
                    <span>Total articles</span>
                    <span>{cart?.items?.reduce((sum, i) => sum + i.quantity, 0) || 0}</span>
                  </div>
                </div>
              </div>
            )}
  </>
);

export const DeliveryStep = ({ currentStep, cart, zones, selectedZone, setSelectedZone, deliveryOption, setDeliveryOption, transportContractAccepted, setTransportContractAccepted }) => (
  <>
            {/* Step 1: Delivery Options */}
            {currentStep === 1 && (
              <div className="glass-panel-soft rounded-[18px] p-6">
                <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                  <Truck className="w-5 h-5 text-[#D4AF37]" />
                  Mode de livraison LOGI'SCOP
                </h3>
                
                {/* Zone Selection */}
                <div className="mb-6">
                  <Label className="text-white/70 mb-2 block">Zone géographique</Label>
                  <Select value={selectedZone} onValueChange={setSelectedZone}>
                    <SelectTrigger className="bg-white/[0.04] border-white/10">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {zones.map(z => (
                        <SelectItem key={z.code} value={z.code}>{z.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                
                {/* Delivery Options Selector */}
                <DeliveryOptionsSelector
                  zoneCode={selectedZone}
                  weightKg={cart?.total_weight_kg || 10}
                  volumeM3={cart?.total_volume_m3 || 0.1}
                  itemsCount={cart?.items?.length || 1}
                  onOptionChange={setDeliveryOption}
                  initialOption={deliveryOption}
                />

                {/* Transport Contract Acceptance (if LOGI'SCOP delivery) */}
                {deliveryOption?.mode === 'DELIVERY' && (
                  <div className="mt-6 p-5 rounded-xl bg-amber-500/5 border border-amber-500/20">
                    <div className="flex items-start gap-3">
                      <Checkbox
                        id="transport-contract"
                        checked={transportContractAccepted}
                        onCheckedChange={setTransportContractAccepted}
                        className="mt-1 border-amber-500/40 data-[state=checked]:bg-amber-500 data-[state=checked]:border-amber-500"
                        data-testid="transport-contract-checkbox"
                      />
                      <div className="flex-1">
                        <Label 
                          htmlFor="transport-contract" 
                          className="text-sm text-white/90 font-medium cursor-pointer leading-relaxed"
                        >
                          J'ai lu et j'accepte le{' '}
                          <Link 
                            to="/legal/contrat-transport" 
                            target="_blank"
                            className="text-amber-400 hover:text-amber-300 underline underline-offset-2"
                          >
                            Contrat de Transport LOGI'SCOP
                          </Link>
                        </Label>
                        <p className="text-xs text-white/50 mt-2 leading-relaxed">
                          La livraison LOGI'SCOP est une prestation de transport indépendante, 
                          distincte de la vente des marchandises, exécutée par un opérateur logistique ESS.
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
  </>
);

export const PreparationStep = ({ currentStep, user, products, selectedZone, handleTotalsChange, handlePreparationChange }) => (
  <>
            {/* Step 2: Preparation Options */}
            {currentStep === 2 && (
              <DynamicOrderForm
                products={products}
                zoneCode={selectedZone}
                orderData={{
                  CLIENT_LEGAL_NAME: user?.company_name || 'Organisation',
                  CLIENT_ADDRESS: user?.address || '',
                  CLIENT_SIRET: user?.siret || '',
                  CLIENT_CONTACT: user?.contact_name || user?.email || ''
                }}
                showStamp={false}
                onTotalsChange={handleTotalsChange}
                onPreparationChange={handlePreparationChange}
              />
            )}
  </>
);

export const SignatureStep = ({ currentStep, signatureComplete, signatureData, setSignatureModalOpen }) => (
  <>
            {/* Step 3: Signature */}
            {currentStep === 3 && (
              <div className="glass-panel-soft rounded-[18px] p-6">
                <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                  <FileSignature className="w-5 h-5 text-purple-400" />
                  Signature électronique
                </h2>
                
                {signatureComplete ? (
                  <div className="text-center py-8">
                    <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-emerald-500/20 flex items-center justify-center">
                      <CheckCircle2 className="w-8 h-8 text-emerald-400" />
                    </div>
                    <p className="text-lg font-medium text-white mb-2">Document signé</p>
                    <p className="text-sm text-white/60 mb-4">
                      Votre bon de commande a été signé électroniquement.
                    </p>
                    <Badge className="bg-emerald-500/20 text-emerald-400 border-emerald-500/30">
                      <Shield className="w-3 h-3 mr-1" />
                      Signature eIDAS niveau AES
                    </Badge>
                    {signatureData?.signature_hash && (
                      <p className="text-xs text-white/40 mt-4 font-mono">
                        Hash: {signatureData.signature_hash?.substring(0, 32)}...
                      </p>
                    )}
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-purple-500/20 flex items-center justify-center">
                      <FileSignature className="w-8 h-8 text-purple-400" />
                    </div>
                    <p className="text-lg font-medium text-white mb-2">Signature requise</p>
                    <p className="text-sm text-white/60 mb-6">
                      Signez votre bon de commande par SMS (code OTP) pour valider votre commande.
                    </p>
                    <Button 
                      onClick={() => setSignatureModalOpen(true)}
                      className="bg-purple-600 hover:bg-purple-700 text-white"
                    >
                      <FileSignature className="w-4 h-4 mr-2" />
                      Signer le bon de commande
                    </Button>
                    <p className="text-xs text-white/40 mt-4">
                      Conformité eIDAS niveau AES (Advanced Electronic Signature)
                    </p>
                  </div>
                )}
              </div>
            )}
  </>
);

