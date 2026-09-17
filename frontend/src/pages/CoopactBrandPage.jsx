import { Link } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { Gavel, Handshake, Scale, Coins, ShieldCheck, ArrowRight, Sparkles, Users } from 'lucide-react';
import { API } from '../services/http';

// Historique public des lots vedettes de chaque semaine (les plus coop'actés)
const WeeklyStarsSection = () => {
  const [stars, setStars] = useState([]);
  useEffect(() => {
    fetch(`${API}/auctions/weekly-stars`).then((r) => (r.ok ? r.json() : { stars: [] }))
      .then((d) => setStars(d.stars || [])).catch(() => {});
  }, []);
  if (stars.length === 0) return null;
  return (
    <div className="mb-10 text-left" data-testid="weekly-stars-section">
      <h2 className="text-base md:text-lg font-black text-[#F2D07A] mb-3 flex items-center gap-2">
        🏆 Lots vedettes des semaines passées
      </h2>
      <div className="grid gap-2" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))' }}>
        {stars.map((s) => (
          <div key={s.week_key} data-testid={`weekly-star-${s.week_key}`}
            className="rounded-xl border border-[#D9B35A]/30 bg-[#D9B35A]/[0.06] p-3 flex items-center gap-2.5">
            {s.image_url && (
              <img src={s.image_url.startsWith('/api/') ? `${API}${s.image_url.slice(4)}` : s.image_url}
                alt={s.title} className="w-11 h-11 rounded-lg object-cover bg-white/90 shrink-0" />
            )}
            <div className="min-w-0">
              <p className="text-[10px] font-black uppercase tracking-wide text-[#D9B35A]">Semaine {s.week_key}</p>
              <p className="text-[11px] font-bold text-white/85 truncate" title={s.title}>{s.title}</p>
              <p className="text-[10px] text-white/50">{s.week_bids} Coop'Act · {Number(s.price_eur).toFixed(2)} €</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

const LEXIQUE = [
  { term: "Coop'acter", def: "L'action : déposer ou améliorer une offre responsable au sein de la Bourse Coopérative." },
  { term: "Coop'Act", def: 'La proposition déposée par un participant.' },
  { term: "Coop'acteur", def: 'Le participant qui agit au sein de la Bourse Coopérative.' },
  { term: "Améliorer mon Coop'Act", def: 'Déposer une nouvelle proposition plus juste que la précédente.' },
  { term: "Coop'actez votre offre", def: "L'instruction : engagez votre proposition pour la juste valeur." },
];

const STEPS = [
  { icon: ShieldCheck, title: '1 · Je rejoins', text: "J'active mon plan CREDI'SCOP-COOP'ACT : il ouvre l'accès à la salle et alimente mes crédits d'action." },
  { icon: Gavel, title: "2 · Je coop'acte", text: 'Chaque Coop\'Act engage mes crédits et fait évoluer le prix vers sa juste valeur, en toute transparence.' },
  { icon: Handshake, title: '3 · La juste valeur', text: 'Le premier qui accepte le prix affiché remporte le lot. Ni spéculation, ni surenchère : une valeur juste, décidée ensemble.' },
];

const VALEURS = [
  { icon: Users, title: 'Coopération', text: "Chaque Coop'acteur participe à la formation du prix : la valeur naît de l'action collective, pas de la rareté artificielle." },
  { icon: Scale, title: 'Juste valeur', text: 'Le prix descend vers son point d\'équilibre. Les documents contractuels conservent la formulation juridique claire : « soumettre ou améliorer une offre », dénommé commercialement "Coop\'acter".' },
  { icon: Coins, title: 'Engagement', text: "Les crédits coop'actés sont définitivement engagés — ils ne sont pas remboursés si vous ne remportez pas le lot. C'est cet engagement qui donne sa valeur à chaque action." },
];

export default function CoopactBrandPage() {
  const [stats, setStats] = useState(null);
  useEffect(() => {
    fetch(`${API}/auctions/community-stats`).then((r) => r.json()).then(setStats).catch(() => {});
  }, []);
  return (
    <div className="min-h-screen text-white" data-testid="coopact-brand-page"
      style={{ background: 'linear-gradient(180deg, #1E0C34 0%, #3D1B61 55%, #22103C 100%)' }}>
      <header className="max-w-5xl mx-auto px-5 pt-14 pb-10">
        <p className="text-[11px] font-bold tracking-[0.25em] text-[#D9B35A] uppercase mb-4" data-testid="coopact-kicker">
          O'SCOP × KDMARCHÉ · LOLODRIVE
        </p>
        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold leading-tight" data-testid="coopact-hero-title">
          BOURSE COOPÉRATIVE
          <span className="block text-[#F2D07A]">— COOP'ACT</span>
        </h1>
        <p className="text-lg text-white/85 mt-4 max-w-2xl" data-testid="coopact-hero-signature">
          Agir ensemble pour la juste valeur.
        </p>
        <p className="text-sm text-white/65 mt-3 max-w-2xl">
          COOP'ACT est un nom court, moderne et dynamique qui associe coopération, action et engagement.
          Un COOP'ACT, c'est l'action par laquelle un participant dépose ou améliore une offre responsable
          au sein de la Bourse Coopérative.
        </p>
        <div className="flex flex-wrap gap-3 mt-7">
          <Link to="/encheres" data-testid="coopact-cta-room"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-bold text-[#2A1045] on-gold transition-transform hover:scale-[1.03]"
            style={{ background: 'linear-gradient(135deg, #D9B35A, #F2D07A)' }}>
            Entrer dans la salle COOP'ACT <ArrowRight className="w-4 h-4" />
          </Link>
          <Link to="/pass-lolodrive" data-testid="coopact-cta-pass"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-bold border border-white/25 text-white/85 hover:bg-white/10 transition-colors">
            Découvrir LOLODRIVE
          </Link>
        </div>
        {stats && (
          <div className="flex flex-wrap gap-6 mt-8" data-testid="coopact-community-stats">
            {[
              [stats.coopacteurs, "Coop'acteur(s) actif(s)", 'stat-coopacteurs'],
              [stats.lots_won, 'lot(s) remporté(s)', 'stat-lots-won'],
              [stats.total_bids, "Coop'Act(s) déposés", 'stat-total-coopacts'],
            ].map(([v, label, tid]) => (
              <div key={tid} data-testid={tid}>
                <div className="text-3xl font-bold text-[#F2D07A]">{v}</div>
                <div className="text-[11px] uppercase tracking-wide text-white/55">{label}</div>
              </div>
            ))}
          </div>
        )}
      </header>

      <section className="max-w-5xl mx-auto px-5 py-8" data-testid="coopact-steps">
        <h2 className="text-lg font-bold text-[#E9CF8E] mb-5 flex items-center gap-2">
          <Sparkles className="w-4 h-4" /> Comment ça marche ?
        </h2>
        <div className="grid gap-4 sm:grid-cols-3">
          {STEPS.map((s) => (
            <div key={s.title} className="rounded-2xl bg-white/[0.05] border border-white/10 p-5">
              <s.icon className="w-6 h-6 text-[#D9B35A] mb-3" />
              <h3 className="text-sm font-bold text-white mb-1.5">{s.title}</h3>
              <p className="text-xs text-white/70 leading-relaxed">{s.text}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="max-w-5xl mx-auto px-5 py-8" data-testid="coopact-values">
        <h2 className="text-lg font-bold text-[#E9CF8E] mb-5 flex items-center gap-2">
          <Handshake className="w-4 h-4" /> Nos trois engagements
        </h2>
        <div className="grid gap-4 sm:grid-cols-3">
          {VALEURS.map((v) => (
            <div key={v.title} className="rounded-2xl border border-[#D9B35A]/25 bg-[#D9B35A]/[0.06] p-5">
              <v.icon className="w-6 h-6 text-[#F2D07A] mb-3" />
              <h3 className="text-sm font-bold text-[#F2D07A] mb-1.5">{v.title}</h3>
              <p className="text-xs text-white/75 leading-relaxed">{v.text}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="max-w-5xl mx-auto px-5 py-8" data-testid="coopact-lexique">
        <h2 className="text-lg font-bold text-[#E9CF8E] mb-5 flex items-center gap-2">
          <Scale className="w-4 h-4" /> Le langage COOP'ACT
        </h2>
        <div className="rounded-2xl bg-white/[0.04] border border-white/10 divide-y divide-white/10">
          {LEXIQUE.map((l) => (
            <div key={l.term} className="p-4 flex flex-col sm:flex-row sm:items-baseline gap-1 sm:gap-5">
              <span className="text-sm font-bold text-[#F2D07A] sm:w-56 shrink-0">{l.term}</span>
              <span className="text-xs text-white/75">{l.def}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="max-w-5xl mx-auto px-5 py-8" data-testid="coopact-universes">
        <h2 className="text-lg font-bold text-[#E9CF8E] mb-5 flex items-center gap-2">
          <Users className="w-4 h-4" /> Deux univers, une même philosophie
        </h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="rounded-2xl bg-white/[0.05] border border-white/10 p-5">
            <h3 className="text-sm font-bold text-white mb-1.5">Professionnels — Bourse COOP'ACT</h3>
            <p className="text-xs text-white/70 leading-relaxed">
              Consultations compétitives entre acheteurs et fournisseurs : chaque vendeur coop'acte son offre,
              à rang anonyme, jusqu'à la juste valeur. Offres scellées lorsque la loi l'exige (art. L.442-8).
            </p>
          </div>
          <div className="rounded-2xl bg-white/[0.05] border border-white/10 p-5">
            <h3 className="text-sm font-bold text-white mb-1.5">Particuliers — Salle COOP'ACT LOLODRIVE</h3>
            <p className="text-xs text-white/70 leading-relaxed">
              Des lots du quotidien à prix descendant : chaque Coop'Act fait baisser le prix,
              le premier qui accepte remporte le lot. Retrait en relais LOLODRIVE ou livraison.
            </p>
          </div>
        </div>
        <div className="mt-6 rounded-2xl border border-amber-300/30 bg-amber-400/[0.07] p-4" data-testid="coopact-rule">
          <p className="text-xs text-amber-100/90 leading-relaxed">
            <b>Règle d'engagement :</b> les crédits coop'actés sont définitivement engagés, que vous remportiez
            le lot ou non. Les crédits CREDI'SCOP-COOP'ACT sont des unités internes de services : ils ne
            constituent ni un solde financier, ni un moyen de paiement.
          </p>
        </div>
      </section>

      <footer className="max-w-5xl mx-auto px-5 py-10 text-center text-[11px] text-white/45">
        <WeeklyStarsSection />
        <p className="font-bold text-[#D9B35A]">BOURSE COOPÉRATIVE — COOP'ACT</p>
        <p>Agir ensemble pour la juste valeur.</p>
        <p className="mt-2">O'SCOP × KDMARCHÉ — CommunityPlace</p>
      </footer>
    </div>
  );
}
