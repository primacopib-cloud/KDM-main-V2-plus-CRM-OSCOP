import React from 'react';
import { Link } from 'react-router-dom';
import { partners } from '../data/mock';
import { Mail, Phone, MapPin, FileText, Scale, Handshake, CreditCard, Truck, Leaf } from 'lucide-react';

const Footer = () => {
  return (
    <footer style={{
      background: 'linear-gradient(180deg, #FBF6EE 0%, #F2E6D3 100%)',
      borderTop: '3px solid transparent',
      borderImage: 'linear-gradient(90deg, #B8941E 0%, #D4AF37 50%, #B8941E 100%) 1',
      color: '#1F2A3A'
    }}>
      <div className="max-w-[1160px] mx-auto px-5 py-16">
        <div className="grid md:grid-cols-4 gap-12">
          {/* Brand */}
          <div className="md:col-span-1">
            <div className="flex items-center gap-4 mb-6">
              <img 
                src={partners.kdmarche.logo} 
                alt="KDMARCHE" 
                className="h-36 w-auto object-contain"
                style={{ filter: 'drop-shadow(0 2px 6px rgba(217,179,90,0.35))' }}
              />
              <span className="text-white/30 font-light">×</span>
              <img 
                src={partners.oscop.logo} 
                alt="O'SCOP" 
                className="h-20 w-auto object-contain"
                style={{ filter: 'drop-shadow(0 2px 6px rgba(87,209,154,0.35))' }}
              />
            </div>
            <p className="text-white/60 text-sm leading-relaxed">
              Centrale d&apos;achats B2B ESS - Partenariat officiel pour l&apos;Économie Sociale et Solidaire.
            </p>
            
            {/* ESS Official Clause Badge */}
            <div className="mt-4 p-3 rounded-lg bg-[#10B981]/10 border border-[#10B981]/20">
              <p className="text-xs text-[#10B981] font-medium flex items-center gap-2">
                <Leaf className="w-3.5 h-3.5" />
                Mutualisation ESS certifiée
              </p>
            </div>
          </div>

          {/* Navigation */}
          <div>
            <h4 className="font-semibold text-sm uppercase tracking-wider text-[#D9B35A] mb-4">Navigation</h4>
            <ul className="space-y-3">
              <li>
                <Link to="/" className="text-white/60 hover:text-white/90 text-sm transition-colors">Accueil</Link>
              </li>
              <li>
                <Link to="/offres" className="text-white/60 hover:text-white/90 text-sm transition-colors">Nos Offres</Link>
              </li>
              <li>
                <Link to="/catalogue" className="text-white/60 hover:text-white/90 text-sm transition-colors">Catalogue B2B</Link>
              </li>
              <li>
                <Link to="/adhesion" className="text-white/60 hover:text-white/90 text-sm transition-colors">Adhérer</Link>
              </li>
              <li>
                <Link to="/connexion" className="text-white/60 hover:text-white/90 text-sm transition-colors">Espace Client</Link>
              </li>
            </ul>
            
            {/* Espaces Section */}
            <h4 className="font-semibold text-sm uppercase tracking-wider text-[#57D19A] mb-4 mt-6">Espaces</h4>
            <ul className="space-y-3">
              <li>
                <Link to="/espace-acheteur" className="text-white/60 hover:text-white/90 text-sm transition-colors">Espace Acheteur Pro</Link>
              </li>
              <li>
                <Link to="/espace-vendeur" className="text-white/60 hover:text-white/90 text-sm transition-colors">Espace Vendeur</Link>
              </li>
              <li>
                <Link to="/superadmin" className="text-white/60 hover:text-white/90 text-sm transition-colors">Administration</Link>
              </li>
            </ul>
          </div>

          {/* Documents Légaux */}
          <div>
            <h4 className="font-semibold text-sm uppercase tracking-wider text-[#D9B35A] mb-4 flex items-center gap-2">
              <Scale className="w-4 h-4" />
              Documents Légaux
            </h4>
            <ul className="space-y-3">
              <li>
                <Link 
                  to="/legal/cgv-kdmarche" 
                  className="text-white/60 hover:text-white/90 text-sm transition-colors flex items-center gap-2"
                  data-testid="footer-link-cgv-kdmarche"
                >
                  <Truck className="w-3.5 h-3.5 text-[#D9B35A]" />
                  <span>CGV KDMARCHE B2B</span>
                </Link>
              </li>
              <li>
                <Link 
                  to="/legal/cg-oscop" 
                  className="text-white/60 hover:text-white/90 text-sm transition-colors flex items-center gap-2"
                  data-testid="footer-link-cg-oscop"
                >
                  <CreditCard className="w-3.5 h-3.5 text-[#57D19A]" />
                  <span>CG O&apos;SCOP</span>
                </Link>
              </li>
              <li>
                <Link 
                  to="/legal/convention" 
                  className="text-white/60 hover:text-white/90 text-sm transition-colors flex items-center gap-2"
                  data-testid="footer-link-convention"
                >
                  <Handshake className="w-3.5 h-3.5 text-[#8B5CF6]" />
                  <span>Convention de partenariat</span>
                </Link>
              </li>
              <li>
                <Link 
                  to="/legal/charte-ess" 
                  className="text-white/60 hover:text-white/90 text-sm transition-colors flex items-center gap-2"
                  data-testid="footer-link-charte-ess"
                >
                  <Leaf className="w-3.5 h-3.5 text-[#10B981]" />
                  <span>Charte ESS de mutualisation</span>
                </Link>
              </li>
              <li>
                <Link 
                  to="/documents" 
                  className="text-white/60 hover:text-white/90 text-sm transition-colors flex items-center gap-2"
                >
                  <FileText className="w-3.5 h-3.5 text-white/40" />
                  <span>GED - Documents</span>
                </Link>
              </li>
            </ul>
          </div>

          {/* Contact */}
          <div>
            <h4 className="font-semibold text-sm uppercase tracking-wider text-[#D9B35A] mb-4">Contact</h4>
            <ul className="space-y-4">
              <li className="flex items-center gap-3 text-white/60 text-sm">
                <Mail className="w-4 h-4 text-[#57D19A]" />
                <span>contact@centrale-ess.fr</span>
              </li>
              <li className="flex items-center gap-3 text-white/60 text-sm">
                <Phone className="w-4 h-4 text-[#57D19A]" />
                <span>+33 1 23 45 67 89</span>
              </li>
              <li className="flex items-start gap-3 text-white/60 text-sm">
                <MapPin className="w-4 h-4 text-[#57D19A] flex-shrink-0 mt-0.5" />
                <span>Outre-mer & Métropole</span>
              </li>
            </ul>
          </div>
        </div>

        <hr className="border-white/10 my-10" />

        <div className="flex flex-col md:flex-row justify-between items-center gap-4">
          <p className="text-white/50 text-xs">
            © 2025 Centrale d&apos;Achats B2B ESS - KDMARCHE &amp; O&apos;SCOP. Tous droits réservés.
          </p>
          <div className="flex gap-6">
            <Link to="/legal/cgv-kdmarche" className="text-white/50 hover:text-white/80 text-xs transition-colors">Mentions légales</Link>
            <Link to="/documents/politique-confidentialite" className="text-white/50 hover:text-white/80 text-xs transition-colors">Confidentialité</Link>
            <Link to="/legal/charte-ess" className="text-white/50 hover:text-white/80 text-xs transition-colors">Charte ESS</Link>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
