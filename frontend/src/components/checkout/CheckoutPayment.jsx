import i18n from '@/i18n';
import React from 'react';
import {
  Package, MapPin, CreditCard, FileText, CheckCircle2, ArrowLeft,
  Truck, Calendar, Building2, RefreshCw, Shield, FileSignature, ChevronRight,
  Download, Loader2, Lock, AlertCircle
} from 'lucide-react';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Checkbox } from '../ui/checkbox';
import { Label } from '../ui/label';
import { Input } from '../ui/input';
import { formatCurrency, MIN_INSTALLMENT_CENTS } from './checkoutUtils';

export const PaymentStep = ({ currentStep, totals, useInstallment, setUseInstallment, paymentMethod, setPaymentMethod, orderNotes, setOrderNotes, signatureComplete, processingPayment, handlePayment, codEligible = false }) => (
  <>
            {/* Step 4: Payment */}
            {currentStep === 4 && (
              <div className="space-y-6">
                {/* Payment Method Selection */}
                <div className="glass-panel-soft rounded-[18px] p-6">
                  <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                    <CreditCard className="w-5 h-5 text-[#D9B35A]" />
                    {i18n.t('checkout.mode_de_paiement')}
                  </h2>
                  
                  <div className="space-y-4">
                    {/* Installment Option */}
                    {totals.totalHT >= MIN_INSTALLMENT_CENTS && (
                      <div className={`p-4 rounded-xl border-2 transition-all cursor-pointer ${
                        useInstallment 
                          ? 'border-purple-500 bg-purple-500/10' 
                          : 'border-white/[0.08] bg-white/[0.02] hover:border-white/20'
                      }`}
                        onClick={() => setUseInstallment(!useInstallment)}
                      >
                        <div className="flex items-center gap-3">
                          <Checkbox 
                            checked={useInstallment} 
                            onCheckedChange={setUseInstallment}
                            className="border-white/30"
                          />
                          <div className="flex-1">
                            <p className="font-medium text-white flex items-center gap-2">
                              <Calendar className="w-4 h-4 text-purple-400" />
                              {i18n.t('checkout.paiement_en_4_sans')}
                            </p>
                            <p className="text-xs text-white/50 mt-1">
                              {i18n.t('checkout.a_partir_de_5')}
                            </p>
                          </div>
                          <Badge className="bg-purple-500/20 text-purple-400 border-purple-500/30">
                            4× {formatCurrency(Math.ceil(totals.totalTTC / 4))}
                          </Badge>
                        </div>
                      </div>
                    )}
                    
                    {/* Card Payment */}
                    <div className={`p-4 rounded-xl border-2 transition-all cursor-pointer ${
                      !useInstallment && paymentMethod === 'card'
                        ? 'border-[#D9B35A] bg-[#D9B35A]/10' 
                        : 'border-white/[0.08] bg-white/[0.02] hover:border-white/20'
                    }`}
                      onClick={() => { setUseInstallment(false); setPaymentMethod('card'); }}
                    >
                      <div className="flex items-center gap-3">
                        <Checkbox 
                          checked={!useInstallment && paymentMethod === 'card'} 
                          onCheckedChange={() => { setUseInstallment(false); setPaymentMethod('card'); }}
                          className="border-white/30"
                        />
                        <div className="flex-1">
                          <p className="font-medium text-white flex items-center gap-2">
                            <CreditCard className="w-4 h-4 text-[#D9B35A]" />
                            {i18n.t('checkout.carte_bancaire')}
                          </p>
                          <p className="text-xs text-white/50 mt-1">
                            {i18n.t('checkout.visa_mastercard_american_express')}
                          </p>
                        </div>
                        <div className="flex gap-1">
                          <div className="w-8 h-5 rounded bg-[#1A1F71] flex items-center justify-center">
                            <span className="text-[8px] text-white font-bold">VISA</span>
                          </div>
                          <div className="w-8 h-5 rounded bg-gradient-to-r from-red-500 to-yellow-500 flex items-center justify-center">
                            <span className="text-[6px] text-white font-bold">MC</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* SEPA Payment */}
                    <div className={`p-4 rounded-xl border-2 transition-all cursor-pointer ${
                      !useInstallment && paymentMethod === 'sepa'
                        ? 'border-blue-500 bg-blue-500/10' 
                        : 'border-white/[0.08] bg-white/[0.02] hover:border-white/20'
                    }`}
                      onClick={() => { setUseInstallment(false); setPaymentMethod('sepa'); }}
                    >
                      <div className="flex items-center gap-3">
                        <Checkbox 
                          checked={!useInstallment && paymentMethod === 'sepa'} 
                          onCheckedChange={() => { setUseInstallment(false); setPaymentMethod('sepa'); }}
                          className="border-white/30"
                        />
                        <div className="flex-1">
                          <p className="font-medium text-white flex items-center gap-2">
                            <Building2 className="w-4 h-4 text-blue-400" />
                            {i18n.t('checkout.prelevement_sepa')}
                          </p>
                          <p className="text-xs text-white/50 mt-1">
                            {i18n.t('checkout.debit_automatique_depuis_votre')}
                          </p>
                        </div>
                        <Badge className="bg-blue-500/20 text-blue-400 border-blue-500/30">SEPA</Badge>
                      </div>
                    </div>

                    {/* Paiement à la livraison (COD) — acheteurs Pro abonnés */}
                    {codEligible && (
                      <div className={`p-4 rounded-xl border-2 transition-all cursor-pointer ${
                        !useInstallment && paymentMethod === 'cod'
                          ? 'border-emerald-500 bg-emerald-500/10'
                          : 'border-white/[0.08] bg-white/[0.02] hover:border-white/20'
                      }`}
                        onClick={() => { setUseInstallment(false); setPaymentMethod('cod'); }}
                        data-testid="cod-payment-option"
                      >
                        <div className="flex items-center gap-3">
                          <Checkbox
                            checked={!useInstallment && paymentMethod === 'cod'}
                            onCheckedChange={() => { setUseInstallment(false); setPaymentMethod('cod'); }}
                            className="border-white/30"
                          />
                          <div className="flex-1">
                            <p className="font-medium text-white flex items-center gap-2">
                              <Truck className="w-4 h-4 text-emerald-400" />
                              Paiement à la livraison
                            </p>
                            <p className="text-xs text-white/50 mt-1">
                              Commandez en toute sérénité : réglez uniquement à réception de vos marchandises. Avantage exclusif membres Pro abonnés.
                            </p>
                          </div>
                          <Badge className="bg-emerald-500/20 text-emerald-400 border-emerald-500/30">Pro abonné</Badge>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Stripe Payment Form */}
                <div className="glass-panel-soft rounded-[18px] p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                      <Lock className="w-4 h-4 text-emerald-400" />
                      {i18n.t('checkout.paiement_securise')}
                    </h3>
                    <div className="flex items-center gap-2">
                      <img 
                        src="https://stripe.com/img/v3/home/twitter.png" 
                        alt="Stripe" 
                        className="h-6 opacity-60"
                        onError={(e) => e.target.style.display = 'none'}
                      />
                      <Badge className="bg-emerald-500/20 text-emerald-400 border-emerald-500/30 text-xs">
                        {i18n.t('checkout.ssl_256_bit')}
                      </Badge>
                    </div>
                  </div>

                  {/* Payment Info */}
                  <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.08] mb-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-white/60">{i18n.t('checkout.montant_a_regler')}</span>
                      <span className="text-2xl font-bold text-[#D9B35A]">
                        {formatCurrency(useInstallment ? totals.installmentTotal : totals.totalTTC)}
                      </span>
                    </div>
                    {useInstallment && (
                      <p className="text-xs text-purple-400">
                        {i18n.t('checkout.dont_frais', { fees: formatCurrency(totals.installmentFees), installment: formatCurrency(Math.ceil((totals.installmentTotal || totals.totalTTC) / 4)) })}
                      </p>
                    )}
                  </div>

                  {/* Payment Action */}
                  <Button
                    onClick={handlePayment}
                    disabled={processingPayment || !signatureComplete}
                    className="w-full bg-gradient-to-r from-[#D9B35A] to-[#c9a34a] hover:from-[#c9a34a] hover:to-[#b9934a] text-black font-semibold h-12"
                    data-testid="pay-now-btn"
                  >
                    {processingPayment ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        {i18n.t('checkout.traitement_en_cours')}
                      </>
                    ) : paymentMethod === 'cod' && !useInstallment ? (
                      <>
                        <Truck className="w-4 h-4 mr-2" />
                        Confirmer — je règle {formatCurrency(totals.totalTTC)} à la livraison
                      </>
                    ) : (
                      <>
                        <Lock className="w-4 h-4 mr-2" />
                        Payer {formatCurrency(useInstallment ? totals.installmentTotal : totals.totalTTC)}
                      </>
                    )}
                  </Button>

                  {!signatureComplete && (
                    <div className="mt-3 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
                      <p className="text-xs text-amber-400 flex items-center gap-2">
                        <AlertCircle className="w-4 h-4" />
                        {i18n.t('checkout.veuillez_d_abord_signer')}
                      </p>
                    </div>
                  )}

                  <p className="text-xs text-white/40 text-center mt-4">
                    {i18n.t('checkout.en_cliquant_sur_payer')}
                  </p>
                </div>

                {/* Notes */}
                <div className="glass-panel-soft rounded-[18px] p-6">
                  <h3 className="text-lg font-semibold text-white mb-4">{i18n.t('checkout.notes_optionnel')}</h3>
                  <Input
                    placeholder={i18n.t('checkout.notes_placeholder')}
                    value={orderNotes}
                    onChange={(e) => setOrderNotes(e.target.value)}
                    className="bg-white/[0.04] border-white/10"
                    data-testid="order-notes-input"
                  />
                </div>

                {/* EXW Warning */}
                <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20">
                  <p className="text-sm text-amber-400">
                    <strong>{i18n.t('checkout.incoterm_exw')}</strong> {i18n.t('checkout.incoterm_exw_desc')}
                  </p>
                </div>
              </div>
            )}
  </>
);

export const OrderSummarySidebar = ({ currentStep, totals, signatureComplete, submitting, setCurrentStep, handleSubmitOrder, nextStep }) => (
  <>
          {/* Sidebar - Order Summary */}
          <div className="lg:col-span-1">
            <div className="sticky top-[140px] glass-panel-soft rounded-[18px] p-6">
              <h3 className="text-lg font-bold text-white mb-4">{i18n.t('checkout.recapitulatif')}</h3>
              
              <div className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-white/60">{i18n.t('checkout.marchandises_ht')}</span>
                  <span className="font-medium text-white">{formatCurrency(totals.productsHT)}</span>
                </div>
                
                {totals.preparationHT > 0 && (
                  <div className="flex justify-between text-emerald-400">
                    <span>{i18n.t('checkout.frais_preparation_ht')}</span>
                    <span className="font-medium">{formatCurrency(totals.preparationHT)}</span>
                  </div>
                )}
                
                <div className="flex justify-between border-t border-white/[0.08] pt-3">
                  <span className="text-white/60">{i18n.t('checkout.total_ht')}</span>
                  <span className="font-bold text-white">{formatCurrency(totals.totalHT)}</span>
                </div>
                
                <div className="flex justify-between">
                  <span className="text-white/60">
                    {i18n.t('checkout.tva')} {totals.isExonerated ? i18n.t('checkout.tva_exoneree') : `(${totals.tvaRate}%)`}
                  </span>
                  <span className={totals.isExonerated ? 'text-emerald-400' : 'text-white'}>
                    {formatCurrency(totals.tva)}
                  </span>
                </div>
                
                <div className="flex justify-between border-t border-white/[0.08] pt-3">
                  <span className="font-semibold text-white">{i18n.t('checkout.total_ttc')}</span>
                  <span className="text-2xl font-bold text-[#D9B35A]">{formatCurrency(totals.totalTTC)}</span>
                </div>
              </div>

              {/* Status badges */}
              <div className="mt-6 space-y-2">
                <Badge className="w-full justify-center bg-emerald-500/20 text-emerald-400 border-emerald-500/30">
                  <Truck className="w-3 h-3 mr-1" />
                  {i18n.t('checkout.incoterm_exw_2')}
                </Badge>
                {signatureComplete && (
                  <Badge className="w-full justify-center bg-purple-500/20 text-purple-400 border-purple-500/30">
                    <Shield className="w-3 h-3 mr-1" />
                    {i18n.t('checkout.signe_electroniquement')}
                  </Badge>
                )}
              </div>

              {/* Action Buttons */}
              <div className="mt-6 space-y-3">
                {currentStep < 4 ? (
                  <Button 
                    onClick={nextStep}
                    className="w-full bg-[#D9B35A] hover:bg-[#c9a34a] text-black"
                  >
                    {i18n.t('checkout.continuer')}
                    <ChevronRight className="w-4 h-4 ml-2" />
                  </Button>
                ) : (
                  <Button 
                    onClick={handleSubmitOrder}
                    disabled={submitting || !signatureComplete}
                    className="w-full bg-emerald-600 hover:bg-emerald-700 text-white"
                  >
                    {submitting ? (
                      <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    ) : (
                      <CheckCircle2 className="w-4 h-4 mr-2" />
                    )}
                    Confirmer la commande
                  </Button>
                )}
                
                {currentStep > 0 && (
                  <Button 
                    variant="outline"
                    onClick={() => setCurrentStep(currentStep - 1)}
                    className="w-full border-white/10 text-white/70"
                  >
                    <ArrowLeft className="w-4 h-4 mr-2" />
                    {i18n.t('checkout.etape_precedente')}
                  </Button>
                )}
              </div>
            </div>
          </div>
  </>
);

