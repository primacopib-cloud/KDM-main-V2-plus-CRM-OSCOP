import i18n from '@/i18n';
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
          {i18n.t('onboarding.informations_de_l_entreprise')}
        </CardTitle>
        <CardDescription>
          {i18n.t('onboarding.renseignez_les_informations_legales')}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="space-y-2">
          <Label>Statut de membre *</Label>
          <div className="grid grid-cols-2 gap-3">
            {[
              { value: 'BUYER_PRO', title: 'Acheteur pro', desc: 'Accédez au catalogue B2B et commandez' },
              { value: 'VENDOR_PRO', title: 'Vendeur pro', desc: 'Publiez vos produits et vos spots vidéo' },
            ].map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => setFormData(prev => ({ ...prev, memberType: opt.value }))}
                data-testid={`adhesion-member-type-${opt.value.toLowerCase()}`}
                className={`p-4 rounded-xl border text-left transition-all ${
                  formData.memberType === opt.value
                    ? 'border-amber-500 bg-amber-500/10'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <p className={`font-semibold text-sm ${formData.memberType === opt.value ? 'text-amber-600' : ''}`}>{opt.title}</p>
                <p className="text-xs text-gray-500 mt-0.5">{opt.desc}</p>
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="legalName">{i18n.t('onboarding.raison_sociale')}</Label>
          <Input
            id="legalName"
            placeholder="Ex: SARL MonEntreprise"
            value={formData.legalName}
            onChange={(e) => setFormData(prev => ({ ...prev, legalName: e.target.value }))}
            data-testid="input-legal-name"
          />
        </div>
        
        <div className="space-y-2">
          <Label htmlFor="registrationId">{i18n.t('onboarding.siret')}</Label>
          <Input
            id="registrationId"
            placeholder="Ex: 123 456 789 00012"
            value={formData.registrationId}
            onChange={(e) => setFormData(prev => ({ ...prev, registrationId: e.target.value }))}
            maxLength={17}
            data-testid="input-siret"
          />
          <p className="text-xs text-gray-500">
            {i18n.t('onboarding.numero_siret_a_14')}
          </p>
        </div>
        
        <div className="space-y-2">
          <Label htmlFor="territory">{i18n.t('onboarding.territoire_principal')}</Label>
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
            {i18n.t('onboarding.zone_geographique_principale_pour')}
          </p>
        </div>
        
        {/* Contact Information */}
        <div className="border-t pt-6 mt-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
            <User className="w-4 h-4" />
            {i18n.t('onboarding.contact_principal')}
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="contactName">{i18n.t('onboarding.nom_du_contact')}</Label>
              <Input
                id="contactName"
                placeholder="Ex: Jean Dupont"
                value={formData.contactName}
                onChange={(e) => setFormData(prev => ({ ...prev, contactName: e.target.value }))}
                data-testid="input-contact-name"
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="contactEmail">{i18n.t('onboarding.email')}</Label>
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
              <Label htmlFor="contactPhone">{i18n.t('onboarding.telephone')}</Label>
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
              <Label htmlFor="address">{i18n.t('onboarding.adresse_optionnel')}</Label>
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
          <Label htmlFor="description">{i18n.t('onboarding.description_de_l_activite')}</Label>
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
              <p className="font-medium">{i18n.t('onboarding.acces_b2b_exclusif')}</p>
              <p className="mt-1">
                {i18n.t('onboarding.l_acces_a_la')}
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
          {i18n.t('onboarding.documents_justificatifs')}
        </CardTitle>
        <CardDescription>
          {i18n.t('onboarding.televersez_les_documents_requis')}
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
                  {i18n.t('onboarding.ajoute')}
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
            {i18n.t('orders.retour')}
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
        <CardTitle>{i18n.t('onboarding.dossier_soumis_avec_succes')}</CardTitle>
        <CardDescription>
          {i18n.t('onboarding.votre_demande_d_adhesion')}
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
              <p className="font-semibold text-amber-900">{i18n.t('onboarding.en_attente_de_validation')}</p>
              <p className="text-sm text-amber-700">
                {i18n.t('onboarding.notre_equipe_conformite_examine')}
              </p>
            </div>
          </div>
        </div>
        
        {/* Organization recap */}
        {createdOrg && (
          <div className="border rounded-lg p-4">
            <h4 className="font-medium text-gray-900 mb-3">{i18n.t('onboarding.recapitulatif')}</h4>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500">{i18n.t('onboarding.raison_sociale_2')}</span>
                <span className="font-medium">{createdOrg.legal_name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">SIRET</span>
                <span className="font-medium">{createdOrg.registration_id}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">{i18n.t('onboarding.territoire')}</span>
                <span className="font-medium">
                  {TERRITORIES.find(t => t.code === createdOrg.territory)?.name || createdOrg.territory}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">{i18n.t('onboarding.documents')}</span>
                <span className="font-medium text-green-600">
                  {Object.keys(documents).length || uploadedDocs.length} fichier(s) envoyé(s)
                </span>
              </div>
            </div>
          </div>
        )}
        
        {/* Next steps */}
        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="font-medium text-gray-900 mb-3">{i18n.t('onboarding.prochaines_etapes')}</h4>
          <ul className="space-y-3 text-sm text-gray-600">
            <li className="flex items-start gap-2">
              <span className="w-5 h-5 rounded-full bg-amber-100 text-amber-700 flex items-center justify-center text-xs flex-shrink-0">1</span>
              <span>{i18n.t('onboarding.notre_equipe_verifie_vos')}</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="w-5 h-5 rounded-full bg-gray-100 text-gray-500 flex items-center justify-center text-xs flex-shrink-0">2</span>
              <span>{i18n.t('onboarding.vous_recevez_une_notification')}</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="w-5 h-5 rounded-full bg-gray-100 text-gray-500 flex items-center justify-center text-xs flex-shrink-0">3</span>
              <span>{i18n.t('onboarding.si_approuve_vous_pouvez')}</span>
            </li>
          </ul>
        </div>
        
        <div className="flex justify-center pt-4">
          <Button
            onClick={() => navigate('/dashboard')}
            className="bg-amber-500 hover:bg-amber-600"
            data-testid="btn-go-dashboard"
          >
            {i18n.t('onboarding.aller_au_tableau_de')}
            <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
