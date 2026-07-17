import i18n from '@/i18n';
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { 
  Building2, FileText, Upload, CheckCircle2, ArrowRight, ArrowLeft,
  MapPin, AlertCircle, Loader2, Info, ExternalLink, User
} from 'lucide-react';

import Header from '../components/Header';
import Footer from '../components/Footer';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { 
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue 
} from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
import { Badge } from '../components/ui/badge';

import { authAPI, orgsAPIV2, applicationsAPIV2, zonesAPIV2, documentsAPI } from '../services/api';

// Territories/Zones for selection
import {
  TERRITORIES, REQUIRED_DOCUMENTS, steps,
  OnboardingStep1, OnboardingStep2, OnboardingStep3,
} from '../components/onboarding/OnboardingSteps';

export default function OnboardingPage() {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  
  // User state
  const [user, setUser] = useState(null);
  const [existingOrg, setExistingOrg] = useState(null);
  const [existingApp, setExistingApp] = useState(null);
  
  // Form data
  const [formData, setFormData] = useState({
    legalName: '',
    registrationId: '', // SIRET
    territory: '',
    contactName: '',
    contactEmail: '',
    contactPhone: '',
    address: '',
    description: '',
  });
  
  // Created entities
  const [createdOrg, setCreatedOrg] = useState(null);
  const [createdApp, setCreatedApp] = useState(null);
  
  // Documents
  const [documents, setDocuments] = useState({});
  const [uploadedDocs, setUploadedDocs] = useState([]);
  
  // Legal docs
  const [legalDocs, setLegalDocs] = useState([]);

  // Check authentication and existing application on mount
  useEffect(() => {
    const init = async () => {
      try {
        const currentUser = authAPI.getCurrentUser();
        if (!currentUser) {
          toast.error(i18n.t('onboarding.toast_connecter'));
          navigate('/connexion?redirect=/onboarding');
          return;
        }
        setUser(currentUser);
        
        // Check for existing org
        try {
          const orgs = await orgsAPIV2.list();
          if (orgs && orgs.length > 0) {
            const org = orgs[0];
            setExistingOrg(org);
            setCreatedOrg(org);
            
            // Check org status
            if (org.status === 'APPROVED') {
              toast.success(i18n.t('onboarding.toast_approuvee'));
              navigate('/dashboard');
              return;
            }
            
            if (org.status === 'PENDING_REVIEW') {
              setCurrentStep(3);
            } else if (org.status === 'DRAFT') {
              setCurrentStep(2);
            }
          }
        } catch (e) {
          console.debug('No existing org, starting onboarding fresh:', e);
        }
        
        // Load legal documents
        try {
          const docsResponse = await documentsAPI.list();
          setLegalDocs(docsResponse.documents || []);
        } catch (e) {
          console.error('Error loading legal docs:', e);
        }
        
      } catch (error) {
        console.error('Init error:', error);
        toast.error('Erreur de chargement');
      } finally {
        setInitialLoading(false);
      }
    };
    
    init();
  }, [navigate]);

  // Form validation
  const validateStep1 = () => {
    if (!formData.legalName.trim()) {
      toast.error('Veuillez saisir la raison sociale');
      return false;
    }
    if (!formData.registrationId.trim() || formData.registrationId.replace(/\s/g, '').length < 9) {
      toast.error('Veuillez saisir un SIRET valide (minimum 9 chiffres)');
      return false;
    }
    if (!formData.territory) {
      toast.error(i18n.t('onboarding.toast_territoire'));
      return false;
    }
    if (!formData.contactName.trim()) {
      toast.error('Veuillez saisir le nom du contact');
      return false;
    }
    if (!formData.contactEmail.trim() || !formData.contactEmail.includes('@')) {
      toast.error('Veuillez saisir un email valide');
      return false;
    }
    if (!formData.contactPhone.trim()) {
      toast.error(i18n.t('onboarding.toast_telephone'));
      return false;
    }
    return true;
  };

  const validateStep2 = () => {
    const requiredDocs = REQUIRED_DOCUMENTS.filter(d => d.required);
    for (const doc of requiredDocs) {
      if (!documents[doc.type]) {
        toast.error(`Document requis manquant: ${doc.label}`);
        return false;
      }
    }
    return true;
  };

  // Step 1: Create organization
  const handleCreateOrg = async () => {
    if (!validateStep1()) return;
    
    setLoading(true);
    try {
      // Create organization
      const org = await orgsAPIV2.create({
        legalName: formData.legalName,
        registrationCountry: 'FR',
        registrationId: formData.registrationId.replace(/\s/g, ''),
        territory: formData.territory,
        contactName: formData.contactName,
        contactEmail: formData.contactEmail,
        contactPhone: formData.contactPhone,
        address: formData.address || null,
      });
      
      setCreatedOrg(org);
      
      // Create application
      const app = await applicationsAPIV2.create(org.id);
      setCreatedApp(app);
      
      toast.success(i18n.t('onboarding.toast_org_creee'));
      setCurrentStep(2);
      
    } catch (error) {
      toast.error(error.message || i18n.t('onboarding.toast_erreur_creation'));
    } finally {
      setLoading(false);
    }
  };

  // Handle document selection
  const handleDocumentChange = (docType, file) => {
    if (file) {
      // In production, this would upload to cloud storage
      // For now, we'll use a placeholder URL
      const fakeUrl = `https://storage.example.com/docs/${createdOrg?.id || 'temp'}/${docType}/${file.name}`;
      setDocuments(prev => ({
        ...prev,
        [docType]: { file, url: fakeUrl, name: file.name }
      }));
    }
  };

  // Step 2: Upload documents and submit
  const handleUploadDocuments = async () => {
    if (!validateStep2()) return;
    if (!createdApp) {
      toast.error(i18n.t('onboarding.toast_app_introuvable'));
      return;
    }
    
    setLoading(true);
    try {
      // Upload each document
      for (const [docType, docData] of Object.entries(documents)) {
        await applicationsAPIV2.uploadDocument(
          createdApp.id,
          docType,
          docData.url,
          null // checksum
        );
        setUploadedDocs(prev => [...prev, docType]);
      }
      
      // Submit application
      await applicationsAPIV2.submit(createdApp.id);
      
      toast.success('Dossier soumis pour validation !');
      setCurrentStep(3);
      
    } catch (error) {
      toast.error(error.message || 'Erreur lors de l\'envoi');
    } finally {
      setLoading(false);
    }
  };

  // Render step indicator
  const renderStepIndicator = () => (
    <div className="mb-8">
      <div className="flex items-center justify-center">
        {steps.map((step, index) => {
          const Icon = step.icon;
          const isActive = currentStep === step.id;
          const isCompleted = currentStep > step.id;
          
          return (
            <div key={step.id} className="flex items-center">
              <div className={`
                flex items-center justify-center w-10 h-10 rounded-full border-2 transition-all
                ${isActive ? 'border-amber-500 bg-amber-500 text-white' : ''}
                ${isCompleted ? 'border-green-500 bg-green-500 text-white' : ''}
                ${!isActive && !isCompleted ? 'border-gray-300 bg-white text-gray-400' : ''}
              `}>
                {isCompleted ? (
                  <CheckCircle2 className="w-5 h-5" />
                ) : (
                  <Icon className="w-5 h-5" />
                )}
              </div>
              <span className={`
                ml-2 text-sm font-medium hidden sm:block
                ${isActive ? 'text-amber-600' : ''}
                ${isCompleted ? 'text-green-600' : ''}
                ${!isActive && !isCompleted ? 'text-gray-400' : ''}
              `}>
                {step.name}
              </span>
              {index < steps.length - 1 && (
                <div className={`
                  w-12 sm:w-24 h-0.5 mx-2 sm:mx-4
                  ${currentStep > step.id ? 'bg-green-500' : 'bg-gray-200'}
                `} />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );

  // Step 1: Company Information

  // Loading state
  if (initialLoading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header />
        <main className="max-w-4xl mx-auto px-4 py-12">
          <div className="flex flex-col items-center justify-center py-20">
            <Loader2 className="w-8 h-8 text-amber-500 animate-spin mb-4" />
            <p className="text-gray-500">{i18n.t('onboarding.chargement')}</p>
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50" data-testid="onboarding-page">
      <Header />
      
      <main className="max-w-4xl mx-auto px-4 py-12">
        {/* Title */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            {i18n.t('onboarding.demande_d_adhesion_b2b')}
          </h1>
          <p className="text-gray-600">
            {i18n.t('onboarding.rejoignez_la_centrale_d')}
          </p>
        </div>
        
        {/* Step indicator */}
        {renderStepIndicator()}
        
        {/* Step content */}
        {currentStep === 1 && <OnboardingStep1 formData={formData} setFormData={setFormData} loading={loading} handleCreateOrg={handleCreateOrg} />}
        {currentStep === 2 && <OnboardingStep2 documents={documents} legalDocs={legalDocs} createdOrg={createdOrg} loading={loading} setCurrentStep={setCurrentStep} handleDocumentChange={handleDocumentChange} handleUploadDocuments={handleUploadDocuments} />}
        {currentStep === 3 && <OnboardingStep3 createdOrg={createdOrg} uploadedDocs={uploadedDocs} navigate={navigate} />}
      </main>
      
      <Footer />
    </div>
  );
}
