import { Truck, Store, ShieldCheck, Headphones } from 'lucide-react';
import i18n from '@/i18n';

const SERVICES = [
  { icon: Truck, id: 'livraison-coordonnee', k: 's1', color: '#8CC63E', audiences: ['pro'] },
  { icon: Store, id: 'retrait-drive', k: 's2', color: '#5B9BD5', audiences: ['particuliers'] },
  { icon: ShieldCheck, id: 'paiement-securise', k: 's3', color: '#D9B35A', audiences: ['pro', 'particuliers'] },
  { icon: Headphones, id: 'assistance-dediee', k: 's4', color: '#B58CD9', audiences: ['pro', 'particuliers'] },
];

// Bloc des services — filtré par audience (pro : accueil Centrale, particuliers : accueil LOLODRIVE)
export const ServicesBlock = ({ audience = 'pro' }) => (
  <section className="max-w-[1160px] mx-auto px-5 mb-14" aria-label="Services KDMARCHÉ" data-testid="kdm-services-block">
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {SERVICES.filter((s) => s.audiences.includes(audience)).map(({ icon: Icon, id, k, color }) => (
        <div key={id} className="glass-panel-soft rounded-[20px] p-6" data-testid={`kdm-service-${id}`}>
          <div className="flex items-center gap-3 mb-3">
            <div className="w-11 h-11 rounded-xl flex items-center justify-center shrink-0"
              style={{ background: `${color}1c`, border: `1px solid ${color}55` }}>
              <Icon className="w-5 h-5" style={{ color }} aria-hidden="true" />
            </div>
            <div>
              <h3 className="font-display text-lg leading-tight m-0" style={{ color }}>{i18n.t(`home.services.${k}_title`)}</h3>
              <p className="text-[11px] uppercase tracking-wide text-white/40 m-0">{i18n.t(`home.services.${k}_tag`)}</p>
            </div>
          </div>
          <p className="text-sm leading-relaxed text-white/75 m-0">{i18n.t(`home.services.${k}_desc`)}</p>
        </div>
      ))}
    </div>
  </section>
);
