import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowRight, Mail, MapPin, Package, ShoppingCart, Store, Loader2 } from 'lucide-react';
import Footer from '../components/Footer';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const resolveLogo = (url) => (url && url.startsWith('/api/') ? `${process.env.REACT_APP_BACKEND_URL}${url}` : url);

export default function TenantPage() {
  const { slug } = useParams();
  const [lic, setLic] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetch(`${API}/licenses/${slug}`)
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then(setLic)
      .catch(() => setError(true));
  }, [slug]);

  if (error) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4 text-white" style={{ background: '#1A092D' }} data-testid="tenant-not-found">
        <p className="text-lg">Cette vitrine territoriale n'existe pas ou n'est plus active.</p>
        <Link to="/" className="text-[#D9B35A] underline">Retour à l'accueil KDMARCHÉ × O'SCOP</Link>
      </div>
    );
  }
  if (!lic) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: '#1A092D' }}>
        <Loader2 className="w-8 h-8 animate-spin text-[#D9B35A]" />
      </div>
    );
  }

  const primary = lic.primary_color || '#5B2E8C';
  const accent = lic.accent_color || '#D9B35A';

  return (
    <div className="min-h-screen text-white" style={{ background: `linear-gradient(180deg, ${primary} 0%, #1A092D 70%)` }} data-testid="tenant-page">
      <header className="px-5 py-4 flex items-center justify-between max-w-[1160px] mx-auto">
        <div className="flex items-center gap-3">
          <div className="h-14 w-14 rounded-xl bg-white flex items-center justify-center p-1.5" style={{ border: `2px solid ${accent}` }}>
            {lic.logo_url
              ? <img src={resolveLogo(lic.logo_url)} alt={lic.name} className="max-h-full max-w-full object-contain" />
              : <span className="text-xl font-bold" style={{ color: primary }}>{lic.name.charAt(0)}</span>}
          </div>
          <div>
            <p className="font-bold text-lg leading-tight" data-testid="tenant-name">{lic.name}</p>
            <p className="text-xs text-white/60">Licence territoriale · {lic.territory_name}</p>
          </div>
        </div>
        <Link to="/connexion">
          <button className="px-4 py-2 rounded-xl text-sm font-semibold" style={{ background: accent, color: '#1A092D' }} data-testid="tenant-login-btn">
            Espace client
          </button>
        </Link>
      </header>

      <section className="px-5 pt-16 pb-12 text-center max-w-[800px] mx-auto">
        <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold mb-5"
          style={{ background: `${accent}22`, border: `1px solid ${accent}55`, color: accent }}>
          <MapPin className="w-3.5 h-3.5" /> {lic.territory_name}
        </span>
        <h1 className="text-4xl sm:text-5xl font-bold tracking-tight mb-4">{lic.name}</h1>
        <p className="text-white/70 text-base max-w-[55ch] mx-auto" data-testid="tenant-tagline">
          {lic.tagline || `La Communityplace coopérative B2B ESS de ${lic.territory_name} — prix structurels, mutualisation et logistique inter-îles.`}
        </p>
        <div className="flex gap-3 justify-center flex-wrap mt-8">
          <Link to="/catalogue">
            <button className="inline-flex items-center gap-2 px-5 py-3 rounded-[14px] text-sm font-semibold" style={{ background: accent, color: '#1A092D' }} data-testid="tenant-catalog-btn">
              <ShoppingCart className="w-4 h-4" /> Accéder au catalogue B2B <ArrowRight className="w-4 h-4" />
            </button>
          </Link>
          <Link to="/adhesion">
            <button className="inline-flex items-center gap-2 px-5 py-3 rounded-[14px] text-sm font-semibold border border-white/25 text-white hover:bg-white/10 transition-colors" data-testid="tenant-join-btn">
              <Store className="w-4 h-4" /> Devenir membre
            </button>
          </Link>
        </div>
      </section>

      <section className="px-5 pb-16 max-w-[800px] mx-auto">
        <div className="grid grid-cols-3 gap-4">
          {[
            { label: 'Produits au catalogue', value: lic.stats?.products ?? 0, icon: Package },
            { label: `Commandes · ${lic.territory_code}`, value: lic.stats?.orders ?? 0, icon: ShoppingCart },
            { label: 'Vendeurs partenaires', value: lic.stats?.vendors ?? 0, icon: Store },
          ].map((s) => (
            <div key={s.label} className="rounded-2xl p-5 text-center border border-white/10" style={{ background: 'rgba(255,255,255,0.05)' }}>
              <s.icon className="w-5 h-5 mx-auto mb-2" style={{ color: accent }} />
              <p className="text-2xl font-bold">{s.value}</p>
              <p className="text-xs text-white/55 mt-1">{s.label}</p>
            </div>
          ))}
        </div>
        {lic.contact_email && (
          <p className="text-center text-sm text-white/60 mt-8 flex items-center justify-center gap-2" data-testid="tenant-contact">
            <Mail className="w-4 h-4" style={{ color: accent }} /> {lic.contact_email}
          </p>
        )}
        <p className="text-center text-xs text-white/35 mt-10">
          Propulsé par <Link to="/" className="underline hover:text-white/60">KDMARCHÉ × O'SCOP Communityplace</Link>
        </p>
      </section>
      <Footer />
    </div>
  );
}
