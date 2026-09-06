import { useEffect, useState } from 'react';
import { Search, Megaphone } from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const STATUS_FR = { NEW: 'Nouvelle', ASSIGNED: 'En traitement', VENDOR_ACCEPTED: 'Offre reçue', VENDOR_DECLINED: 'En recherche', OFFER_ACCEPTED: 'Conclue' };

// Accueil : offres & demandes de produits publiées (CommunityPlace) avec drapeau du territoire
export const CommunityBoard = () => {
  const [demands, setDemands] = useState([]);
  const [q, setQ] = useState('');
  useEffect(() => {
    fetch(`${API_URL}/api/public/community-board`)
      .then((r) => (r.ok ? r.json() : { demands: [] })).then((d) => setDemands(d.demands || [])).catch(() => {});
  }, []);
  if (!demands.length) return null;
  const ql = q.trim().toLowerCase();
  const filtered = ql ? demands.filter((d) => `${d.product} ${d.territory} ${d.reference}`.toLowerCase().includes(ql)) : demands;
  return (
    <section className="py-10 px-5" data-testid="community-board">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center gap-3 flex-wrap mb-5">
          <h2 className="text-lg md:text-lg font-bold m-0 flex items-center gap-2" style={{ color: '#F7F2E9' }}>
            <Megaphone className="w-5 h-5 text-[#D9B35A]" /> Offres & demandes de produits
          </h2>
          <div className="relative ml-auto w-full sm:w-72">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-white/40" />
            <input value={q} onChange={(e) => setQ(e.target.value)} data-testid="community-board-search"
              placeholder="Rechercher un produit, un territoire…"
              className="h-10 w-full pl-9 pr-3 rounded-xl bg-white/[0.06] border border-white/15 text-white text-sm placeholder:text-white/35" />
          </div>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((d) => (
            <div key={d.reference} className="rounded-2xl p-4 bg-white/[0.03] border border-white/[0.08] hover:border-[#D9B35A]/40 transition-colors"
              data-testid={`board-demand-${d.reference}`}>
              <div className="flex items-center gap-2">
                <img src={`https://flagcdn.com/w40/${d.flag.toLowerCase()}.png`} alt={d.territory} width={24} height={16} className="rounded-[2px]" />
                <span className="text-white font-semibold text-sm truncate">{d.product}</span>
              </div>
              <p className="text-[11px] text-white/50 m-0 mt-1.5">Demande {d.reference} · qté {d.quantity} · {d.territory}</p>
              <span className="inline-block mt-2 px-2 py-0.5 rounded-full text-[10px] font-semibold text-[#E9CF8E] bg-white/[0.05] border border-[#D9B35A]/30">
                {STATUS_FR[d.status] || d.status}
              </span>
            </div>
          ))}
          {!filtered.length && <p className="text-white/40 text-sm">Aucun résultat pour « {q} ».</p>}
        </div>
      </div>
    </section>
  );
};
