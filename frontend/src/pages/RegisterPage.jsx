import Seo from '../components/Seo';
import { useTranslation } from 'react-i18next';
import React, { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Checkbox } from '../components/ui/checkbox';
import { partners, subscriptionPlans } from '../data/mock';
import { countries, getFlagDataUrl, getPhonePlaceholder, defaultCountry } from '../data/countries';
import { ArrowLeft, UserPlus, Building2, Mail, Lock, Loader2, Globe, Phone, Eye, EyeOff } from 'lucide-react';
import { toast } from 'sonner';
import { authAPI } from '../services/api';
import PreselectedRelayBadge from '../components/PreselectedRelayBadge';

const RegisterPage = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const preselectedPlan = searchParams.get('plan') || '';
  
  const [isLoading, setIsLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [selectedCountry, setSelectedCountry] = useState(defaultCountry.code);
  const [selectedPhoneCountry, setSelectedPhoneCountry] = useState(defaultCountry.code);
  const [formData, setFormData] = useState({
    companyName: '',
    siret: '',
    contactName: '',
    email: '',
    phone: '',
    password: '',
    confirmPassword: '',
    plan: preselectedPlan,
    acceptTerms: false,
    country: defaultCountry.code,
    accountType: 'buyer',
  });

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleCountryChange = (countryCode) => {
    setSelectedCountry(countryCode);
    setFormData(prev => ({ ...prev, country: countryCode }));
  };

  const handlePhoneCountryChange = (countryCode) => {
    setSelectedPhoneCountry(countryCode);
  };

  const getFullPhoneNumber = () => {
    const country = countries.find(c => c.code === selectedPhoneCountry);
    if (!country || !formData.phone) return formData.phone;
    return `${country.phoneCode} ${formData.phone}`;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (formData.password !== formData.confirmPassword) {
      toast.error(t('auth.passwords_mismatch'));
      return;
    }
    
    if (!formData.acceptTerms) {
      toast.error(t('auth.accept_terms_error'));
      return;
    }
    
    setIsLoading(true);
    
    try {
      const submitData = {
        ...formData,
        phone: getFullPhoneNumber(),
      };
      await authAPI.register(submitData);
      toast.success(t('auth.account_created'));
      navigate('/connexion');
    } catch (error) {
      toast.error(error.message || t('auth.account_creation_error'));
    } finally {
      setIsLoading(false);
    }
  };

  const selectedPlan = subscriptionPlans.find(p => p.id === formData.plan);
  const currentPhoneCountry = countries.find(c => c.code === selectedPhoneCountry);

  return (
    <div 
      className="min-h-screen flex items-center justify-center p-4 py-12"
      style={{
        background: `
          radial-gradient(900px 420px at 20% -10%, rgba(217,179,90,0.22), transparent 55%),
          radial-gradient(820px 460px at 88% 0%, rgba(212,175,55,0.16), transparent 55%),
          linear-gradient(180deg, #2A1045 0%, #451F6B 55%, #2A1045 100%)
        `
      }}
    >
      <Seo titleKey="seo.register_title" />
      <div className="w-full max-w-2xl">
        <Link to="/" className="inline-flex items-center text-white/60 hover:text-white mb-6 transition-colors text-sm">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Retour à l'accueil
        </Link>
        
        <div className="glass-panel rounded-[26px] p-8">
          <div className="text-center mb-6">
            <div className="flex items-center justify-center gap-4 mb-4">
              <div className="bg-white rounded-2xl px-3 py-2 shadow-lg">
                <img src={partners.kdmarche.logo} alt="KDMARCHE" className="h-16 w-auto object-contain" />
              </div>
              <span className="text-white/40 text-2xl font-light">×</span>
              <div className="bg-white rounded-2xl px-3 py-2 shadow-lg">
                <img src={partners.oscop.logo} alt="O'SCOP" className="h-16 w-auto object-contain" />
              </div>
            </div>
            <h1 className="text-2xl font-bold">{t('auth.create_account')}</h1>
            <p className="text-white/60 text-sm mt-1">{t('auth.register_subtitle')}</p>
          </div>
          
          <form onSubmit={handleSubmit} className="space-y-6">
            <PreselectedRelayBadge testId="register-preselected-relay" />
            {/* Company Info */}
            <div className="space-y-4">
              <h3 className="font-semibold text-sm text-white/75 flex items-center gap-2 uppercase tracking-wider">
                <Building2 className="w-4 h-4" />
                Informations entreprise
              </h3>

              <div className="space-y-2">
                <Label className="text-white/80 text-sm">Statut *</Label>
                <div className="grid grid-cols-2 gap-3" data-testid="account-type-selector">
                  {[
                    ['buyer', 'Acheteur pro', 'Accédez au catalogue B2B et commandez'],
                    ['vendor', 'Vendeur pro', 'Publiez vos produits et vos spots vidéo'],
                  ].map(([value, label, desc]) => (
                    <button
                      key={value}
                      type="button"
                      onClick={() => setFormData((prev) => ({ ...prev, accountType: value }))}
                      data-testid={`account-type-${value}`}
                      className="rounded-xl p-3 text-left transition-all"
                      style={{
                        background: formData.accountType === value ? 'rgba(217,179,90,0.14)' : 'rgba(31,42,58,0.04)',
                        border: formData.accountType === value ? '1.5px solid rgba(184,134,11,0.7)' : '1px solid rgba(31,42,58,0.15)',
                      }}
                    >
                      <p className="text-sm font-semibold" style={{ color: formData.accountType === value ? '#B8860B' : '#1F2A3A' }}>
                        {label}
                      </p>
                      <p className="text-[11px] mt-0.5" style={{ color: 'rgba(31,42,58,0.55)' }}>{desc}</p>
                    </button>
                  ))}
                </div>
              </div>
              
              <div className="grid md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="companyName" className="text-white/80 text-sm">{t('auth.company_name')} *</Label>
                  <Input
                    id="companyName"
                    name="companyName"
                    value={formData.companyName}
                    onChange={handleChange}
                    placeholder={t('auth.company_placeholder')}
                    required
                    className="h-11 bg-white/[0.04] border-white/10 text-white placeholder:text-white/40 rounded-xl focus:border-[#D9B35A]/50"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="siret" className="text-white/80 text-sm">N° SIRET *</Label>
                  <Input
                    id="siret"
                    name="siret"
                    value={formData.siret}
                    onChange={handleChange}
                    placeholder="123 456 789 00012"
                    required
                    className="h-11 bg-white/[0.04] border-white/10 text-white placeholder:text-white/40 rounded-xl focus:border-[#D9B35A]/50"
                  />
                </div>
              </div>
              
              {/* Country Selector */}
              <div className="space-y-2">
                <Label className="text-white/80 text-sm flex items-center gap-2">
                  <Globe className="w-4 h-4" />
                  Pays *
                </Label>
                <Select value={selectedCountry} onValueChange={handleCountryChange}>
                  <SelectTrigger className="h-11 bg-white/[0.04] border-white/10 text-white rounded-xl focus:border-[#D9B35A]/50">
                    <SelectValue>
                      {selectedCountry && (
                        <div className="flex items-center gap-2">
                          <img 
                            src={getFlagDataUrl(countries.find(c => c.code === selectedCountry)?.flag || '')} 
                            alt="" 
                            className="w-5 h-4 object-cover rounded-sm"
                          />
                          <span>{countries.find(c => c.code === selectedCountry)?.name}</span>
                        </div>
                      )}
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent className="max-h-[300px]">
                    {countries.map((country) => (
                      <SelectItem key={country.code} value={country.code}>
                        <div className="flex items-center gap-2">
                          <img 
                            src={getFlagDataUrl(country.flag)} 
                            alt={country.name} 
                            className="w-5 h-4 object-cover rounded-sm"
                          />
                          <span>{country.name}</span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Contact Info */}
            <div className="space-y-4">
              <h3 className="font-semibold text-sm text-white/75 flex items-center gap-2 uppercase tracking-wider">
                <Mail className="w-4 h-4" />
                Contact principal
              </h3>
              
              <div className="grid md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="contactName" className="text-white/80 text-sm">Nom complet *</Label>
                  <Input
                    id="contactName"
                    name="contactName"
                    value={formData.contactName}
                    onChange={handleChange}
                    placeholder={t('auth.fullname_placeholder')}
                    required
                    className="h-11 bg-white/[0.04] border-white/10 text-white placeholder:text-white/40 rounded-xl focus:border-[#D9B35A]/50"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="phone" className="text-white/80 text-sm flex items-center gap-2">
                    <Phone className="w-4 h-4" />
                    Téléphone *
                  </Label>
                  <div className="flex gap-2">
                    {/* Phone Country Selector */}
                    <Select value={selectedPhoneCountry} onValueChange={handlePhoneCountryChange}>
                      <SelectTrigger className="w-[130px] h-11 bg-white/[0.04] border-white/10 text-white rounded-xl focus:border-[#D9B35A]/50">
                        <SelectValue>
                          {currentPhoneCountry && (
                            <div className="flex items-center gap-1.5">
                              <img 
                                src={getFlagDataUrl(currentPhoneCountry.flag)} 
                                alt="" 
                                className="w-5 h-4 object-cover rounded-sm"
                              />
                              <span className="text-sm">{currentPhoneCountry.phoneCode}</span>
                            </div>
                          )}
                        </SelectValue>
                      </SelectTrigger>
                      <SelectContent className="max-h-[300px]">
                        {countries.map((country) => (
                          <SelectItem key={country.code} value={country.code}>
                            <div className="flex items-center gap-2">
                              <img 
                                src={getFlagDataUrl(country.flag)} 
                                alt={country.name} 
                                className="w-5 h-4 object-cover rounded-sm"
                              />
                              <span className="text-white/60">{country.phoneCode}</span>
                              <span className="text-xs text-white/40">{country.name}</span>
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {/* Phone Input */}
                    <Input
                      id="phone"
                      name="phone"
                      type="tel"
                      value={formData.phone}
                      onChange={handleChange}
                      placeholder={getPhonePlaceholder(selectedPhoneCountry)}
                      required
                      className="flex-1 h-11 bg-white/[0.04] border-white/10 text-white placeholder:text-white/40 rounded-xl focus:border-[#D9B35A]/50"
                    />
                  </div>
                </div>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="email" className="text-white/80 text-sm">{t('auth.professional_email')} *</Label>
                <Input
                  id="email"
                  name="email"
                  type="email"
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="contact@entreprise.fr"
                  required
                  className="h-11 bg-white/[0.04] border-white/10 text-white placeholder:text-white/40 rounded-xl focus:border-[#D9B35A]/50"
                />
              </div>
            </div>

            {/* Security */}
            <div className="space-y-4">
              <h3 className="font-semibold text-sm text-white/75 flex items-center gap-2 uppercase tracking-wider">
                <Lock className="w-4 h-4" />
                Sécurité
              </h3>
              
              <div className="grid md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="password" className="text-white/80 text-sm">Mot de passe *</Label>
                  <div className="relative">
                    <Input
                      id="password"
                      name="password"
                      type={showPassword ? "text" : "password"}
                      value={formData.password}
                      onChange={handleChange}
                      placeholder={t('auth.password_min')}
                      required
                      minLength={8}
                      className="h-11 pr-11 bg-white/[0.04] border-white/10 text-white placeholder:text-white/40 rounded-xl focus:border-[#D9B35A]/50"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3.5 top-1/2 -translate-y-1/2 text-white/40 hover:text-white/70 transition-colors"
                      tabIndex={-1}
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="confirmPassword" className="text-white/80 text-sm">Confirmer *</Label>
                  <div className="relative">
                    <Input
                      id="confirmPassword"
                      name="confirmPassword"
                      type={showConfirmPassword ? "text" : "password"}
                      value={formData.confirmPassword}
                      onChange={handleChange}
                      placeholder={t('auth.confirm_password_placeholder')}
                      required
                      className="h-11 pr-11 bg-white/[0.04] border-white/10 text-white placeholder:text-white/40 rounded-xl focus:border-[#D9B35A]/50"
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      className="absolute right-3.5 top-1/2 -translate-y-1/2 text-white/40 hover:text-white/70 transition-colors"
                      tabIndex={-1}
                    >
                      {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* Plan Selection */}
            <div className="space-y-3">
              <Label className="text-white/80 text-sm">{t('auth.oscop_plan')}</Label>
              <Select 
                value={formData.plan} 
                onValueChange={(value) => setFormData(prev => ({ ...prev, plan: value }))}
              >
                <SelectTrigger className="h-11 bg-white/[0.04] border-white/10 text-white rounded-xl focus:border-[#D9B35A]/50">
                  <SelectValue placeholder={t('auth.select_plan')} />
                </SelectTrigger>
                <SelectContent className="bg-[#0d1117] border-white/10">
                  {subscriptionPlans.map((plan) => (
                    <SelectItem key={plan.id} value={plan.id} className="text-white/80 focus:bg-white/10 focus:text-white">
                      {plan.name} - {plan.price}€ HT/mois
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              
              {selectedPlan && (
                <div className="p-4 rounded-xl callout-gold">
                  <div className="flex justify-between items-center mb-2">
                    <span className="font-semibold text-white/90">{selectedPlan.name}</span>
                    <span className="ribbon text-xs">{selectedPlan.price}€ HT/mois</span>
                  </div>
                  <ul className="text-sm text-white/70 space-y-1">
                    {selectedPlan.features.slice(0, 3).map((f) => (
                      <li key={`${selectedPlan.id}-${f}`}>• {f}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Terms */}
            <div className="flex items-start gap-3">
              <Checkbox
                id="acceptTerms"
                name="acceptTerms"
                checked={formData.acceptTerms}
                onCheckedChange={(checked) => setFormData(prev => ({ ...prev, acceptTerms: checked }))}
                className="border-white/20 data-[state=checked]:bg-[#D9B35A] data-[state=checked]:border-[#D9B35A]"
              />
              <Label htmlFor="acceptTerms" className="text-sm text-white/60 cursor-pointer">
                {t('auth.accept_terms_1')} <a href="#" className="text-[#D9B35A] hover:underline">{t('auth.terms')}</a> {t('auth.accept_terms_2')} <a href="#" className="text-[#D9B35A] hover:underline">{t('auth.privacy_policy')}</a>
              </Label>
            </div>

            <button 
              type="submit" 
              disabled={isLoading}
              className="btn-gold w-full h-12 inline-flex items-center justify-center gap-2.5 rounded-[14px] text-sm font-semibold disabled:opacity-50"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  {t('auth.creating')}
                </>
              ) : (
                <>
                  <UserPlus className="w-4 h-4" />
                  {t('auth.create_my_account')}
                </>
              )}
            </button>
            
            <p className="text-center text-sm text-white/60">
              {t('auth.already_account')} <Link to="/connexion" className="text-[#D9B35A] hover:text-[#F2D07A] font-medium">{t('auth.sign_in')}</Link>
            </p>
          </form>
        </div>
      </div>
    </div>
  );
};

export default RegisterPage;
