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

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Signature API functions
const signatureAPI = {
  initiate: async (data) => {
    const res = await fetch(`${API_URL}/api/signatures/initiate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Erreur initiation signature');
    }
    return res.json();
  },
  
  verifyOTP: async (signatureId, otpCode) => {
    const res = await fetch(`${API_URL}/api/signatures/verify-otp`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ signature_id: signatureId, otp_code: otpCode })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Code incorrect');
    }
    return res.json();
  },
  
  confirm: async (signatureId, consentText) => {
    const res = await fetch(`${API_URL}/api/signatures/confirm`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ signature_id: signatureId, consent_text: consentText })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Erreur confirmation');
    }
    return res.json();
  },
  
  resendOTP: async (signatureId) => {
    const res = await fetch(`${API_URL}/api/signatures/resend-otp`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ signature_id: signatureId })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Erreur renvoi code');
    }
    return res.json();
  },
  
  getStatus: async (signatureId) => {
    const res = await fetch(`${API_URL}/api/signatures/status/${signatureId}`);
    if (!res.ok) throw new Error('Erreur statut');
    return res.json();
  },
  
  decline: async (signatureId, reason) => {
    const res = await fetch(`${API_URL}/api/signatures/decline/${signatureId}?reason=${encodeURIComponent(reason)}`, {
      method: 'POST'
    });
    if (!res.ok) throw new Error('Erreur refus');
    return res.json();
  }
};

// OTP Input Component
const OTPInput = ({ length = 6, value, onChange, disabled }) => {
  const inputRefs = useRef([]);
  const [otp, setOtp] = useState(value ? value.split('') : Array(length).fill(''));
  
  useEffect(() => {
    onChange(otp.join(''));
  }, [otp, onChange]);
  
  const handleChange = (e, index) => {
    const val = e.target.value;
    if (!/^\d*$/.test(val)) return; // Only digits
    
    const newOtp = [...otp];
    newOtp[index] = val.slice(-1);
    setOtp(newOtp);
    
    // Auto-focus next input
    if (val && index < length - 1) {
      inputRefs.current[index + 1]?.focus();
    }
  };
  
  const handleKeyDown = (e, index) => {
    if (e.key === 'Backspace' && !otp[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };
  
  const handlePaste = (e) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, length);
    const newOtp = [...otp];
    for (let i = 0; i < pastedData.length; i++) {
      newOtp[i] = pastedData[i];
    }
    setOtp(newOtp);
    inputRefs.current[Math.min(pastedData.length, length - 1)]?.focus();
  };
  
  return (
    <div className="flex gap-2 justify-center">
      {Array.from({ length }).map((_, index) => (
        <input
          key={index}
          ref={el => inputRefs.current[index] = el}
          type="text"
          inputMode="numeric"
          maxLength={1}
          value={otp[index] || ''}
          onChange={e => handleChange(e, index)}
          onKeyDown={e => handleKeyDown(e, index)}
          onPaste={handlePaste}
          disabled={disabled}
          className={`
            w-12 h-14 text-center text-2xl font-bold rounded-xl border-2
            transition-all duration-200
            ${disabled ? 'bg-gray-100 border-gray-200 text-gray-400' : 'bg-white border-gray-300 text-gray-900 focus:border-[#4a1776] focus:ring-2 focus:ring-[#4a1776]/20'}
          `}
          data-testid={`otp-input-${index}`}
        />
      ))}
    </div>
  );
};

// Countdown Timer Component
const CountdownTimer = ({ expiresAt, onExpired }) => {
  const [timeLeft, setTimeLeft] = useState(0);
  
  useEffect(() => {
    if (!expiresAt) return;
    
    const updateTimer = () => {
      const now = new Date().getTime();
      const expiry = new Date(expiresAt).getTime();
      const diff = Math.max(0, Math.floor((expiry - now) / 1000));
      setTimeLeft(diff);
      
      if (diff <= 0) {
        onExpired?.();
      }
    };
    
    updateTimer();
    const interval = setInterval(updateTimer, 1000);
    return () => clearInterval(interval);
  }, [expiresAt, onExpired]);
  
  const minutes = Math.floor(timeLeft / 60);
  const seconds = timeLeft % 60;
  
  return (
    <span className={`font-mono ${timeLeft < 60 ? 'text-red-500' : 'text-gray-600'}`}>
      {minutes}:{seconds.toString().padStart(2, '0')}
    </span>
  );
};

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
          {step === 'preview' && (
            <div className="space-y-6">
              {/* Document Info */}
              <div className="p-4 rounded-xl bg-gray-50 border border-gray-100">
                <h3 className="font-semibold text-gray-900 mb-2">{documentTitle || 'Document à signer'}</h3>
                <p className="text-sm text-gray-600">
                  Type : <span className="font-medium">{documentType}</span>
                </p>
                {documentRef && (
                  <p className="text-sm text-gray-600">
                    Référence : <span className="font-mono">{documentRef}</span>
                  </p>
                )}
              </div>
              
              {/* Signer Info */}
              <div className="p-4 rounded-xl bg-[#4a1776]/5 border border-[#4a1776]/10">
                <div className="flex items-center gap-2 mb-3">
                  <Smartphone className="w-4 h-4 text-[#4a1776]" />
                  <span className="text-sm font-semibold text-[#4a1776]">Signataire</span>
                </div>
                <p className="text-sm text-gray-900">
                  {signerInfo?.first_name} {signerInfo?.last_name}
                </p>
                <p className="text-sm text-gray-600">{signerInfo?.email}</p>
                <p className="text-sm text-gray-600 font-mono">{signerInfo?.phone}</p>
              </div>
              
              {/* Document Preview */}
              {documentPreview && (
                <div className="max-h-48 overflow-y-auto rounded-lg border border-gray-200 p-3 text-sm text-gray-700">
                  {documentPreview}
                </div>
              )}
              
              {/* Security Badge */}
              <div className="flex items-center gap-2 p-3 rounded-lg bg-green-50 border border-green-100">
                <Shield className="w-4 h-4 text-green-600" />
                <span className="text-xs text-green-700">
                  Signature conforme eIDAS • Niveau AES • Authentification SMS
                </span>
              </div>
              
              {/* Actions */}
              <div className="flex gap-3">
                <Button
                  variant="outline"
                  onClick={handleDecline}
                  className="flex-1"
                  data-testid="decline-signature-btn"
                >
                  Refuser
                </Button>
                <Button
                  onClick={handleInitiateSignature}
                  disabled={loading}
                  className="flex-1 bg-[#4a1776] hover:bg-[#3a0d5e]"
                  data-testid="initiate-signature-btn"
                >
                  {loading ? (
                    <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  ) : (
                    <ChevronRight className="w-4 h-4 mr-2" />
                  )}
                  Recevoir le code SMS
                </Button>
              </div>
            </div>
          )}
          
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
          {step === 'confirm' && (
            <div className="space-y-6">
              <div className="text-center">
                <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center mx-auto mb-4">
                  <CheckCircle2 className="w-8 h-8 text-green-600" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  Identité vérifiée
                </h3>
                <p className="text-sm text-gray-600">
                  Confirmez votre signature en cliquant sur le bouton ci-dessous
                </p>
              </div>
              
              {/* Consent */}
              <div className="p-4 rounded-xl bg-[#d4af37]/10 border border-[#d4af37]/20">
                <p className="text-sm text-gray-800">
                  En signant ce document, je confirme avoir lu et approuvé son contenu.
                  Cette signature électronique a la même valeur juridique qu'une signature manuscrite.
                </p>
              </div>
              
              {/* Signature Preview */}
              <div className="p-4 rounded-xl bg-gray-50 border border-gray-200 text-center">
                <p className="text-xs text-gray-500 mb-2">Aperçu de la signature</p>
                <div className="inline-flex items-center gap-3 p-3 bg-white rounded-lg border border-gray-200">
                  <img 
                    src="/kdmarche-stamp.svg" 
                    alt="Tampon" 
                    className="w-12 h-12 opacity-80"
                  />
                  <div className="text-left">
                    <p className="font-semibold text-gray-900">
                      {signerInfo?.first_name} {signerInfo?.last_name}
                    </p>
                    <p className="text-xs text-gray-500">
                      Signé le {new Date().toLocaleDateString('fr-FR')}
                    </p>
                    <p className="text-xs text-[#4a1776] font-medium">
                      ✓ Vérifié par SMS
                    </p>
                  </div>
                </div>
              </div>
              
              {/* Actions */}
              <div className="flex gap-3">
                <Button
                  variant="outline"
                  onClick={handleDecline}
                  className="flex-1"
                >
                  Refuser
                </Button>
                <Button
                  onClick={handleConfirmSignature}
                  disabled={loading}
                  className="flex-1 bg-[#4a1776] hover:bg-[#3a0d5e]"
                  data-testid="confirm-signature-btn"
                >
                  {loading ? (
                    <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  ) : (
                    <FileSignature className="w-4 h-4 mr-2" />
                  )}
                  Signer le document
                </Button>
              </div>
            </div>
          )}
          
          {/* Step: Success */}
          {step === 'success' && signatureResult && (
            <div className="space-y-6">
              <div className="text-center">
                <div className="w-20 h-20 rounded-full bg-green-100 flex items-center justify-center mx-auto mb-4">
                  <CheckCircle2 className="w-10 h-10 text-green-600" />
                </div>
                <h3 className="text-xl font-bold text-gray-900 mb-2">
                  Document signé !
                </h3>
                <p className="text-sm text-gray-600">
                  Votre signature a été enregistrée avec succès
                </p>
              </div>
              
              {/* Signature Details */}
              <div className="p-4 rounded-xl bg-gray-50 border border-gray-100 space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">ID Signature</span>
                  <span className="font-mono text-gray-900">{signatureResult.signature_id}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Date</span>
                  <span className="text-gray-900">
                    {new Date(signatureResult.signed_at).toLocaleString('fr-FR')}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Hash</span>
                  <span className="font-mono text-xs text-gray-600 truncate max-w-[200px]">
                    {signatureResult.signature_hash}
                  </span>
                </div>
              </div>
              
              {/* Close Button */}
              <Button
                onClick={onClose}
                className="w-full bg-[#4a1776] hover:bg-[#3a0d5e]"
              >
                Fermer
              </Button>
            </div>
          )}
          
          {/* Step: Error */}
          {step === 'error' && (
            <div className="space-y-6">
              <div className="text-center">
                <div className="w-16 h-16 rounded-full bg-red-100 flex items-center justify-center mx-auto mb-4">
                  <XCircle className="w-8 h-8 text-red-600" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  Erreur de signature
                </h3>
                <p className="text-sm text-red-600">{error}</p>
              </div>
              
              <div className="flex gap-3">
                <Button variant="outline" onClick={onClose} className="flex-1">
                  Fermer
                </Button>
                <Button
                  onClick={() => setStep('preview')}
                  className="flex-1 bg-[#4a1776] hover:bg-[#3a0d5e]"
                >
                  Réessayer
                </Button>
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
