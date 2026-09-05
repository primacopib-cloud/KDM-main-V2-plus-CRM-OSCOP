import { CreditCard, Ticket, Euro, RefreshCcw, XCircle, CheckCircle2 } from 'lucide-react';

const COMPARTMENTS = [
  { icon: CreditCard, title: "Abonnement mensuel O'SCOP", desc: 'Accès aux services de la centrale, facturé en euros.' },
  { icon: Ticket, title: "Compteur d'unités de services CREDI'SCOP-I", desc: 'Active les services internes coopératifs. Sans valeur monétaire.' },
  { icon: Euro, title: 'Investissements réels', desc: 'En euros ou devises, ils financent les opérations d\'achat-revente.' },
  { icon: RefreshCcw, title: 'Remboursements par opération', desc: 'Ventilés selon la cascade d\'encaissement de chaque opération.' },
];

const CAN = ['Data room', 'Qualification fournisseur', 'Analyse économique', 'Analyse logistique', "Bon d'Engagement", 'Workflow de paiement', 'Reporting', 'Clôture'];
const CANNOT = [
  'Payer un produit', 'Payer la logistique', 'Être convertis en monnaie',
  'Être transférés à un fournisseur', 'Être chargés sur une carte',
  'Générer un rendement', 'Représenter le montant investi',
];

export const FinancingCompartments = () => (
  <section className="py-8 px-5" data-testid="financing-compartments">
    <div className="max-w-[1160px] mx-auto">
      <div className="section-title mb-5">
        <div>
          <h2 className="text-[24px] font-bold tracking-tight m-0">Financement : quatre compartiments séparés</h2>
          <p className="text-[#D9B35A] text-sm mt-1 m-0 font-semibold">
            Les CREDI'SCOP-I activent les services internes. Les euros ou devises financent l'opération.
          </p>
        </div>
      </div>
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3.5 mb-5">
        {COMPARTMENTS.map((c) => (
          <div key={c.title} className="glass-panel-soft rounded-[18px] p-5">
            <c.icon className="w-5 h-5 text-[#D9B35A] mb-2.5" />
            <h3 className="text-sm font-bold text-white m-0 mb-1.5">{c.title}</h3>
            <p className="text-white/65 text-[12.5px] m-0">{c.desc}</p>
          </div>
        ))}
      </div>
      <div className="grid md:grid-cols-2 gap-3.5">
        <div className="glass-panel-soft rounded-[18px] p-5">
          <h4 className="text-sm tracking-wider uppercase text-[#A9D96C] font-semibold mb-3 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4" /> Les CREDI'SCOP-I peuvent activer
          </h4>
          <div className="flex flex-wrap gap-2">
            {CAN.map((s) => (
              <span key={s} className="px-2.5 py-1 rounded-full bg-white/[0.05] border border-white/10 text-white/80 text-xs">{s}</span>
            ))}
          </div>
        </div>
        <div className="glass-panel-soft rounded-[18px] p-5">
          <h4 className="text-sm tracking-wider uppercase text-[#E88] font-semibold mb-3 flex items-center gap-2">
            <XCircle className="w-4 h-4" /> Ils ne peuvent jamais
          </h4>
          <div className="space-y-1.5">
            {CANNOT.map((s) => (
              <div key={s} className="flex items-center gap-2 text-white/75 text-[13px]">
                <div className="cross-icon"></div><span>{s}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  </section>
);
