import i18n from '@/i18n';
import { useEffect, useRef, useState } from 'react';
import { Users, MapPin, Package, Store, ShoppingBag } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const useCountUp = (target, start, duration = 1400) => {
  const [value, setValue] = useState(0);
  const started = useRef(false);
  useEffect(() => {
    if (!target || !start || started.current) return;
    started.current = true;
    const t0 = performance.now();
    const tick = (now) => {
      const p = Math.min((now - t0) / duration, 1);
      setValue(Math.round(target * (1 - Math.pow(1 - p, 3))));
      if (p < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }, [target, start, duration]);
  return value;
};

const StatItem = ({ icon: Icon, value, label, testId, start }) => {
  const display = useCountUp(value, start);
  return (
    <div className="flex flex-col items-center gap-1 px-4 py-2" data-testid={testId}>
      <Icon className="w-5 h-5 text-[#D9B35A]" />
      <span className="text-2xl sm:text-3xl font-extrabold text-white tabular-nums">{display}</span>
      <span className="text-xs text-white/60 text-center">{label}</span>
    </div>
  );
};

export const CommunityStatsStrip = () => {
  const [stats, setStats] = useState(null);
  const [start, setStart] = useState(false);
  const sectionRef = useRef(null);

  useEffect(() => {
    fetch(`${API}/api/public/community-stats`)
      .then((r) => (r.ok ? r.json() : null))
      .then(setStats)
      .catch(() => {});
  }, []);

  useEffect(() => {
    const el = sectionRef.current;
    if (!el || typeof IntersectionObserver === 'undefined') { setStart(true); return undefined; }
    const obs = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) { setStart(true); obs.disconnect(); }
    }, { threshold: 0.3 });
    obs.observe(el);
    return () => obs.disconnect();
  }, [stats]);

  if (!stats) return null;

  return (
    <section ref={sectionRef} className="py-6 px-5" data-testid="community-stats-strip">
      <div className="max-w-[1160px] mx-auto">
        <div
          className="rounded-[22px] py-5 px-4 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2"
          style={{
            background: 'linear-gradient(180deg, rgba(217,179,90,0.10), rgba(255,255,255,0.02))',
            border: '1px solid rgba(217,179,90,0.22)',
          }}
        >
          <StatItem icon={Users} value={stats.members} start={start} testId="stat-members"
            label={i18n.t('landing.stat_adherents', 'Adhérents professionnels')} />
          <StatItem icon={MapPin} value={stats.territories} start={start} testId="stat-territories"
            label={i18n.t('landing.stat_territoires', 'Territoires couverts')} />
          <StatItem icon={ShoppingBag} value={stats.orders} start={start} testId="stat-orders"
            label={i18n.t('landing.stat_commandes', 'Commandes traitées')} />
          <StatItem icon={Package} value={stats.products} start={start} testId="stat-products"
            label={i18n.t('landing.stat_produits', 'Produits au catalogue')} />
          <StatItem icon={Store} value={stats.lolo_points} start={start} testId="stat-lolo-points"
            label={i18n.t('landing.stat_points', 'Points relais LOLO')} />
        </div>
      </div>
    </section>
  );
};
