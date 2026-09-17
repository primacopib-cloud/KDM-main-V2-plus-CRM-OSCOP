import { Link } from 'react-router-dom';
import { Store, Gavel, Coins, Globe2, QrCode, CalendarClock, BadgePercent, ArrowRight } from 'lucide-react';

const FEATURES = [
  { icon: Gavel, t: 'Accès à la salle COOP\'ACT', d: 'Vos lots entrent dans la Bourse Coopérative à prix descendant : les Coop\'acteurs remportent vos invendus à la juste valeur.' },
  { icon: Coins, t: '3 offres incluses / mois', d: 'L\'abonnement à 390 €/mois inclut 3 offres de lots. Au-delà : 100 crédits par lot supplémentaire. Dépôt : 2,5 % de la valeur du lot.' },
  { icon: BadgePercent, t: 'Réduction minimum −15 %', d: 'Chaque lot ×3 (même produit ou composé) est proposé avec au moins 15 % de réduction, en % ou en montant, dans votre devise.' },
  { icon: Globe2, t: 'Monde entier — 4 langues', d: 'Raison sociale, localité, pays avec drapeau, 59 devises internationales. Interface en français, anglais, espagnol et créole.' },
  { icon: CalendarClock, t: 'Programmation & countdown', d: 'Programmez vos offres à la date voulue : le compte à rebours attire les Coop\'acteurs avant l\'ouverture.' },
  { icon: QrCode, t: 'Enlèvement sécurisé par QR', d: 'Le gagnant présente son QR unique à l\'enlèvement selon vos créneaux : remise du lot tracée et confirmée.' },
];

export default function DetaillantConceptPage() {
  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white" data-testid="detaillant-concept-page">
      <div className="max-w-5xl mx-auto px-6 py-14">
        <div className="flex items-center gap-2 text-[#D9B35A] text-xs font-bold uppercase tracking-[0.2em]">
          <Store className="w-4 h-4" /> KDMARCHÉ × O'SCOP — Espace Détaillant
        </div>
        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black mt-4 leading-tight">
          Écoulez vos lots en boutique<br />
          <span className="text-[#E9CF8E]">sur la Bourse COOP'ACT</span>
        </h1>
        <p className="text-base text-white/60 mt-5 max-w-2xl">
          Détaillants du monde entier : déposez vos lots ×3 issus du catalogue LOLODRIVE en vigueur,
          fixez votre réduction (−15 % minimum) et laissez les Coop'acteurs remporter vos offres
          au prix juste. Validation par notre équipe, retrait en boutique selon vos créneaux.
        </p>
        <div className="flex flex-wrap gap-3 mt-8">
          <Link to="/espace-detaillant" data-testid="concept-cta-join"
            className="inline-flex items-center gap-2 px-6 h-11 rounded-full bg-[#D9B35A] text-black text-sm font-bold hover:bg-[#E9CF8E]">
            Devenir détaillant — 390 €/mois <ArrowRight className="w-4 h-4" />
          </Link>
          <Link to="/coopact" data-testid="concept-cta-coopact"
            className="inline-flex items-center gap-2 px-6 h-11 rounded-full border border-white/20 text-sm font-semibold hover:bg-white/5">
            Découvrir COOP'ACT
          </Link>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 mt-14">
          {FEATURES.map((fx) => (
            <div key={fx.t} className="rounded-2xl border border-white/10 bg-white/[0.03] p-5" data-testid="concept-feature">
              <fx.icon className="w-5 h-5 text-[#D9B35A]" />
              <p className="text-sm font-bold mt-2">{fx.t}</p>
              <p className="text-xs text-white/55 mt-1 leading-relaxed">{fx.d}</p>
            </div>
          ))}
        </div>
        <div className="rounded-2xl border border-[#D9B35A]/30 bg-[#D9B35A]/5 p-6 mt-12">
          <p className="text-sm font-bold text-[#E9CF8E]">Comment ça marche ?</p>
          <ol className="text-xs text-white/60 mt-2 space-y-1.5 list-decimal list-inside">
            <li>Inscrivez votre boutique (raison sociale, localité, pays, créneaux d'enlèvement).</li>
            <li>Activez l'abonnement Détaillant à 390 €/mois — 3 offres de lots incluses chaque mois.</li>
            <li>Choisissez un produit du catalogue LOLODRIVE, composez votre lot ×3 et fixez la réduction (min. −15 %).</li>
            <li>Le dépôt coûte 2,5 % de la valeur du lot en crédits COOP'ACT (+100 crédits/lot au-delà des 3 offres).</li>
            <li>Après validation, votre lot part en salle avec countdown ; le gagnant retire son lot avec son QR.</li>
          </ol>
        </div>
      </div>
    </div>
  );
}
