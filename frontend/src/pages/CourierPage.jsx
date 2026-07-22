import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Truck, PenLine, RefreshCw, CheckCircle2, KeyRound, MapPin, Map } from 'lucide-react';
import { toast } from 'sonner';
import { CodSignatureDialog } from '../components/superadmin/CodSignatureDialog';
import LoloPointsMap from '../components/LoloPointsMap';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const eur = (c) => `${((c || 0) / 100).toFixed(2)} €`;
const ZONE_TO_TERRITORY = { GUADELOUPE: 'GP', MARTINIQUE: 'MQ', GUYANE: 'GF', REUNION: 'RE' };

export default function CourierPage() {
  const [params] = useSearchParams();
  const [token, setToken] = useState(params.get('token') || localStorage.getItem('courier_token') || '');
  const [courier, setCourier] = useState('');
  const [items, setItems] = useState(null);
  const [signOrder, setSignOrder] = useState(null);
  const [marking, setMarking] = useState(false);
  const [done, setDone] = useState([]);
  const [showMap, setShowMap] = useState(false);

  const load = useCallback(async (tk) => {
    if (!tk) return;
    const r = await fetch(`${API}/courier/orders?token=${encodeURIComponent(tk)}`);
    const d = await r.json();
    if (!r.ok) {
      setItems(null);
      return toast.error(d.detail || 'Accès invalide');
    }
    localStorage.setItem('courier_token', tk);
    setCourier(d.courier);
    setItems(d.items || []);
  }, []);
  useEffect(() => { if (token) load(token); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const collect = async ({ signature, signer_name, photo }) => {
    setMarking(true);
    const r = await fetch(`${API}/courier/orders/${signOrder.id}/collected?token=${encodeURIComponent(token)}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ signature, signer_name, photo }),
    });
    const d = await r.json();
    setMarking(false);
    if (!r.ok) return toast.error(d.detail || 'Encaissement impossible');
    setDone((prev) => [...prev, signOrder.id]);
    setSignOrder(null);
    toast.success(`${d.order_number} encaissée (${eur(d.amount_paid_cents)}) — reçu envoyé au client`);
    load(token);
  };

  return (
    <div className="min-h-screen text-white px-4 py-6" style={{ background: 'linear-gradient(160deg, #2A1045, #451F6B)' }} data-testid="courier-page">
      <div className="max-w-md mx-auto">
        <h1 className="text-xl font-display font-bold flex items-center gap-2 mb-1">
          <Truck size={20} className="text-[#D9B35A]" /> Espace livreur
        </h1>
        <p className="text-xs text-white/55 mb-5">
          {courier ? `Bonjour ${courier} — encaissements du jour à faire signer.` : 'Tournée du jour — paiements à la livraison.'}
        </p>

        {items === null ? (
          <div className="rounded-2xl p-5 bg-white/[0.05] border border-white/10 space-y-3">
            <p className="text-sm text-white/70 flex items-center gap-2"><KeyRound size={14} className="text-[#D9B35A]" /> Entrez votre code d'accès livreur (fourni par l'équipe)</p>
            <input value={token} onChange={(e) => setToken(e.target.value)} placeholder="Code d'accès"
              data-testid="courier-token-input"
              className="w-full h-11 px-3 rounded-lg bg-white/[0.06] border border-white/15 text-sm text-white placeholder:text-white/35 focus:outline-none focus:border-[#D9B35A]/60" />
            <button onClick={() => load(token)} data-testid="courier-token-submit"
              className="w-full h-11 rounded-lg text-sm font-semibold text-[#1A092D]"
              style={{ background: 'linear-gradient(135deg, #D9B35A, #F2D07A)' }}>
              Accéder à ma tournée
            </button>
          </div>
        ) : (
          <>
            <div className="flex items-center justify-between mb-3">
              <span className="px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-300 text-xs font-semibold" data-testid="courier-pending-count">
                {items.length} encaissement(s) à faire
              </span>
              <div className="flex items-center gap-2">
                <button onClick={() => setShowMap((v) => !v)} data-testid="courier-map-toggle"
                  className={`px-2.5 py-1.5 rounded-lg text-xs font-semibold inline-flex items-center gap-1.5 border transition-colors ${showMap
                    ? 'bg-[#D9B35A]/20 border-[#D9B35A]/40 text-[#E9CF8E]'
                    : 'bg-white/[0.06] border-white/10 text-white/70'}`}>
                  <Map size={13} /> Carte
                </button>
                <button onClick={() => load(token)} className="p-2 rounded-lg bg-white/[0.06] border border-white/10" title="Actualiser">
                  <RefreshCw size={14} />
                </button>
              </div>
            </div>
            {showMap && items.length > 0 && (
              <div className="mb-4" data-testid="courier-tour-map">
                <LoloPointsMap height="300px"
                  territory={ZONE_TO_TERRITORY[items[0]?.zone_code] || null}
                  points={items.filter((o) => o.lat != null && o.lng != null).map((o, i) => ({
                    id: o.id, code: o.order_number, name: `Arrêt ${i + 1} — ${o.pickup_name || o.order_number}`,
                    lat: o.lat, lng: o.lng, city: o.org_name, territory: String(i + 1),
                    zone_name: o.zone_code,
                  }))} />
                <p className="text-[10px] text-white/40 mt-1.5">Les marqueurs suivent l'ordre optimisé de la tournée (1 → {items.length}).</p>
              </div>
            )}
            <div className="space-y-3">
              {items.map((o, idx) => (
                <div key={o.id}>
                  {(idx === 0 || (items[idx - 1].zone_code || '') !== (o.zone_code || '')) && (
                    <p className="text-[11px] font-bold uppercase tracking-wider text-[#E9CF8E] flex items-center gap-1.5 mb-2 mt-1" data-testid={`courier-zone-${o.zone_code || 'autre'}`}>
                      <MapPin size={11} /> {o.zone_code || 'Zone non précisée'}
                      <span className="text-white/40 font-normal normal-case">({items.filter((x) => (x.zone_code || '') === (o.zone_code || '')).length} arrêt(s))</span>
                    </p>
                  )}
                  <div className="rounded-2xl p-4 bg-white/[0.05] border border-white/10" data-testid={`courier-order-${o.id}`}>
                    <div className="flex items-center justify-between mb-1">
                      <p className="text-sm font-semibold">{o.order_number}</p>
                      <p className="text-lg font-bold text-[#E9CF8E]">{eur(o.cod_amount_due_cents || o.total_ttc_cents)}</p>
                    </div>
                    {(o.org_name || o.pickup_name) && (
                      <p className="text-xs text-white/55 mb-3">
                        {o.org_name}{o.pickup_name ? ` · 📍 ${o.pickup_name}` : ''}
                      </p>
                    )}
                    <button onClick={() => setSignOrder(o)} data-testid={`courier-collect-btn-${o.id}`}
                      className="w-full h-11 rounded-xl text-sm font-semibold text-[#1A092D] inline-flex items-center justify-center gap-2"
                      style={{ background: 'linear-gradient(135deg, #D9B35A, #F2D07A)' }}>
                      <PenLine size={15} /> Encaisser + faire signer
                    </button>
                  </div>
                </div>
              ))}
              {!items.length && (
                <div className="rounded-2xl p-8 bg-white/[0.04] border border-white/10 text-center" data-testid="courier-empty">
                  <CheckCircle2 size={36} className="mx-auto text-emerald-300 mb-2" />
                  <p className="text-sm text-white/70">Tournée terminée — aucun encaissement en attente. Bravo !</p>
                  {done.length > 0 && <p className="text-xs text-white/45 mt-1">{done.length} encaissement(s) réalisés dans cette session.</p>}
                </div>
              )}
            </div>
          </>
        )}
      </div>
      <CodSignatureDialog open={!!signOrder} onClose={() => setSignOrder(null)} order={signOrder}
        onConfirm={collect} loading={marking} />
    </div>
  );
}
