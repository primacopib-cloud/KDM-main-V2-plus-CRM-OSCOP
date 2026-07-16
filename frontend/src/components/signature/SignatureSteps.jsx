import i18n from '@/i18n';
import React from 'react';
import { Button } from '../ui/button';
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

export const PreviewStep = ({ step, documentPreview, documentTitle, documentType, documentRef, signerInfo, loading, handleDecline, handleInitiateSignature }) => (
  <>
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
          
  </>
);

export const ConfirmStep = ({ step, signerInfo, loading, handleDecline, handleConfirmSignature }) => (
  <>
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
                      Signé le {new Date().toLocaleDateString(i18n.language)}
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
          
  </>
);

export const SuccessStep = ({ step, signatureResult, onClose }) => (
  <>
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
                    {new Date(signatureResult.signed_at).toLocaleString(i18n.language)}
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
          
  </>
);

export const ErrorStep = ({ step, error, onClose, setStep }) => (
  <>
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
  </>
);

