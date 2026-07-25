import i18n from '@/i18n';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../ui/select';
import { LEGAL_STATUSES, PHONE_COUNTRIES } from '../contactFormData';
import { Flag } from '../Flag';

export const LegalFormField = ({ formData, setFormData }) => (
  <div className="space-y-2">
    <Label>{i18n.t('onboarding.statut_juridique', 'Statut juridique')}</Label>
    <Select value={formData.legalForm} onValueChange={(v) => setFormData((p) => ({ ...p, legalForm: v }))}>
      <SelectTrigger data-testid="select-legal-form">
        <SelectValue placeholder={i18n.t('onboarding.selectionnez_un_statut', 'Sélectionnez un statut')} />
      </SelectTrigger>
      <SelectContent className="max-h-64">
        {LEGAL_STATUSES.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
      </SelectContent>
    </Select>
  </div>
);

export const CountryField = ({ formData, setFormData }) => {
  const c = PHONE_COUNTRIES.find((x) => x.code === formData.country) || PHONE_COUNTRIES[0];
  return (
    <div className="space-y-2">
      <Label>{i18n.t('onboarding.pays', 'Pays')}</Label>
      <Select value={formData.country} onValueChange={(v) => setFormData((p) => ({ ...p, country: v }))}>
        <SelectTrigger data-testid="select-country">
          <SelectValue>
            <span className="flex items-center gap-2"><Flag code={c.code} className="w-5 h-auto rounded-[2px]" />{c.name}</span>
          </SelectValue>
        </SelectTrigger>
        <SelectContent className="max-h-64">
          {PHONE_COUNTRIES.map((x) => (
            <SelectItem key={x.code} value={x.code}>
              <span className="flex items-center gap-2"><Flag code={x.code} className="w-5 h-auto rounded-[2px]" />{x.name}</span>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <p className="text-xs text-gray-500">{i18n.t('onboarding.pays_immatriculation', "Pays d'immatriculation de l'entreprise")}</p>
    </div>
  );
};

export const PhoneField = ({ formData, setFormData }) => {
  const c = PHONE_COUNTRIES.find((x) => x.code === formData.phoneCountry) || PHONE_COUNTRIES[0];
  return (
    <div className="space-y-2">
      <Label htmlFor="contactPhone">{i18n.t('onboarding.telephone')}</Label>
      <div className="flex gap-2">
        <Select value={formData.phoneCountry} onValueChange={(v) => setFormData((p) => ({ ...p, phoneCountry: v }))}>
          <SelectTrigger className="w-[120px] flex-shrink-0" data-testid="select-phone-country">
            <SelectValue>
              <span className="flex items-center gap-1.5"><Flag code={c.code} className="w-5 h-auto rounded-[2px]" /><span className="text-sm">{c.dial}</span></span>
            </SelectValue>
          </SelectTrigger>
          <SelectContent className="max-h-64">
            {PHONE_COUNTRIES.map((x) => (
              <SelectItem key={x.code} value={x.code}>
                <span className="flex items-center gap-2"><Flag code={x.code} className="w-5 h-auto rounded-[2px]" />{x.name} <span className="opacity-50">{x.dial}</span></span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Input id="contactPhone" type="tel" placeholder="690 12 34 56" className="flex-1"
          value={formData.contactPhone}
          onChange={(e) => setFormData((p) => ({ ...p, contactPhone: e.target.value }))}
          data-testid="input-contact-phone" />
      </div>
    </div>
  );
};

export const AddressFields = ({ formData, setFormData }) => (
  <>
    <div className="space-y-2 md:col-span-2">
      <Label htmlFor="address">{i18n.t('onboarding.adresse', 'Adresse')}</Label>
      <Input id="address" placeholder="N° et nom de rue" value={formData.address}
        onChange={(e) => setFormData((p) => ({ ...p, address: e.target.value }))}
        data-testid="input-address" />
    </div>
    <div className="space-y-2">
      <Label htmlFor="postalCode">{i18n.t('onboarding.code_postal', 'Code postal')}</Label>
      <Input id="postalCode" placeholder="97110" value={formData.postalCode}
        onChange={(e) => setFormData((p) => ({ ...p, postalCode: e.target.value }))}
        data-testid="input-postal-code" />
    </div>
    <div className="space-y-2">
      <Label htmlFor="city">{i18n.t('onboarding.ville', 'Ville')}</Label>
      <Input id="city" placeholder="Pointe-à-Pitre" value={formData.city}
        onChange={(e) => setFormData((p) => ({ ...p, city: e.target.value }))}
        data-testid="input-city" />
    </div>
  </>
);
