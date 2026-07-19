import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Store, ShoppingBag, Users, Globe2, Package, TrendingUp, HeartHandshake, ArrowRight } from 'lucide-react';
import Header from '../components/Header';
import { FlashPromoBanner } from '../components/FlashPromoBanner';
import Footer from '../components/Footer';
import CommunityplaceBadge from '../components/CommunityplaceBadge';
import { VideoShowcase } from '../components/kdmarche/VideoShowcase';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const Stat = ({ icon: Icon, value, label, color }) => (
  <div className="glass-panel-soft rounded-[18px] p-5 text-center" data-testid={`kdm-stat-${label.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`}>
    <Icon className="w-5 h-5 mx-auto mb-2" style={{ color }} />
    <p className="text-3xl font-bold" style={{ color }}>{value ?? '—'}</p>
    <p className="text-xs uppercase tracking-wider opacity-60 mt-1">{label}</p>
  </div>
);

const Pillar = ({ icon: Icon, title, items, color, testId }) => (
  <div className="glass-panel-soft rounded-[20px] p-6" data-testid={testId}>
    <div className="w-11 h-11 rounded-xl flex items-center justify-center mb-4"
      style={{ background: `${color}1c`, border: `1px solid ${color}55` }}>
      <Icon className="w-5 h-5" style={{ color }} />
    </div>
    <h3 className="font-display text-xl mb-3" style={{ color }}>{title}</h3>
    <ul className="space-y-2">
      {items.map((it) => (
        <li key={it} className="text-sm text-white/75 flex gap-2">
          <span style={{ color }}>•</span>{it}
        </li>
      ))}
    </ul>
  </div>
);

export default function KdmarchePage() {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    fetch(`${API}/public/kdmarche-stats`).then((r) => r.ok && r.json()).then((d) => d && setStats(d)).catch(() => {});
    window.scrollTo(0, 0);
  }, []);

  return (
    <div className="min-h-screen" data-testid="kdmarche-page">
      <Header />
      <main className="pt-24 pb-16">
        <FlashPromoBanner placement="kdmarche" />
        {/* Hero */}
        <section className="max-w-[1160px] mx-auto px-5 text-center mb-12">
          <CommunityplaceBadge className="mb-4" />
          <h1 className="font-display text-4xl sm:text-5xl lg:text-6xl tracking-tight mb-4">
            KDMARCHÉ, la <span className="text-[#D9B35A]">Communityplace</span><br />coopérative B2B2C
          </h1>
          <p className="text-white/70 max-w-[62ch] mx-auto text-base">
            La place de marché où vendeurs et acheteurs professionnels des Outre-mer interagissent
            dans un cadre coopératif de <strong className="text-white/90">mutualisation</strong> et
            d&apos;<strong className="text-white/90">agrégation collective des volumes</strong> et des services associés.
          </p>
          <div className="flex flex-wrap justify-center gap-3 mt-6">
            <Link to="/tarifs" className="btn-gold h-11 px-6 rounded-lg inline-flex items-center gap-2 text-sm font-semibold" data-testid="kdm-cta-register">
              Rejoindre la coopérative <ArrowRight size={15} />
            </Link>
            <Link to="/catalogue" className="btn-ghost h-11 px-6 rounded-lg inline-flex items-center text-sm" data-testid="kdm-cta-catalog">
              Découvrir le catalogue
            </Link>
          </div>
        </section>

        {/* Stats en direct */}
        <section className="max-w-[1160px] mx-auto px-5 mb-14" data-testid="kdm-live-stats">
          <p className="text-center text-[11px] uppercase tracking-[0.2em] text-[#D9B35A] mb-4">
            <span className="inline-block w-2 h-2 rounded-full bg-[#6FA82E] mr-2 animate-pulse" />
            Chiffres en direct de la plateforme
          </p>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <Stat icon={Package} value={stats?.products} label="Produits référencés" color="#D9B35A" />
            <Stat icon={Store} value={stats?.vendors} label="Vendeurs" color="#8CC63E" />
            <Stat icon={ShoppingBag} value={stats?.buyers} label="Acheteurs pro" color="#5B9BD5" />
            <Stat icon={Globe2} value={stats?.zones} label="Territoires" color="#E67E22" />
            <Stat icon={TrendingUp} value={stats?.orders} label="Commandes mutualisées" color="#B58CD9" />
          </div>
        </section>

        {/* Vendeurs / Acheteurs */}
        <section className="max-w-[1160px] mx-auto px-5 grid md:grid-cols-2 gap-4 mb-14">
          <Pillar
            icon={Store} title="Vendeurs référencés" color="#8CC63E" testId="kdm-pillar-vendors"
            items={[
              'Soumettez vos fiches produits avec photos et Studio IA intégré',
              'Accédez à la demande agrégée des acheteurs pro des Outre-mer',
              'Circuit de validation qualité par la coopérative',
              "Visibilité multi-territoires : Antilles, Guyane, Réunion, Mayotte",
            ]}
          />
          <Pillar
            icon={ShoppingBag} title="Acheteurs professionnels" color="#5B9BD5" testId="kdm-pillar-buyers"
            items={[
              'Prix structurels obtenus par mutualisation des volumes',
              'Catalogue B2B multi-zones avec tarifs négociés collectivement',
              'PASS Vie Chère et paiements échelonnés',
              'Livraison LOLODRIVE et points relais coopératifs',
            ]}
          />
        </section>

        {/* Galerie spots vidéo IA */}
        <VideoShowcase />

        {/* Mutualisation */}
        <section className="max-w-[820px] mx-auto px-5 text-center mb-12" data-testid="kdm-coop-section">
          <HeartHandshake className="w-8 h-8 mx-auto mb-3 text-[#D9B35A]" />
          <h2 className="font-display text-2xl mb-3">Un cadre coopératif ESS</h2>
          <p className="text-white/70 text-sm">
            1 personne = 1 voix. Gouvernance partagée, marges plafonnées et bénéfices réinvestis
            au service du pouvoir d&apos;achat des territoires. En agrégeant les besoins des professionnels,
            KDMARCHÉ transforme le volume collectif en levier de négociation pour tous ses membres.
          </p>
          <div className="flex justify-center gap-3 mt-6">
            <Link to="/tarifs" className="btn-gold h-11 px-6 rounded-lg inline-flex items-center gap-2 text-sm font-semibold" data-testid="kdm-cta-pricing">
              <Users size={15} /> Devenir membre
            </Link>
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
}
