import { Truck, Store, ShieldCheck, Headphones } from 'lucide-react';

const SERVICES = [
  { icon: Truck, title: 'Livraison coordonnée', color: '#8CC63E', audiences: ['pro'],
    tagline: 'Transport mutualisé',
    desc: 'Tournées LOGI\'SCOP partagées entre acheteurs : moins de kilomètres, des coûts de transport réduits pour chacun.' },
  { icon: Store, title: 'Retrait Drive', color: '#5B9BD5', audiences: ['particuliers'],
    tagline: 'Points relais LOLODRIVE',
    desc: 'Commandez en ligne et récupérez vos lots ×3 dans le point relais LOLODRIVE le plus proche, quand cela vous arrange.' },
  { icon: ShieldCheck, title: 'Paiement sécurisé', color: '#D9B35A', audiences: ['pro', 'particuliers'],
    tagline: 'Payez à votre rythme',
    desc: 'Stripe, CREDI\'SCOP ou Règlement à Réception Pro : choisissez le mode de paiement adapté, en toute sécurité.' },
  { icon: Headphones, title: 'Assistance dédiée', color: '#B58CD9', audiences: ['pro', 'particuliers'],
    tagline: 'Une équipe à vos côtés',
    desc: 'La coopérative vous accompagne sur vos commandes, litiges et approvisionnements — réponse rapide garantie.' },
];

// Bloc des services — filtré par audience (pro : accueil Centrale, particuliers : accueil LOLODRIVE)
export const ServicesBlock = ({ audience = 'pro' }) => (
  <section className="max-w-[1160px] mx-auto px-5 mb-14" aria-label="Services KDMARCHÉ" data-testid="kdm-services-block">
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {SERVICES.filter((s) => s.audiences.includes(audience)).map(({ icon: Icon, title, color, tagline, desc }) => (
        <div key={title} className="glass-panel-soft rounded-[20px] p-6" data-testid={`kdm-service-${title.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`}>
          <div className="flex items-center gap-3 mb-3">
            <div className="w-11 h-11 rounded-xl flex items-center justify-center shrink-0"
              style={{ background: `${color}1c`, border: `1px solid ${color}55` }}>
              <Icon className="w-5 h-5" style={{ color }} aria-hidden="true" />
            </div>
            <div>
              <h3 className="font-display text-lg leading-tight m-0" style={{ color }}>{title}</h3>
              <p className="text-[11px] uppercase tracking-wide text-white/40 m-0">{tagline}</p>
            </div>
          </div>
          <p className="text-sm leading-relaxed text-white/75 m-0">{desc}</p>
        </div>
      ))}
    </div>
  </section>
);
