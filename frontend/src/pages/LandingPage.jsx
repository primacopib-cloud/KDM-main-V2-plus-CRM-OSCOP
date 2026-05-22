import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { downloadOffer, lolodriveAPI } from '../services/api';
import { 
  Download, 
  ArrowRight, 
  CheckCircle2,
  XCircle,
  Zap,
  ShieldCheck,
  Users,
  Truck,
  CreditCard,
  Building2,
  MapPin
} from 'lucide-react';
import { partners, subscriptionPlans, logisticsSteps, officialStatement, priceAdvantages, compliancePoints } from '../data/mock';
import PricingSection from '../components/PricingSection';
import PartnersSection from '../components/PartnersSection';
import LogisticsSection from '../components/LogisticsSection';
import ContactForm from '../components/ContactForm';
import NavBar from '../components/NavBar';
import Footer from '../components/Footer';
import LoloPointsMap from '../components/LoloPointsMap';
import TerritorySelector from '../components/TerritorySelector';

const LandingPage = () => {
  return (
    <div className="min-h-screen">
      <NavBar />
      
      {/* Hero Section */}
      <section className="pt-20 pb-8 px-5">
        <div className="max-w-[1160px] mx-auto">
          <div className="grid lg:grid-cols-[1.15fr_0.85fr] gap-6 items-stretch">
            {/* Main Hero Card */}
            <div className="glass-panel card-glow rounded-[26px] p-7">
              {/* Kicker */}
              <div className="flex items-center gap-2.5 flex-wrap mb-3.5">
                <div className="badge-status">
                  <span className="dot pulse-glow"></span>
                  Partenariat actif
                </div>
                <span className="pill">
                  <span className="font-bold text-white/90">ESS</span>
                  <span className="text-white/65">Économie Sociale et Solidaire</span>
                </span>
              </div>
              
              <h2 className="text-[40px] leading-[1.05] font-bold tracking-tight my-2.5">
                Communityplace <span className="text-[#D9B35A]">coopérative B2B2C</span>
              </h2>
              
              <p className="text-white/75 text-base max-w-[60ch] m-0">
                {officialStatement}
              </p>
              
              {/* Actions */}
              <div className="flex gap-3 flex-wrap mt-5">
                <Link to="/offres">
                  <button className="btn-gold inline-flex items-center justify-center gap-2.5 rounded-[14px] px-4 py-3 text-sm font-semibold">
                    Découvrir les offres
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </Link>
                <button 
                  className="btn-ghost inline-flex items-center justify-center gap-2.5 rounded-[14px] px-4 py-3 text-sm font-semibold"
                  onClick={downloadOffer}
                >
                  <Download className="w-4 h-4" />
                  Télécharger l'offre PDF
                </button>
              </div>
              
              {/* Mini Stats */}
              <div className="grid grid-cols-3 gap-3 mt-5">
                <div className="mini-card">
                  <div className="text-xs text-white/65 uppercase tracking-wider">Prix</div>
                  <div className="text-sm mt-1.5 text-white/90 font-bold">Jusqu'à –50%</div>
                </div>
                <div className="mini-card">
                  <div className="text-xs text-white/65 uppercase tracking-wider">Modèle</div>
                  <div className="text-sm mt-1.5 text-white/90 font-bold">B2B EXW</div>
                </div>
                <div className="mini-card">
                  <div className="text-xs text-white/65 uppercase tracking-wider">Commission</div>
                  <div className="text-sm mt-1.5 text-white/90 font-bold">0% produit</div>
                </div>
              </div>
            </div>
            
            {/* Side Card */}
            <div className="glass-panel-soft rounded-[26px] p-5 flex flex-col gap-3.5" style={{ boxShadow: '0 16px 50px rgba(0,0,0,0.35)' }}>
              <h3 className="text-sm tracking-wider uppercase text-white/75 font-semibold m-0">Avantages clés</h3>
              
              {/* Callout */}
              <div className="callout-gold">
                <strong className="text-white/90">Prix structurels B2B</strong>
                <p className="text-sm text-white/70 mt-1 mb-0">
                  Il ne s'agit ni de remises, ni de promotions, mais de prix résultant d'une mutualisation ESS.
                </p>
              </div>
              
              {/* List */}
              <ul className="grid gap-2.5 m-0 p-0 list-none">
                {priceAdvantages.map((advantage, index) => (
                  <li 
                    key={index} 
                    className="flex gap-2.5 items-start p-2.5 px-3 rounded-2xl bg-white/[0.03] border border-white/[0.08]"
                  >
                    <div className="check-icon mt-0.5"></div>
                    <div>
                      <b className="block text-white/90 text-sm">{advantage}</b>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Partners Section */}
      <PartnersSection />

      {/* Access Condition */}
      <section className="py-8 px-5">
        <div className="max-w-[1160px] mx-auto">
          <div 
            className="rounded-[22px] p-6 text-center"
            style={{
              background: 'linear-gradient(180deg, rgba(217,179,90,0.12), rgba(255,255,255,0.02))',
              border: '1px solid rgba(217,179,90,0.25)'
            }}
          >
            <span className="ribbon mb-4 inline-block">Règle absolue</span>
            <h3 className="text-2xl font-bold mt-3 mb-3">
              Condition d'accès à la Centrale d'Achats
            </h3>
            <p className="text-white/75 mb-5 max-w-2xl mx-auto">
              L'accès aux conditions <strong className="text-white">KDMARCHE – Centrale ESS</strong> est conditionné à une <strong className="text-[#57D19A]">adhésion O'SCOP active</strong>.
            </p>
            
            <div className="inline-flex flex-wrap gap-4 justify-center p-4 rounded-2xl bg-black/20">
              {[
                "Pas d'accès aux prix mutualisés",
                "Pas d'accès à la centrale B2B",
                "Pas d'accès aux zones"
              ].map((item, index) => (
                <div key={index} className="flex items-center gap-2 text-[#FF6B6B] text-sm">
                  <div className="cross-icon"></div>
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <PricingSection />

      {/* Logistics Section */}
      <LogisticsSection />

      {/* Compliance Section */}
      <section className="py-8 px-5">
        <div className="max-w-[1160px] mx-auto">
          <div className="section-title mb-4">
            <div>
              <h3 className="text-[22px] font-bold tracking-tight m-0">Conformité Juridique & Administrative</h3>
              <p className="text-white/70 text-sm mt-1 m-0">Le partenariat garantit une transparence totale</p>
            </div>
          </div>
          
          <div className="grid md:grid-cols-2 gap-3.5">
            <div className="glass-panel-soft rounded-[18px] p-5">
              <h4 className="text-sm tracking-wider uppercase text-[#57D19A] font-semibold mb-4 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4" />
                Garanties
              </h4>
              <div className="space-y-2.5">
                {compliancePoints.guaranteed.map((point, index) => (
                  <div key={index} className="flex items-center gap-2.5 text-white/80 text-sm">
                    <div className="check-icon"></div>
                    <span>{point}</span>
                  </div>
                ))}
              </div>
            </div>
            
            <div className="glass-panel-soft rounded-[18px] p-5">
              <h4 className="text-sm tracking-wider uppercase text-[#D9B35A] font-semibold mb-4 flex items-center gap-2">
                <ShieldCheck className="w-4 h-4" />
                Exclusions
              </h4>
              <div className="space-y-2.5">
                {compliancePoints.excluded.map((point, index) => (
                  <div key={index} className="flex items-center gap-2.5 text-white/80 text-sm">
                    <div className="cross-icon"></div>
                    <span>{point}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Réseau LOLODRIVE — carte publique */}
      <PublicLolodriveMapSection />

      {/* Contact Section */}
      <section id="contact" className="py-8 px-5">
        <div className="max-w-[800px] mx-auto">
          <div className="text-center mb-6">
            <span className="badge-status mb-4 inline-flex">
              <span className="dot"></span>
              Formulaire de contact
            </span>
            <h3 className="text-[28px] font-bold tracking-tight mt-3 mb-2">Demande de Devis</h3>
            <p className="text-white/70 text-sm">Contactez-nous pour rejoindre la centrale d'achats ESS</p>
          </div>
          
          <ContactForm />
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default LandingPage;

/* =================================================================
 * Section publique : carte du Reseau LOLODRIVE (acquisition / contact)
 * ================================================================= */

const PublicLolodriveMapSection = () => {
  const [points, setPoints] = useState([]);
  const [territories, setTerritories] = useState([]);
  const [territory, setTerritory] = useState(null);
  const [selected, setSelected] = useState(null);

  // Load territories once on mount
  useEffect(() => {
    lolodriveAPI.listTerritories()
      .then((t) => setTerritories(t.territories || []))
      .catch(() => {});
  }, []);

  // Load points whenever territory changes
  useEffect(() => {
    lolodriveAPI.listLoloPoints({ territory: territory || undefined })
      .then((p) => setPoints(p.points || []))
      .catch(() => setPoints([]));
  }, [territory]);

  const activateHere = (point) => {
    // Persist for the registration / PASS purchase funnel
    try {
      localStorage.setItem('kdm_preselected_point', JSON.stringify({
        id: point.id, code: point.code, name: point.name, territory: point.territory,
      }));
      if (point.territory) localStorage.setItem('kdm_territory', point.territory);
    } catch (_) {}
  };

  return (
    <section id="reseau-lolodrive" className="py-10 px-5" data-testid="public-lolodrive-section">
      <div className="max-w-[1160px] mx-auto">
        <div className="text-center mb-5">
          <span className="badge-status mb-3 inline-flex">
            <span className="dot pulse-glow"></span>
            Réseau LOLODRIVE
          </span>
          <h3 className="text-[28px] font-display font-bold tracking-tight mt-2 mb-2">
            Trouvez le relais coopératif <span className="text-or-metallise">le plus proche</span>
          </h3>
          <p className="text-white/70 text-sm max-w-[60ch] mx-auto">
            <strong>LOLODRIVE by O'SCOP</strong> est le réseau coopératif de proximité de KDMARCHÉ : retrait drive, livraison locale,
            relais commerçants et POS terrain. <strong>Cliquez sur un relais</strong> pour activer votre PASS Vie Chère sur place.
          </p>
        </div>

        <div className="glass-panel rounded-[18px] p-4 mb-3 flex flex-wrap items-center justify-between gap-3">
          <TerritorySelector
            territories={territories}
            value={territory}
            onChange={setTerritory}
            testId="public-territory-selector"
          />
          <div className="text-xs text-white/60 inline-flex items-center gap-1.5" data-testid="public-points-count">
            <MapPin className="w-3.5 h-3.5 text-or-metallise" />
            <strong className="text-white/90">{points.length}</strong> relais{points.length > 1 ? ' actifs' : ' actif'}
          </div>
        </div>

        <LoloPointsMap points={points} territory={territory} height="460px" onSelect={(p) => setSelected(p)} />

        <div className="mt-3 text-center">
          <Link to="/inscription">
            <button className="btn-gold inline-flex items-center justify-center gap-2.5 rounded-[14px] px-5 py-3 text-sm font-semibold" data-testid="join-network-btn">
              Devenir relais LOLODRIVE
              <ArrowRight className="w-4 h-4" />
            </button>
          </Link>
        </div>

        {/* Fiche relais — modal coopératif */}
        {selected && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in"
            onClick={() => setSelected(null)}
            data-testid="relay-detail-modal"
          >
            <div
              className="glass-panel rounded-[20px] p-6 max-w-md w-full border border-or-metallise/30"
              onClick={(e) => e.stopPropagation()}
              style={{ background: 'linear-gradient(180deg, rgba(15,16,24,0.95), rgba(7,10,16,0.98))' }}
            >
              <div className="flex items-start justify-between mb-3">
                <div>
                  <div className="text-[11px] uppercase tracking-wider text-or-metallise mb-1">Relais LOLODRIVE</div>
                  <h3 className="text-2xl font-display font-bold leading-tight">{selected.name}</h3>
                  <div className="font-mono text-xs text-white/40 mt-1">{selected.code} · {selected.territory}</div>
                </div>
                <button onClick={() => setSelected(null)} className="text-white/40 hover:text-white text-xl leading-none px-2" data-testid="close-relay-detail">×</button>
              </div>
              <div className="separator-premium"><span className="dot"></span></div>
              <div className="space-y-2 text-sm mb-5">
                <div className="flex items-start gap-2"><MapPin className="w-4 h-4 mt-0.5 text-violet-premium flex-shrink-0" /><span>{selected.address || '—'}, {selected.city || '—'}</span></div>
                {selected.zone_name && <div className="text-xs text-white/50 ml-6">Zone : {selected.zone_name}</div>}
              </div>
              <div className="grid grid-cols-2 gap-3 mb-5 text-center">
                <div className="rounded-lg bg-vert-lime/10 border border-vert-lime/30 p-3">
                  <div className="text-[10px] uppercase tracking-wider text-vert-lime mb-0.5">Drive</div>
                  <div className="text-xs text-white/80">Retrait coopératif</div>
                </div>
                <div className="rounded-lg bg-violet-premium/10 border border-violet-premium/30 p-3">
                  <div className="text-[10px] uppercase tracking-wider text-violet-premium mb-0.5">Livraison</div>
                  <div className="text-xs text-white/80">Livraison locale</div>
                </div>
              </div>
              <Link to="/inscription" onClick={() => activateHere(selected)} data-testid="activate-pass-here-btn">
                <button className="btn-gold w-full inline-flex items-center justify-center gap-2 rounded-[14px] py-3 text-sm font-semibold">
                  Activer mon PASS ici
                  <ArrowRight className="w-4 h-4" />
                </button>
              </Link>
              <p className="text-[11px] text-white/40 mt-3 text-center">
                Vous serez redirigé vers l'inscription PASS, ce relais sera pré-sélectionné comme point de retrait.
              </p>
            </div>
          </div>
        )}
      </div>
    </section>
  );
};
