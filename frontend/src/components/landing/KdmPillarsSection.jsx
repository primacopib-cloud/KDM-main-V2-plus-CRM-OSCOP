import { Store, ShoppingBag } from 'lucide-react';

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

export const KdmPillarsSection = () => (
  <section className="max-w-[1160px] mx-auto px-5 grid md:grid-cols-2 gap-4 mb-14">
    <Pillar
      icon={Store} title="Vendeurs référencés" color="#8CC63E" testId="kdm-pillar-vendors"
      items={[
        'Soumettez vos fiches produits avec photos et Studio IA intégré',
        'Accédez à la demande agrégée des acheteurs pro des Outre-mer',
        'Circuit de validation qualité par la coopérative',
        'Visibilité multi-territoires : Antilles, Guyane, Réunion, Mayotte',
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
);
