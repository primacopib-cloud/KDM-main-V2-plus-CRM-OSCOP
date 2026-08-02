import { Truck, Store, ShieldCheck, Headphones } from 'lucide-react';

const SERVICES = [
  { icon: Truck, title: 'Livraison coordonnée', color: '#8CC63E',
    desc: 'Tournées LOGI\'SCOP mutualisées entre acheteurs pour réduire les coûts de transport.' },
  { icon: Store, title: 'Retrait Drive', color: '#5B9BD5',
    desc: 'Récupérez vos commandes en points relais LOLODRIVE partout sur votre territoire.' },
  { icon: ShieldCheck, title: 'Paiement sécurisé', color: '#D9B35A',
    desc: 'Stripe, Credi\'SCOP et Règlement à Réception Pro : payez selon vos besoins, en toute sécurité.' },
  { icon: Headphones, title: 'Assistance dédiée', color: '#B58CD9',
    desc: 'Une équipe coopérative à votre écoute pour vos commandes, litiges et approvisionnements.' },
];

// Bloc des quatre services professionnels — page /kdmarche
export const ServicesBlock = () => (
  <section className="max-w-[1160px] mx-auto px-5 mb-14" aria-label="Services professionnels KDMARCHÉ" data-testid="kdm-services-block">
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {SERVICES.map(({ icon: Icon, title, color, desc }) => (
        <div key={title} className="glass-panel-soft rounded-[20px] p-6" data-testid={`kdm-service-${title.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`}>
          <div className="w-11 h-11 rounded-xl flex items-center justify-center mb-4"
            style={{ background: `${color}1c`, border: `1px solid ${color}55` }}>
            <Icon className="w-5 h-5" style={{ color }} aria-hidden="true" />
          </div>
          <h3 className="font-display text-lg mb-2" style={{ color }}>{title}</h3>
          <p className="text-sm text-white/70 m-0">{desc}</p>
        </div>
      ))}
    </div>
  </section>
);
