import { Link } from 'react-router-dom';
import { ShieldCheck, ArrowRight, PackageCheck } from 'lucide-react';
import { trackCta } from '../../services/ctaTracking';

// Bloc commercial « Règlement à Réception Pro » — accueil, après les avantages clés
export const ReceptionProSection = () => (
  <section className="py-8 px-5" data-testid="reception-pro-section">
    <div className="max-w-[1160px] mx-auto">
      <div className="rounded-[26px] p-8 md:p-10 relative overflow-hidden"
        style={{
          background: 'linear-gradient(120deg, rgba(217,179,90,0.14) 0%, rgba(91,46,140,0.18) 55%, rgba(255,255,255,0.02) 100%)',
          border: '1px solid rgba(217,179,90,0.35)',
        }}>
        <div className="grid lg:grid-cols-[1.3fr_0.7fr] gap-8 items-center">
          <div>
            <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-[11px] uppercase tracking-[0.16em] font-bold mb-4"
              style={{ background: 'rgba(217,179,90,0.15)', border: '1px solid rgba(217,179,90,0.4)', color: '#D9B35A' }}>
              <ShieldCheck className="w-3.5 h-3.5" />
              Accès sous réserve d'éligibilité et de plafond disponible
            </span>
            <h3 className="text-3xl md:text-4xl font-bold tracking-tight text-white mb-3">
              Règlement à <span className="text-[#D9B35A]">Réception Pro</span>
            </h3>
            <p className="text-lg text-white/85 font-semibold mb-3">
              Commandez sans acompte sur les marchandises éligibles.
            </p>
            <p className="text-sm text-white/70 leading-relaxed mb-3 max-w-[62ch]">
              En tant qu'acheteur professionnel disposant d'une adhésion O'SCOP active, vous pouvez
              bénéficier d'un règlement déclenché uniquement après validation électronique de la
              réception de votre commande.
            </p>
            <p className="text-sm font-bold text-[#A9D96C] mb-5 flex items-center gap-2">
              <PackageCheck className="w-4 h-4" />
              Aucun paiement de la marchandise avant réception.
            </p>
            <Link to="/espace-acheteur" data-testid="reception-pro-eligibility-btn"
              onClick={() => trackCta('reception_pro_eligibilite')}
              className="force-white inline-flex items-center gap-2.5 rounded-[14px] px-5 py-3 text-sm font-semibold text-black shadow-lg transition-transform hover:scale-[1.02]"
              style={{ background: 'linear-gradient(135deg, #D9B35A 0%, #B8933D 100%)' }}>
              Vérifier mon éligibilité
              <ArrowRight className="w-4 h-4" />
            </Link>
            <p className="text-[11px] text-white/45 mt-3 max-w-[68ch]">
              Service réservé aux acheteurs professionnels éligibles, après validation par KDMARCHÉ,
              sous plafond disponible et selon les produits, territoires et modes de livraison concernés.
            </p>
          </div>
          <div className="rounded-2xl p-5 bg-black/25 border border-white/[0.08]" data-testid="reception-pro-card">
            <p className="text-base font-bold text-white mb-2">Commandez maintenant. Réglez à réception.</p>
            <p className="text-xs text-white/65 leading-relaxed mb-4">
              Aucun acompte sur les marchandises éligibles. Le règlement est déclenché après
              confirmation électronique de la livraison par LOGI'SCOP, dans la limite de votre
              plafond disponible.
            </p>
            <div className="space-y-2">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold text-emerald-300 bg-emerald-400/10 border border-emerald-400/30">
                ✓ Éligible au règlement à réception
              </span>
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold text-sky-300 bg-sky-400/10 border border-sky-400/30 ml-1.5">
                Règlement à l'enlèvement — produit EXW
              </span>
            </div>
            <p className="text-[10px] text-white/40 mt-4 leading-relaxed">
              Offre réservée aux professionnels éligibles, selon les produits, territoires et modes
              de livraison. Les commandes EXW restent payables à la mise à disposition ou à l'enlèvement.
            </p>
          </div>
        </div>
      </div>
    </div>
  </section>
);
