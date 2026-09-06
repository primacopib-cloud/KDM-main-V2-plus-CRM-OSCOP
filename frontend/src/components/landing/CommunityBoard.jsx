import { useEffect, useState } from 'react';
import { Search, Megaphone, Users } from 'lucide-react';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const STATUS_FR = { NEW: 'Nouvelle', ASSIGNED: 'En traitement', VENDOR_ACCEPTED: 'Offre reçue', VENDOR_DECLINED: 'En recherche', OFFER_ACCEPTED: 'Conclue' };

// Accueil : offres & demandes de produits publiées (CommunityPlace) avec drapeau du territoire
export const CommunityBoard = () => {
  const [demands, setDemands] = useState([]);
  const [q, setQ] = useState('');
  const [joinRef, setJoinRef] = useState(null);
  const [joinEmail, setJoinEmail] = useState('');
  const [joinQty, setJoinQty] = useState(3);
  const submitJoin = async (ref) => {
    if (!joinEmail.includes('@')) return toast.error('Email invalide');
    try {
      const r = await fetch(`${API_URL}/api/public/purchase-needs/${ref}/join`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: joinEmail, quantity: Number(joinQty) || 1 }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Erreur');
      setDemands((prev) => prev.map((x) => (x.reference === ref
        ? { ...x, joiners_count: d.joiners_count, joined_quantity: d.joined_quantity } : x)));
      setJoinRef(null); setJoinEmail('');
      toast.success('Vous avez rejoint la demande — volumes groupés !');
    } catch (e) { toast.error(e.message); }
  };
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
              <div className="mt-2" data-testid={`board-gauge-${d.reference}`}>
                <div className="flex justify-between text-[9px] text-white/45 mb-0.5">
                  <span>Volume groupé : {d.current_quantity}</span>
                  <span>Objectif : {d.goal_quantity}</span>
                </div>
                <div className="h-1.5 rounded-full bg-white/[0.08] overflow-hidden">
                  <div className="h-full rounded-full transition-[width] duration-700"
                    style={{ width: `${Math.min(100, Math.round((d.current_quantity / (d.goal_quantity || 1)) * 100))}%`,
                      background: 'linear-gradient(90deg, #8CC63E, #D9B35A)' }} />
                </div>
              </div>
              <div className="mt-2 flex items-center justify-between gap-2">
                <span className="text-[10px] text-white/45 inline-flex items-center gap-1">
                  <Users className="w-3 h-3" />
                  {d.joiners_count > 0 ? `${d.joiners_count} participant${d.joiners_count > 1 ? 's' : ''} · +${d.joined_quantity} qté groupée` : 'Groupez les volumes'}
                </span>
                {d.grouping_closed ? (
                  <span className="text-[10px] font-bold px-2 py-1 rounded-full bg-white/[0.06] text-white/50 border border-white/15" data-testid={`board-closed-${d.reference}`}>
                    Groupage clôturé
                  </span>
                ) : (
                <span className="flex items-center gap-1.5">
                <a data-testid={`board-share-${d.reference}`}
                  href={`https://wa.me/?text=${encodeURIComponent(`🤝 Rejoignez la demande d'achat groupée « ${d.product} » (${d.territory}) sur KDMARCHÉ — plus on est nombreux, meilleurs sont les prix ! Suivi ${d.reference} → ${window.location.origin}/?besoin=${d.reference}#community-board`)}`}
                  target="_blank" rel="noreferrer" title="Partager sur WhatsApp"
                  className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-[#25D366]/15 text-[#4be284] border border-[#25D366]/40 hover:bg-[#25D366]/30 transition-colors">
                  <svg viewBox="0 0 24 24" className="w-3.5 h-3.5 fill-current"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.297-.347.446-.52.149-.174.198-.298.297-.497.1-.198.05-.371-.025-.52-.074-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
                </a>
                <button type="button" data-testid={`board-join-${d.reference}`}
                  onClick={() => { setJoinRef(joinRef === d.reference ? null : d.reference); setJoinQty(3); }}
                  className="text-[10px] font-bold px-2 py-1 rounded-full bg-[#D9B35A]/15 text-[#E9CF8E] border border-[#D9B35A]/40 hover:bg-[#D9B35A]/25 transition-colors">
                  Rejoindre
                </button>
                </span>
                )}
              </div>
              {joinRef === d.reference && (
                <div className="mt-2 flex gap-1.5" data-testid={`board-join-form-${d.reference}`}>
                  <input value={joinEmail} onChange={(e) => setJoinEmail(e.target.value)} placeholder="votre@email.fr"
                    data-testid={`board-join-email-${d.reference}`}
                    className="h-8 flex-1 min-w-0 px-2 rounded-lg bg-white/[0.06] border border-white/15 text-white text-[11px] placeholder:text-white/35" />
                  <input type="number" min="1" value={joinQty} onChange={(e) => setJoinQty(e.target.value)}
                    data-testid={`board-join-qty-${d.reference}`}
                    className="h-8 w-14 px-1.5 rounded-lg bg-white/[0.06] border border-white/15 text-white text-[11px]" />
                  <button type="button" onClick={() => submitJoin(d.reference)} data-testid={`board-join-submit-${d.reference}`}
                    className="h-8 px-2.5 rounded-lg text-[11px] font-bold text-[#1F2A12] bg-[#D9B35A] hover:brightness-110 transition-[filter]">
                    OK
                  </button>
                </div>
              )}
            </div>
          ))}
          {!filtered.length && <p className="text-white/40 text-sm">Aucun résultat pour « {q} ».</p>}
        </div>
      </div>
    </section>
  );
};
