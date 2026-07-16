import React, { useState, useEffect, useRef } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { 
  Loader2, 
  Phone, 
  CheckCircle2, 
  XCircle, 
  FileSignature, 
  Shield, 
  RefreshCw,
  AlertCircle,
  ChevronRight,
  Smartphone
} from 'lucide-react';
import { toast } from 'sonner';

import { signatureAPI, OTPInput, CountdownTimer } from './signature/signatureHelpers';
import { PreviewStep, ConfirmStep, SuccessStep, ErrorStep } from './signature/SignatureSteps';


// Main SMS Signature Modal Component
export default function SMSSignatureModal({
  isOpen,
  onClose,
  documentType,
  documentRef,
  documentTitle,
  signerInfo,
  documentPreview,
  onSignatureComplete,
  onSignatureDeclined
}) {
  const [step, setStep] = useState('preview'); // preview, otp, confirm, success, error
  const [loading, setLoading] = useState(false);
  const [signatureId, setSignatureId] = useState(null);
  const [otpCode, setOtpCode] = useState('');
  const [otpExpiresAt, setOtpExpiresAt] = useState(null);
  const [attemptsRemaining, setAttemptsRemaining] = useState(3);
  const [phoneMasked, setPhoneMasked] = useState('');
  const [signatureResult, setSignatureResult] = useState(null);
  const [error, setError] = useState(null);
  const [canResend, setCanResend] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(0);
  
  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setStep('preview');
      setSignatureId(null);
      setOtpCode('');
      setOtpExpiresAt(null);
      setError(null);
      setSignatureResult(null);
    }
  }, [isOpen]);
  
  // Resend cooldown timer
  useEffect(() => {
    if (resendCooldown > 0) {
      const timer = setTimeout(() => setResendCooldown(resendCooldown - 1), 1000);
      return () => clearTimeout(timer);
    } else {
      setCanResend(true);
    }
  }, [resendCooldown]);
  
  // Step 1: Initiate signature and send OTP
  const handleInitiateSignature = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const result = await signatureAPI.initiate({
        document_type: documentType,
        document_ref: documentRef,
        signer: signerInfo
      });
      
      setSignatureId(result.signature_id);
      setPhoneMasked(result.signer_phone_masked);
      setOtpExpiresAt(result.otp_expires_at);
      setAttemptsRemaining(result.attempts_remaining);
      setStep('otp');
      setResendCooldown(60);
      setCanResend(false);
      
      toast.success('Code envoyé par SMS');
    } catch (err) {
      setError(err.message);
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  };
  
  // Step 2: Verify OTP
  const handleVerifyOTP = async () => {
    if (otpCode.length !== 6) {
      toast.error('Veuillez entrer le code à 6 chiffres');
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const result = await signatureAPI.verifyOTP(signatureId, otpCode);
      setAttemptsRemaining(result.attempts_remaining);
      setStep('confirm');
      toast.success('Code vérifié !');
    } catch (err) {
      setError(err.message);
      setAttemptsRemaining(prev => Math.max(0, prev - 1));
      toast.error(err.message);
      setOtpCode('');
    } finally {
      setLoading(false);
    }
  };
  
  // Step 3: Confirm signature
  const handleConfirmSignature = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const result = await signatureAPI.confirm(signatureId, 'Lu et approuvé');
      setSignatureResult(result);
      setStep('success');
      toast.success('Document signé avec succès !');
      onSignatureComplete?.(result);
    } catch (err) {
      setError(err.message);
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  };
  
  // Resend OTP
  const handleResendOTP = async () => {
    if (!canResend) return;
    
    setLoading(true);
    try {
      const result = await signatureAPI.resendOTP(signatureId);
      setOtpExpiresAt(result.otp_expires_at);
      setAttemptsRemaining(result.attempts_remaining);
      setOtpCode('');
      setResendCooldown(60);
      setCanResend(false);
      toast.success('Nouveau code envoyé');
    } catch (err) {
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  };
  
  // Decline signature
  const handleDecline = async () => {
    if (signatureId) {
      try {
        await signatureAPI.decline(signatureId, 'Refusé par le signataire');
        onSignatureDeclined?.();
      } catch (err) {
        console.error(err);
      }
    }
    onClose();
  };
  
  // Handle OTP expiration
  const handleOTPExpired = () => {
    setError('Le code a expiré. Veuillez demander un nouveau code.');
    setCanResend(true);
    setResendCooldown(0);
  };
  
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[500px] p-0 overflow-hidden bg-white">
        {/* Header */}
        <div 
          className="px-6 py-5"
          style={{
            background: 'linear-gradient(135deg, #1a0b2e 0%, #341057 45%, #4a1776 100%)'
          }}
        >
          <DialogHeader>
            <DialogTitle className="text-white flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-white/10 flex items-center justify-center">
                <FileSignature className="w-5 h-5 text-[#d4af37]" />
              </div>
              <div>
                <div className="text-lg font-semibold">Signature électronique</div>
                <div className="text-sm text-white/60 font-normal">par SMS (OTP)</div>
              </div>
            </DialogTitle>
          </DialogHeader>
        </div>
        
        {/* Content */}
        <div className="p-6">
          {/* Step: Preview */}
          <PreviewStep step={step} documentPreview={documentPreview} documentTitle={documentTitle} documentType={documentType} signerInfo={signerInfo} loading={loading} handleDecline={handleDecline} handleInitiateSignature={handleInitiateSignature} />
          {/* Step: OTP Verification */}
          {step === 'otp' && (
            <div className="space-y-6">
              {/* Phone Info */}
              <div className="text-center">
                <div className="w-16 h-16 rounded-full bg-[#4a1776]/10 flex items-center justify-center mx-auto mb-4">
                  <Phone className="w-8 h-8 text-[#4a1776]" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  Vérification par SMS
                </h3>
                <p className="text-sm text-gray-600">
                  Un code à 6 chiffres a été envoyé au
                </p>
                <p className="font-mono font-semibold text-[#4a1776]">{phoneMasked}</p>
              </div>
              
              {/* OTP Input */}
              <div>
                <OTPInput
                  length={6}
                  value={otpCode}
                  onChange={setOtpCode}
                  disabled={loading}
                />
              </div>
              
              {/* Timer & Attempts */}
              <div className="flex justify-between items-center text-sm">
                <div className="flex items-center gap-2">
                  <span className="text-gray-500">Expire dans :</span>
                  <CountdownTimer expiresAt={otpExpiresAt} onExpired={handleOTPExpired} />
                </div>
                <span className="text-gray-500">
                  {attemptsRemaining} tentative(s)
                </span>
              </div>
              
              {/* Error */}
              {error && (
                <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 border border-red-100">
                  <AlertCircle className="w-4 h-4 text-red-500" />
                  <span className="text-sm text-red-700">{error}</span>
                </div>
              )}
              
              {/* Resend */}
              <div className="text-center">
                <button
                  onClick={handleResendOTP}
                  disabled={!canResend || loading}
                  className={`text-sm ${canResend ? 'text-[#4a1776] hover:underline' : 'text-gray-400'}`}
                >
                  {canResend ? (
                    <span className="flex items-center gap-1">
                      <RefreshCw className="w-3 h-3" />
                      Renvoyer le code
                    </span>
                  ) : (
                    `Renvoyer dans ${resendCooldown}s`
                  )}
                </button>
              </div>
              
              {/* Actions */}
              <div className="flex gap-3">
                <Button
                  variant="outline"
                  onClick={handleDecline}
                  className="flex-1"
                >
                  Annuler
                </Button>
                <Button
                  onClick={handleVerifyOTP}
                  disabled={loading || otpCode.length !== 6}
                  className="flex-1 bg-[#4a1776] hover:bg-[#3a0d5e]"
                  data-testid="verify-otp-btn"
                >
                  {loading ? (
                    <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  ) : (
                    <CheckCircle2 className="w-4 h-4 mr-2" />
                  )}
                  Vérifier
                </Button>
              </div>
            </div>
          )}
          
          {/* Step: Confirm Signature */}
          <ConfirmStep step={step} signerInfo={signerInfo} loading={loading} handleDecline={handleDecline} handleConfirmSignature={handleConfirmSignature} />
          <SuccessStep step={step} signatureResult={signatureResult} onClose={onClose} />
          <ErrorStep step={step} error={error} onClose={onClose} setStep={setStep} />
        </div>
      </DialogContent>
    </Dialog>
  );
}
