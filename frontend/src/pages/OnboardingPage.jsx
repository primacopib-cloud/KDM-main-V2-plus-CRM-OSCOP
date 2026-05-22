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
const TERRITORIES = [
  { code: 'MARTINIQUE', name: 'Martinique', flag: '🇲🇶' },
  { code: 'GUADELOUPE', name: 'Guadeloupe', flag: '🇬🇵' },
  { code: 'GUYANE', name: 'Guyane', flag: '🇬🇫' },
  { code: 'REUNION', name: 'La Réunion', flag: '🇷🇪' },
  { code: 'MAYOTTE', name: 'Mayotte', flag: '🇾🇹' },
  { code: 'EUROPE', name: 'Europe', flag: '🇪🇺' },
  { code: 'CARIBBEAN', name: 'Caraïbes', flag: '🌴' },
];

// Document types required
const REQUIRED_DOCUMENTS = [
  { 
    type: 'REGISTRATION_DOC', 
    label: 'Extrait Kbis ou équivalent', 
    description: 'Document officiel d\'immatriculation de moins de 3 mois',
    required: true
  },
  { 
    type: 'ID_SIGNATORY', 
    label: 'Pièce d\'identité du signataire', 
    description: 'Carte d\'identité ou passeport en cours de validité',
    required: true
  },
  { 
    type: 'BANK_RIB', 
    label: 'RIB de l\'entreprise', 
    description: 'Relevé d\'identité bancaire (optionnel)',
    required: false
  },
];

// Step components
const steps = [
  { id: 1, name: 'Entreprise', icon: Building2 },
  { id: 2, name: 'Documents', icon: FileText },
  { id: 3, name: 'Vérification', icon: CheckCircle2 },
];

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
          toast.error('Veuillez vous connecter pour accéder à cette page');
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
              toast.success('Votre organisation est déjà approuvée !');
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
          // No existing org, start fresh
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
    // Init runs once on mount; navigate, helpers (authAPI, orgsAPIV2, documentsAPI, toast) are stable.
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
      toast.error('Veuillez sélectionner un territoire');
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
      toast.error('Veuillez saisir un numéro de téléphone');
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
      
      toast.success('Organisation créée avec succès');
      setCurrentStep(2);
      
    } catch (error) {
      toast.error(error.message || 'Erreur lors de la création');
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
      toast.error('Erreur: application non trouvée');
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
  const renderStep1 = () => (
    <Card className="max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Building2 className="w-5 h-5 text-amber-500" />
          Informations de l'entreprise
        </CardTitle>
        <CardDescription>
          Renseignez les informations légales de votre entreprise pour rejoindre la centrale d'achats B2B.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="space-y-2">
          <Label htmlFor="legalName">Raison sociale *</Label>
          <Input
            id="legalName"
            placeholder="Ex: SARL MonEntreprise"
            value={formData.legalName}
            onChange={(e) => setFormData(prev => ({ ...prev, legalName: e.target.value }))}
            data-testid="input-legal-name"
          />
        </div>
        
        <div className="space-y-2">
          <Label htmlFor="registrationId">SIRET *</Label>
          <Input
            id="registrationId"
            placeholder="Ex: 123 456 789 00012"
            value={formData.registrationId}
            onChange={(e) => setFormData(prev => ({ ...prev, registrationId: e.target.value }))}
            maxLength={17}
            data-testid="input-siret"
          />
          <p className="text-xs text-gray-500">
            Numéro SIRET à 14 chiffres de votre établissement
          </p>
        </div>
        
        <div className="space-y-2">
          <Label htmlFor="territory">Territoire principal *</Label>
          <Select
            value={formData.territory}
            onValueChange={(value) => setFormData(prev => ({ ...prev, territory: value }))}
          >
            <SelectTrigger data-testid="select-territory">
              <SelectValue placeholder="Sélectionnez votre territoire" />
            </SelectTrigger>
            <SelectContent>
              {TERRITORIES.map(t => (
                <SelectItem key={t.code} value={t.code}>
                  <span className="flex items-center gap-2">
                    <span>{t.flag}</span>
                    <span>{t.name}</span>
                  </span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-xs text-gray-500">
            Zone géographique principale pour vos commandes (enlèvement EXW)
          </p>
        </div>
        
        {/* Contact Information */}
        <div className="border-t pt-6 mt-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
            <User className="w-4 h-4" />
            Contact principal
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="contactName">Nom du contact *</Label>
              <Input
                id="contactName"
                placeholder="Ex: Jean Dupont"
                value={formData.contactName}
                onChange={(e) => setFormData(prev => ({ ...prev, contactName: e.target.value }))}
                data-testid="input-contact-name"
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="contactEmail">Email *</Label>
              <Input
                id="contactEmail"
                type="email"
                placeholder="contact@entreprise.fr"
                value={formData.contactEmail}
                onChange={(e) => setFormData(prev => ({ ...prev, contactEmail: e.target.value }))}
                data-testid="input-contact-email"
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="contactPhone">Téléphone *</Label>
              <Input
                id="contactPhone"
                type="tel"
                placeholder="Ex: 0596 12 34 56"
                value={formData.contactPhone}
                onChange={(e) => setFormData(prev => ({ ...prev, contactPhone: e.target.value }))}
                data-testid="input-contact-phone"
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="address">Adresse (optionnel)</Label>
              <Input
                id="address"
                placeholder="Adresse de l'entreprise"
                value={formData.address}
                onChange={(e) => setFormData(prev => ({ ...prev, address: e.target.value }))}
              />
            </div>
          </div>
        </div>
        
        <div className="space-y-2">
          <Label htmlFor="description">Description de l'activité (optionnel)</Label>
          <Textarea
            id="description"
            placeholder="Décrivez brièvement votre activité..."
            value={formData.description}
            onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
            rows={3}
          />
        </div>
        
        {/* Info box */}
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
          <div className="flex gap-3">
            <Info className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-amber-800">
              <p className="font-medium">Accès B2B exclusif</p>
              <p className="mt-1">
                L'accès à la centrale d'achats est réservé aux professionnels. 
                Votre dossier sera vérifié par notre équipe conformité.
              </p>
            </div>
          </div>
        </div>
        
        <div className="flex justify-end pt-4">
          <Button
            onClick={handleCreateOrg}
            disabled={loading}
            className="bg-amber-500 hover:bg-amber-600"
            data-testid="btn-continue-step1"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin mr-2" />
            ) : null}
            Continuer
            <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );

  // Step 2: Document Upload
  const renderStep2 = () => (
    <Card className="max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileText className="w-5 h-5 text-amber-500" />
          Documents justificatifs
        </CardTitle>
        <CardDescription>
          Téléversez les documents requis pour valider votre dossier d'adhésion.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Organization info */}
        {createdOrg && (
          <div className="bg-gray-50 rounded-lg p-4 mb-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-gray-900">{createdOrg.legal_name}</p>
                <p className="text-sm text-gray-500">SIRET: {createdOrg.registration_id}</p>
              </div>
              <Badge variant="outline" className="text-amber-600 border-amber-300">
                {TERRITORIES.find(t => t.code === createdOrg.territory)?.name || createdOrg.territory}
              </Badge>
            </div>
          </div>
        )}
        
        {/* Document upload fields */}
        {REQUIRED_DOCUMENTS.map(doc => (
          <div key={doc.type} className="border rounded-lg p-4">
            <div className="flex items-start justify-between mb-3">
              <div>
                <Label className="flex items-center gap-2">
                  {doc.label}
                  {doc.required && <span className="text-red-500">*</span>}
                </Label>
                <p className="text-xs text-gray-500 mt-1">{doc.description}</p>
              </div>
              {documents[doc.type] && (
                <Badge className="bg-green-100 text-green-700">
                  <CheckCircle2 className="w-3 h-3 mr-1" />
                  Ajouté
                </Badge>
              )}
            </div>
            
            <div className="flex items-center gap-3">
              <Input
                type="file"
                accept=".pdf,.jpg,.jpeg,.png"
                onChange={(e) => handleDocumentChange(doc.type, e.target.files?.[0])}
                className="flex-1"
                data-testid={`input-doc-${doc.type}`}
              />
            </div>
            
            {documents[doc.type] && (
              <p className="text-xs text-gray-500 mt-2">
                Fichier: {documents[doc.type].name}
              </p>
            )}
          </div>
        ))}
        
        {/* Legal documents info */}
        {legalDocs.length > 0 && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mt-6">
            <p className="text-sm font-medium text-blue-800 mb-2">
              Documents contractuels applicables :
            </p>
            <ul className="space-y-1">
              {legalDocs.map(doc => (
                <li key={doc.id} className="text-sm text-blue-700 flex items-center gap-2">
                  <ExternalLink className="w-3 h-3" />
                  <a 
                    href={`/docs/${doc.filename}`} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="hover:underline"
                  >
                    {doc.title}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        )}
        
        <div className="flex justify-between pt-4">
          <Button
            variant="outline"
            onClick={() => setCurrentStep(1)}
            disabled={loading}
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Retour
          </Button>
          <Button
            onClick={handleUploadDocuments}
            disabled={loading}
            className="bg-amber-500 hover:bg-amber-600"
            data-testid="btn-submit-application"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin mr-2" />
            ) : null}
            Soumettre le dossier
            <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );

  // Step 3: Confirmation / Status
  const renderStep3 = () => (
    <Card className="max-w-2xl mx-auto">
      <CardHeader className="text-center">
        <div className="mx-auto w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mb-4">
          <CheckCircle2 className="w-8 h-8 text-green-600" />
        </div>
        <CardTitle>Dossier soumis avec succès !</CardTitle>
        <CardDescription>
          Votre demande d'adhésion est en cours d'examen par notre équipe.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Status card */}
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-6">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-amber-100 rounded-full flex items-center justify-center">
              <Loader2 className="w-6 h-6 text-amber-600 animate-spin" />
            </div>
            <div>
              <p className="font-semibold text-amber-900">En attente de validation</p>
              <p className="text-sm text-amber-700">
                Notre équipe conformité examine votre dossier. Vous recevrez une notification dès la décision.
              </p>
            </div>
          </div>
        </div>
        
        {/* Organization recap */}
        {createdOrg && (
          <div className="border rounded-lg p-4">
            <h4 className="font-medium text-gray-900 mb-3">Récapitulatif</h4>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500">Raison sociale</span>
                <span className="font-medium">{createdOrg.legal_name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">SIRET</span>
                <span className="font-medium">{createdOrg.registration_id}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Territoire</span>
                <span className="font-medium">
                  {TERRITORIES.find(t => t.code === createdOrg.territory)?.name || createdOrg.territory}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Documents</span>
                <span className="font-medium text-green-600">
                  {Object.keys(documents).length || uploadedDocs.length} fichier(s) envoyé(s)
                </span>
              </div>
            </div>
          </div>
        )}
        
        {/* Next steps */}
        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="font-medium text-gray-900 mb-3">Prochaines étapes</h4>
          <ul className="space-y-3 text-sm text-gray-600">
            <li className="flex items-start gap-2">
              <span className="w-5 h-5 rounded-full bg-amber-100 text-amber-700 flex items-center justify-center text-xs flex-shrink-0">1</span>
              <span>Notre équipe vérifie vos documents (délai: 24-48h)</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="w-5 h-5 rounded-full bg-gray-100 text-gray-500 flex items-center justify-center text-xs flex-shrink-0">2</span>
              <span>Vous recevez une notification de décision</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="w-5 h-5 rounded-full bg-gray-100 text-gray-500 flex items-center justify-center text-xs flex-shrink-0">3</span>
              <span>Si approuvé, vous pouvez accéder au catalogue et passer commande</span>
            </li>
          </ul>
        </div>
        
        <div className="flex justify-center pt-4">
          <Button
            onClick={() => navigate('/dashboard')}
            className="bg-amber-500 hover:bg-amber-600"
            data-testid="btn-go-dashboard"
          >
            Aller au tableau de bord
            <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );

  // Loading state
  if (initialLoading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header />
        <main className="max-w-4xl mx-auto px-4 py-12">
          <div className="flex flex-col items-center justify-center py-20">
            <Loader2 className="w-8 h-8 text-amber-500 animate-spin mb-4" />
            <p className="text-gray-500">Chargement...</p>
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
            Demande d'adhésion B2B
          </h1>
          <p className="text-gray-600">
            Rejoignez la centrale d'achats KDMARCHE × O'SCOP
          </p>
        </div>
        
        {/* Step indicator */}
        {renderStepIndicator()}
        
        {/* Step content */}
        {currentStep === 1 && renderStep1()}
        {currentStep === 2 && renderStep2()}
        {currentStep === 3 && renderStep3()}
      </main>
      
      <Footer />
    </div>
  );
}
