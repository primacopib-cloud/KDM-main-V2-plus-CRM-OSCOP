import { useTranslation } from 'react-i18next';
import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { partners } from '../data/mock';
import { Mail, MapPin, FileText, Scale, Handshake, CreditCard, Truck, Leaf, Store, ChevronDown, FileSpreadsheet } from 'lucide-react';
import ContactForm from './ContactForm';
import { PartnerForm } from './PartnerForm';

const Footer = () => {
  const { t } = useTranslation();
  const [quoteOpen, setQuoteOpen] = useState(false);
  return (
    <footer style={{
      background: 'linear-gradient(180deg, #221038 0%, #1A092D 100%)',
      borderTop: '3px solid transparent',
      borderImage: 'linear-gradient(90deg, #B8941E 0%, #D4AF37 50%, #B8941E 100%) 1',
      color: '#1F2A3A'
    }}>
      <div className="max-w-[1160px] mx-auto px-5 py-16">
        <div className="grid md:grid-cols-4 gap-12">
          {/* Brand */}
          <div className="md:col-span-1">
            <div className="flex items-center gap-4 mb-6" data-testid="footer-logos">
              <div className="h-24 w-24 rounded-xl bg-white flex items-center justify-center p-1.5 flex-shrink-0">
                <img 
                  src={partners.kdmarche.logo} 
                  alt="KDMARCHE Pro" 
                  className="max-h-full max-w-full object-contain"
                />
              </div>
              <span className="text-white/30 font-light">×</span>
              <div className="h-24 w-24 rounded-xl bg-white flex items-center justify-center p-1.5 flex-shrink-0">
                <img 
                  src={partners.oscop.logo} 
                  alt="Objectif SCOP Outremer" 
                  className="max-h-full max-w-full object-contain"
                />
              </div>
            </div>
            <p className="text-white/60 text-sm leading-relaxed">
              {t('footer.tagline')}
            </p>
            
            {/* ESS Official Clause Badge */}
            <div className="mt-4 p-3 rounded-lg bg-[#10B981]/10 border border-[#10B981]/20">
              <p className="text-xs text-[#10B981] font-medium flex items-center gap-2">
                <Leaf className="w-3.5 h-3.5" />
                {t('footer.ess_certified')}
              </p>
            </div>

            <PartnerForm />
          </div>

          {/* Navigation */}
          <div>
            <h4 className="font-semibold text-sm uppercase tracking-wider text-[#D9B35A] mb-4">{t('footer.navigation')}</h4>
            <ul className="space-y-3">
              <li>
                <Link to="/" className="text-white/60 hover:text-white/90 text-sm transition-colors">{t('nav.home')}</Link>
              </li>
              <li>
                <Link to="/offres" className="text-white/60 hover:text-white/90 text-sm transition-colors">{t('footer.our_offers')}</Link>
              </li>
              <li>
                <Link to="/kdmarche" className="text-white/60 hover:text-white/90 text-sm transition-colors flex items-center gap-2" data-testid="footer-link-kdmarche">
                  <Store className="w-3.5 h-3.5 text-[#D9B35A]" />
                  <span>KDMARCHÉ Communityplace</span>
                </Link>
              </li>
              <li>
                <Link to="/logiscop" className="text-white/60 hover:text-white/90 text-sm transition-colors flex items-center gap-2" data-testid="footer-link-logiscop">
                  <Truck className="w-3.5 h-3.5 text-[#5B2E8C]" />
                  <span>LOGI&apos;SCOP</span>
                </Link>
              </li>
              <li>
                <Link to="/oscop" className="text-white/60 hover:text-white/90 text-sm transition-colors flex items-center gap-2" data-testid="footer-link-oscop">
                  <Handshake className="w-3.5 h-3.5 text-[#8CC63E]" />
                  <span>O&apos;SCOP</span>
                </Link>
              </li>
              <li>
                <Link to="/tarifs" className="text-white/60 hover:text-white/90 text-sm transition-colors" data-testid="footer-link-tarifs">{t('nav.pro_access')}</Link>
              </li>
              <li>
                <Link to="/catalogue" className="text-white/60 hover:text-white/90 text-sm transition-colors">{t('footer.b2b_catalog')}</Link>
              </li>
              <li>
                <Link to="/adhesion" className="text-white/60 hover:text-white/90 text-sm transition-colors">{t('footer.join')}</Link>
              </li>
              <li>
                <Link to="/connexion" className="text-white/60 hover:text-white/90 text-sm transition-colors">{t('footer.client_space')}</Link>
              </li>
            </ul>
            
            {/* Espaces Section */}
            <h4 className="font-semibold text-sm uppercase tracking-wider text-[#D4AF37] mb-4 mt-6">{t('footer.spaces')}</h4>
            <ul className="space-y-3">
              <li>
                <Link to="/espace-acheteur" className="text-white/60 hover:text-white/90 text-sm transition-colors">{t('footer.buyer_space')}</Link>
              </li>
              <li>
                <Link to="/espace-vendeur" className="text-white/60 hover:text-white/90 text-sm transition-colors">{t('nav.vendor_space')}</Link>
              </li>
              <li>
                <Link to="/superadmin" className="text-white/60 hover:text-white/90 text-sm transition-colors">{t('footer.administration')}</Link>
              </li>
            </ul>
          </div>

          {/* Documents Légaux */}
          <div>
            <h4 className="font-semibold text-sm uppercase tracking-wider text-[#D9B35A] mb-4 flex items-center gap-2">
              <Scale className="w-4 h-4" />
              {t('footer.legal_docs')}
            </h4>
            <ul className="space-y-3">
              <li>
                <Link 
                  to="/legal/cgv-kdmarche" 
                  className="text-white/60 hover:text-white/90 text-sm transition-colors flex items-center gap-2"
                  data-testid="footer-link-cgv-kdmarche"
                >
                  <Truck className="w-3.5 h-3.5 text-[#D9B35A]" />
                  <span>{t('footer.cgv_kdmarche')}</span>
                </Link>
              </li>
              <li>
                <Link 
                  to="/legal/cg-oscop" 
                  className="text-white/60 hover:text-white/90 text-sm transition-colors flex items-center gap-2"
                  data-testid="footer-link-cg-oscop"
                >
                  <CreditCard className="w-3.5 h-3.5 text-[#D4AF37]" />
                  <span>{t('footer.cg_oscop')}</span>
                </Link>
              </li>
              <li>
                <Link 
                  to="/legal/convention" 
                  className="text-white/60 hover:text-white/90 text-sm transition-colors flex items-center gap-2"
                  data-testid="footer-link-convention"
                >
                  <Handshake className="w-3.5 h-3.5 text-[#8B5CF6]" />
                  <span>{t('footer.convention')}</span>
                </Link>
              </li>
              <li>
                <Link 
                  to="/legal/charte-ess" 
                  className="text-white/60 hover:text-white/90 text-sm transition-colors flex items-center gap-2"
                  data-testid="footer-link-charte-ess"
                >
                  <Leaf className="w-3.5 h-3.5 text-[#10B981]" />
                  <span>{t('footer.charte_mutualisation')}</span>
                </Link>
              </li>
              <li>
                <Link 
                  to="/documents" 
                  className="text-white/60 hover:text-white/90 text-sm transition-colors flex items-center gap-2"
                >
                  <FileText className="w-3.5 h-3.5 text-white/40" />
                  <span>{t('footer.ged_documents')}</span>
                </Link>
              </li>
            </ul>
          </div>

          {/* Contact */}
          <div>
            <h4 className="font-semibold text-sm uppercase tracking-wider text-[#D9B35A] mb-4">{t('footer.contact')}</h4>
            <ul className="space-y-4">
              <li className="flex items-center gap-3 text-white/60 text-sm">
                <Mail className="w-4 h-4 text-[#D4AF37]" />
                <span>contact@objectifscopoutremer.com</span>
              </li>
              <li className="flex items-start gap-3 text-white/60 text-sm">
                <MapPin className="w-4 h-4 text-[#D4AF37] flex-shrink-0 mt-0.5" />
                <span>{t('footer.regions')}</span>
              </li>
            </ul>
          </div>
        </div>

        <hr className="border-white/10 my-10" />

        {/* Demande de devis — onglet dépliable */}
        <div className="rounded-2xl border border-[#D9B35A]/30 overflow-hidden mb-10" data-testid="footer-quote-accordion">
          <button
            type="button"
            onClick={() => setQuoteOpen((v) => !v)}
            data-testid="footer-quote-toggle"
            className="w-full flex items-center justify-between gap-3 px-5 py-4 text-left transition-colors hover:bg-white/[0.04]"
            style={{ background: 'rgba(217,179,90,0.08)' }}
            aria-expanded={quoteOpen}
          >
            <span className="flex items-center gap-2.5 text-sm font-bold text-[#E9CF8E] uppercase tracking-wider">
              <FileSpreadsheet className="w-4 h-4 text-[#D4AF37]" /> Demande de devis
            </span>
            <ChevronDown className={`w-4 h-4 text-[#D4AF37] transition-transform duration-300 ${quoteOpen ? 'rotate-180' : ''}`} />
          </button>
          {quoteOpen && (
            <div className="px-4 sm:px-6 py-6 border-t border-[#D9B35A]/20" data-testid="footer-quote-form">
              <div className="text-center mb-6">
                <span className="badge-status mb-3 inline-flex">
                  <span className="dot"></span>
                  Formulaire de contact
                </span>
                <h3 className="text-[28px] font-bold tracking-tight mt-3 mb-2 text-white">Demande de Devis</h3>
                <p className="text-white/70 text-sm">
                  Contactez-nous pour rejoindre la Communityplace ESS — votre demande est transmise à notre équipe commerciale.
                </p>
              </div>
              <div className="max-w-3xl mx-auto">
                <ContactForm />
              </div>
            </div>
          )}
        </div>

        <div className="flex flex-col md:flex-row justify-between items-center gap-4">
          <p className="text-white/50 text-xs">
            {t('footer.copyright')}
          </p>
          <div className="flex gap-6">
            <Link to="/legal/cgv-kdmarche" className="text-white/50 hover:text-white/80 text-xs transition-colors">{t('footer.legal_notice')}</Link>
            <Link to="/documents/politique-confidentialite" className="text-white/50 hover:text-white/80 text-xs transition-colors">{t('footer.privacy')}</Link>
            <Link to="/legal/charte-ess" className="text-white/50 hover:text-white/80 text-xs transition-colors">{t('footer.ess_charter')}</Link>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
