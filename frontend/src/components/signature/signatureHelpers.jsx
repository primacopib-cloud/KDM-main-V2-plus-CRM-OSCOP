import React, { useState, useEffect, useRef } from 'react';
import { Input } from '../ui/input';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Signature API functions
export const signatureAPI = {
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
export const OTPInput = ({ length = 6, value, onChange, disabled }) => {
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
          key={`otp-slot-${index}`}
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
export const CountdownTimer = ({ expiresAt, onExpired }) => {
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
