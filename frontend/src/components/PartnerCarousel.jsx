import { useEffect, useState } from 'react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const resolveLogo = (url) => (url && url.startsWith('/api/') ? `${process.env.REACT_APP_BACKEND_URL}${url}` : url);

const LogoCard = ({ p }) => {
  const inner = (
    <div className="flex flex-col items-center gap-2 px-6" style={{ minWidth: '140px' }}>
      <div className="h-20 w-20 rounded-2xl bg-white flex items-center justify-center p-2 shadow-lg transition-transform duration-300 hover:scale-105">
        {p.logo_url ? (
          <img src={resolveLogo(p.logo_url)} alt={p.name} className="max-h-full max-w-full object-contain" loading="lazy" />
        ) : (
          <span className="text-2xl font-bold text-[#5B2E8C]">{p.name.charAt(0)}</span>
        )}
      </div>
      <span className="text-xs text-white/60 font-medium whitespace-nowrap">{p.name}</span>
    </div>
  );
  return p.link ? (
    <a href={p.link} target="_blank" rel="noreferrer" className="hover:opacity-90">{inner}</a>
  ) : inner;
};

const PartnerCarousel = () => {
  const [items, setItems] = useState([]);

  useEffect(() => {
    fetch(`${API}/showcase/partners`)
      .then((r) => r.json())
      .then((d) => setItems(d.items || []))
      .catch(() => {});
  }, []);

  if (!items.length) return null;
  const marquee = items.length >= 3;
  const loop = marquee ? [...items, ...items] : items;

  return (
    <section className="py-10 px-5" data-testid="partner-carousel-section">
      <div className="max-w-[1160px] mx-auto">
        <div className="text-center mb-6">
          <span className="pill inline-flex">
            <span className="font-bold text-white/90">Ils nous font confiance</span>
          </span>
          <p className="text-white/55 text-sm mt-3">Vendeurs et opérateurs partenaires de la Communityplace</p>
        </div>
        <div className="relative overflow-hidden" style={marquee ? { maskImage: 'linear-gradient(90deg, transparent, black 8%, black 92%, transparent)', WebkitMaskImage: 'linear-gradient(90deg, transparent, black 8%, black 92%, transparent)' } : {}}>
          <div
            className={`flex items-start ${marquee ? '' : 'justify-center flex-wrap gap-y-4'}`}
            style={marquee ? { width: 'max-content', animation: `partner-scroll ${Math.max(items.length * 5, 20)}s linear infinite` } : {}}
          >
            {loop.map((p, i) => <LogoCard key={`${p.id}-${i}`} p={p} />)}
          </div>
        </div>
      </div>
      <style>{`
        @keyframes partner-scroll {
          from { transform: translateX(0); }
          to { transform: translateX(-50%); }
        }
      `}</style>
    </section>
  );
};

export default PartnerCarousel;
