import { useEffect, useState } from 'react';
import { Home, Building2, ShoppingBasket, CreditCard, MapPin, Truck, Mail } from 'lucide-react';

const ITEMS = [
  { id: 'top', label: 'Accueil', icon: Home },
  { id: 'pros', label: 'Professionnels', icon: Building2 },
  { id: 'offres', label: 'Tarifs', icon: CreditCard },
  { id: 'particuliers', label: 'Particuliers', icon: ShoppingBasket },
  { id: 'territoires', label: 'Territoires', icon: MapPin },
  { id: 'reseau-lolodrive', label: 'Points relais', icon: Truck },
  { id: 'contact', label: 'Contact', icon: Mail },
];

export const FloatingToc = () => {
  const [active, setActive] = useState('top');
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const onScroll = () => {
      setVisible(window.scrollY > 350);
      let current = 'top';
      for (const item of ITEMS) {
        if (item.id === 'top') continue;
        const el = document.getElementById(item.id);
        if (el && el.getBoundingClientRect().top <= 160) current = item.id;
      }
      setActive(current);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const go = (id) => {
    if (id === 'top') {
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  return (
    <nav
      aria-label="Sommaire de la page"
      data-testid="floating-toc"
      className={`hidden lg:flex flex-col gap-1 fixed right-4 top-1/2 -translate-y-1/2 z-40 p-1.5 rounded-2xl transition-all duration-300 ${
        visible ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-4 pointer-events-none'}`}
      style={{
        background: 'rgba(30,12,52,0.82)',
        backdropFilter: 'blur(14px)',
        border: '1px solid rgba(217,179,90,0.28)',
        boxShadow: '0 12px 40px rgba(0,0,0,0.35)',
      }}
    >
      {ITEMS.map(({ id, label, icon: Icon }) => {
        const isActive = active === id;
        return (
          <button
            key={id} type="button" onClick={() => go(id)} title={label}
            data-testid={`toc-link-${id}`} aria-current={isActive ? 'true' : undefined}
            className="group relative flex items-center justify-center w-9 h-9 rounded-xl transition-colors"
            style={isActive
              ? { background: 'rgba(217,179,90,0.18)', border: '1px solid rgba(217,179,90,0.5)' }
              : { border: '1px solid transparent' }}
          >
            <Icon className="w-4 h-4" style={{ color: isActive ? '#E9CF8E' : 'rgba(255,255,255,0.55)' }} />
            <span
              className="absolute right-full mr-2 px-2.5 py-1 rounded-lg text-[11px] font-semibold whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"
              style={{ background: '#1F0A33', border: '1px solid rgba(217,179,90,0.4)', color: '#E9CF8E' }}
            >
              {label}
            </span>
          </button>
        );
      })}
    </nav>
  );
};
