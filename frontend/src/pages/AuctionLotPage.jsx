import { useCallback, useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Gavel, ArrowRight } from 'lucide-react';
import { API, getAuthHeaders, getSessionToken } from '../services/http';
import LolodriveLayout from '../components/LolodriveLayout';
import { AuctionCard } from '../components/auctions/AuctionCard';

export default function AuctionLotPage() {
  const { reference } = useParams();
  const [lot, setLot] = useState(undefined);
  const [me, setMe] = useState(null);
  const isLogged = Boolean(getSessionToken());

  const load = useCallback(async () => {
    const res = await fetch(`${API}/auctions/public/lot/${encodeURIComponent(reference)}`);
    setLot(res.ok ? await res.json() : null);
  }, [reference]);

  useEffect(() => {
    load();
    const id = setInterval(load, 10000);
    return () => clearInterval(id);
  }, [load]);

  useEffect(() => {
    if (!isLogged) return;
    fetch(`${API}/auctions/me`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null)).then(setMe).catch(() => {});
  }, [isLogged]);

  return (
    <LolodriveLayout title="Lot COOP'ACT" subtitle={lot?.title || ''}>
      <div data-testid="auction-lot-page" className="max-w-sm mx-auto">
        {lot === undefined && <div className="text-center text-white/40 py-14">Chargement…</div>}
        {lot === null && (
          <div className="text-center text-white/40 py-14" data-testid="auction-lot-not-found">
            <Gavel className="w-8 h-8 mx-auto mb-2 opacity-40" />
            Lot introuvable ou retiré de la salle.
          </div>
        )}
        {lot && <AuctionCard auction={lot} canBid={Boolean(me?.active)} onChanged={load} />}
        <div className="mt-5 text-center">
          <Link to="/encheres" data-testid="auction-lot-back-link"
            className="inline-flex items-center gap-1.5 text-sm font-semibold text-[#F2D07A] hover:underline">
            Voir toute la salle COOP'ACT <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </div>
    </LolodriveLayout>
  );
}
