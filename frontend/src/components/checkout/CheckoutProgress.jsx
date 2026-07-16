import i18n from '@/i18n';
import React from 'react';
import { Link } from 'react-router-dom';
import {
  Package, MapPin, CreditCard, FileText, CheckCircle2, ArrowLeft,
  Truck, Calendar, Building2, RefreshCw, Shield, FileSignature, ChevronRight,
  Download, Loader2, Lock, AlertCircle
} from 'lucide-react';
import { Button } from '../ui/button';
import { partners } from '../../data/mock';
import { STEPS } from './checkoutUtils';

export const CheckoutProgress = ({ currentStep, goToStep, navigate }) => (
  <>
      {/* Header */}
      <header 
        className="sticky top-0 z-50"
        style={{
          background: 'rgba(255,253,247,0.86)',
          backdropFilter: 'blur(10px)',
          borderBottom: '1px solid rgba(212,175,55,0.32)'
        }}
      >
        <div className="max-w-[1400px] mx-auto px-5 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              onClick={() => navigate(-1)}
              className="text-white/60 hover:text-white"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              {i18n.t('orders.retour')}
            </Button>
            <div className="flex items-center gap-3">
              <img src={partners.kdmarche.logo} alt="KDMARCHE" className="h-10 w-auto object-contain" />
              <span className="text-white/40">×</span>
              <img src={partners.oscop.logo} alt="O'SCOP" className="h-6 w-auto object-contain" />
            </div>
          </div>
          
          <h1 className="text-lg font-bold text-white">{i18n.t('checkout.finaliser_la_commande')}</h1>
        </div>

        {/* Steps Progress */}
        <div className="max-w-[1400px] mx-auto px-5 py-3 border-t border-white/[0.06]">
          <div className="flex items-center justify-center gap-2">
            {STEPS.map((step, idx) => {
              const StepIcon = step.icon;
              const isActive = idx === currentStep;
              const isComplete = idx < currentStep;
              
              return (
                <React.Fragment key={step.id}>
                  <button
                    onClick={() => goToStep(idx)}
                    className={`flex items-center gap-2 px-4 py-2 rounded-xl transition-all ${
                      isActive 
                        ? 'bg-[#D9B35A]/20 text-[#D9B35A] border border-[#D9B35A]/30' 
                        : isComplete
                        ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                        : 'bg-white/[0.04] text-white/40 border border-white/[0.08]'
                    }`}
                    disabled={idx > currentStep + 1}
                  >
                    {isComplete ? (
                      <CheckCircle2 className="w-4 h-4" />
                    ) : (
                      <StepIcon className="w-4 h-4" />
                    )}
                    <span className="text-sm font-medium hidden sm:inline">{step.label}</span>
                  </button>
                  {idx < STEPS.length - 1 && (
                    <ChevronRight className="w-4 h-4 text-white/20" />
                  )}
                </React.Fragment>
              );
            })}
          </div>
        </div>
      </header>

  </>
);
