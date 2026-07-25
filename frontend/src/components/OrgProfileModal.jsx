import i18n from '@/i18n';
import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Loader2, Building2 } from 'lucide-react';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { orgsAPIV2 } from '../services/api';
import { COUNTRIES, splitPhone } from './onboarding/countries';
import {
  LegalFormField, CountryField, PhoneField, AddressFields,
} from './onboarding/OnboardingCompanyFields';

const codeByDial = (dial) => (COUNTRIES.find((c) => c.dial === dial) || {}).code || 'GP';

export const OrgProfileModal = ({ open, onOpenChange }) => {
  const [org, setOrg] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState(null);

  useEffect(() => {
    if (!open) return;
    const load = async () => {
      setLoading(true);
      try {
        const orgs = await orgsAPIV2.list();
        const o = orgs && orgs[0];
        if (!o) { setOrg(null); return; }
        setOrg(o);
        // Rétrocompatibilité : anciens profils avec téléphone combiné / adresse unique
        const legacy = splitPhone(o.contact_phone);
        const dial = o.phone_dial || legacy.dial;
        setFormData({
          legalName: o.legal_name || '',
          legalForm: o.legal_form || '',
          country: o.registration_country || 'GP',
          contactName: o.contact_name || '',
          contactEmail: o.contact_email || '',
          phoneCountry: codeByDial(dial),
          contactPhone: o.phone_number || legacy.number || '',
          address: o.address || '',
          postalCode: o.postal_code || '',
          city: o.city || '',
        });
      } catch (e) {
        toast.error(e.message || 'Erreur de chargement');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [open]);

  const save = async () => {
    if (!org || !formData) return;
    setSaving(true);
    try {
      const dial = (COUNTRIES.find((c) => c.code === formData.phoneCountry) || {}).dial || '';
      await orgsAPIV2.update(org.id, {
        legal_name: formData.legalName || undefined,
        legal_form: formData.legalForm || null,
        registration_country: formData.country || undefined,
        contact_name: formData.contactName || null,
        contact_email: formData.contactEmail || undefined,
        contact_phone: formData.contactPhone ? `${dial} ${formData.contactPhone}`.trim() : null,
        phone_dial: dial || null,
        phone_number: formData.contactPhone || null,
        address: formData.address || null,
        postal_code: formData.postalCode || null,
        city: formData.city || null,
      });
      toast.success(i18n.t('org_profile.enregistre', 'Informations mises à jour !'));
      onOpenChange(false);
    } catch (e) {
      toast.error(e.message || 'Erreur lors de la sauvegarde');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-white text-gray-900 max-w-2xl max-h-[85vh] overflow-y-auto" data-testid="org-profile-modal">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-gray-900">
            <Building2 className="w-5 h-5 text-amber-500" />
            {i18n.t('org_profile.titre', 'Mon entreprise')}
          </DialogTitle>
          <DialogDescription>
            {i18n.t('org_profile.sous_titre', 'Coordonnées, adresse et informations légales de votre organisation')}
          </DialogDescription>
        </DialogHeader>

        {loading || !formData ? (
          <div className="py-10 flex flex-col items-center gap-3">
            {loading ? (
              <Loader2 className="w-6 h-6 text-amber-500 animate-spin" />
            ) : (
              <p className="text-sm text-gray-500">{i18n.t('org_profile.aucune_org', "Aucune organisation associée à votre compte.")}</p>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="orgLegalName">{i18n.t('onboarding.raison_sociale', 'Raison sociale')}</Label>
                <Input id="orgLegalName" value={formData.legalName}
                  onChange={(e) => setFormData((p) => ({ ...p, legalName: e.target.value }))}
                  data-testid="org-profile-legal-name" />
              </div>
              <LegalFormField formData={formData} setFormData={setFormData} />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <CountryField formData={formData} setFormData={setFormData} />
              <div className="space-y-2">
                <Label htmlFor="orgContactName">{i18n.t('onboarding.nom_du_contact', 'Nom du contact')}</Label>
                <Input id="orgContactName" value={formData.contactName}
                  onChange={(e) => setFormData((p) => ({ ...p, contactName: e.target.value }))}
                  data-testid="org-profile-contact-name" />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="orgContactEmail">{i18n.t('onboarding.email', 'Email')}</Label>
                <Input id="orgContactEmail" type="email" value={formData.contactEmail}
                  onChange={(e) => setFormData((p) => ({ ...p, contactEmail: e.target.value }))}
                  data-testid="org-profile-contact-email" />
              </div>
              <PhoneField formData={formData} setFormData={setFormData} />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <AddressFields formData={formData} setFormData={setFormData} />
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <Button variant="outline" onClick={() => onOpenChange(false)} data-testid="org-profile-cancel">
                {i18n.t('org_profile.annuler', 'Annuler')}
              </Button>
              <Button onClick={save} disabled={saving} className="bg-amber-500 hover:bg-amber-600"
                data-testid="org-profile-save">
                {saving && <Loader2 className="w-4 h-4 animate-spin mr-2" />}
                {i18n.t('org_profile.enregistrer', 'Enregistrer')}
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};
