import {
  Building2, FileText, Upload, CheckCircle2, ArrowRight, ArrowLeft,
  MapPin, AlertCircle, Loader2, Info, ExternalLink, User
} from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '../ui/select';
import { Textarea } from '../ui/textarea';
import { Badge } from '../ui/badge';

export const TERRITORIES = [
  { code: 'MARTINIQUE', name: 'Martinique', flag: '🇲🇶' },
  { code: 'GUADELOUPE', name: 'Guadeloupe', flag: '🇬🇵' },
  { code: 'GUYANE', name: 'Guyane', flag: '🇬🇫' },
  { code: 'REUNION', name: 'La Réunion', flag: '🇷🇪' },
  { code: 'MAYOTTE', name: 'Mayotte', flag: '🇾🇹' },
  { code: 'EUROPE', name: 'Europe', flag: '🇪🇺' },
  { code: 'CARIBBEAN', name: 'Caraïbes', flag: '🌴' },
];

// Document types required
export const REQUIRED_DOCUMENTS = [
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
export const steps = [
  { id: 1, name: 'Entreprise', icon: Building2 },
  { id: 2, name: 'Documents', icon: FileText },
  { id: 3, name: 'Vérification', icon: CheckCircle2 },
];


export const OnboardingStep1 = ({ formData, setFormData, loading, handleCreateOrg }) => (
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
export const OnboardingStep2 = ({ documents, legalDocs, createdOrg, loading, setCurrentStep, handleDocumentChange, handleUploadDocuments }) => (
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
export const OnboardingStep3 = ({ createdOrg, uploadedDocs, navigate }) => (
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
