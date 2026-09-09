import { useEffect, useState } from 'react';
import { Megaphone, Package, Loader2, MapPin, Calendar, Users } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';

const STATUS_STYLE = {
  ASSIGNED: 'bg-[#D9B35A]/15 text-[#8a6d24] border-[#D9B35A]/40',
  VENDOR_ACCEPTED: 'bg-emerald-500/15 text-emerald-700 border-emerald-500/40',
  OFFER_ACCEPTED: 'bg-emerald-600/15 text-emerald-800 border-emerald-600/40',
  CLOSED: 'bg-black/5 text-black/50 border-black/10',
};
const fmtDate = (iso) => { try { return new Date(iso).toLocaleDateString('fr-FR'); } catch (_e) { return '—'; } };

// Onglet COOPER'S : besoins d'achat assignés à ce COOPER'S
export const CooperNeedsTab = () => {
  const [needs, setNeeds] = useState(null);
  const [respondFor, setRespondFor] = useState(null);
  const [resp, setResp] = useState({ price_eur: '', delay_days: '', note: '' });
  const [busy, setBusy] = useState(false);

  const load = () => {
    fetch(`${API}/cooper/purchase-needs`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((d) => setNeeds(d.needs))
      .catch(() => toast.error('Erreur de chargement des besoins assignés'));
  };
  useEffect(load, []);

  const sendResponse = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const r = await fetch(`${API}/cooper/purchase-needs/${respondFor.id}/respond`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({
          price_eur: Number(resp.price_eur),
          delay_days: resp.delay_days ? Number(resp.delay_days) : null,
          note: resp.note || null,
        }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Erreur');
      toast.success('Offre envoyée — demandeur et participants notifiés par email');
      setRespondFor(null);
      setResp({ price_eur: '', delay_days: '', note: '' });
      load();
    } catch (err) { toast.error(err.message); } finally { setBusy(false); }
  };

  return (
    <div className="glass-panel-soft rounded-[18px] p-5" data-testid="cooper-needs-tab">
      <h3 className="font-display text-lg mb-3 text-[#1F2A3A] flex items-center gap-2">
        <Megaphone className="w-4 h-4 text-[#6FA82E]" /> Besoins d'achat assignés
        {needs && <span className="text-xs font-body opacity-50">({needs.length})</span>}
      </h3>
      {!needs ? (
        <div className="py-6 flex justify-center"><Loader2 className="w-5 h-5 animate-spin opacity-40" /></div>
      ) : needs.length === 0 ? (
        <p className="text-sm opacity-50 py-3">Aucun besoin assigné pour le moment. La centrale vous notifiera par email dès qu'un besoin vous sera confié.</p>
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {needs.map((n) => (
            <div key={n.id} className="rounded-xl p-4 bg-white/60 border border-black/[0.06] shadow-sm" data-testid={`cooper-need-${n.reference}`}>
              <div className="flex items-start justify-between gap-2 mb-2">
                <div>
                  <p className="text-sm font-bold text-[#1F2A3A] m-0">{n.product}</p>
                  <p className="text-[10px] font-mono opacity-50 m-0">{n.reference}</p>
                </div>
                <span className={`text-[10px] uppercase font-semibold px-2 py-0.5 rounded-full border ${STATUS_STYLE[n.status] || 'bg-black/5 text-black/50 border-black/10'}`}>
                  {n.status}
                </span>
              </div>
              <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs opacity-70">
                <span className="inline-flex items-center gap-1"><Package className="w-3 h-3" /> Quantité : {n.quantity}</span>
                {n.territory && <span className="inline-flex items-center gap-1"><MapPin className="w-3 h-3" /> {n.territory}</span>}
                <span className="inline-flex items-center gap-1"><Calendar className="w-3 h-3" /> {fmtDate(n.created_at)}</span>
                {n.joiners_count > 0 && <span className="inline-flex items-center gap-1"><Users className="w-3 h-3" /> {n.joiners_count} participant(s)</span>}
              </div>
              {(n.contact_name || n.email) && (
                <p className="text-xs opacity-70 mt-2 m-0">Demandeur : {n.contact_name || '—'} {n.email ? `· ${n.email}` : ''}</p>
              )}
              {n.description && <p className="text-xs opacity-60 mt-1 m-0 italic">{n.description.slice(0, 140)}</p>}
              {(n.photos || []).length > 0 && (
                <div className="flex gap-2 mt-2">
                  {n.photos.slice(0, 4).map((ph, i) => (
                    <img key={i} src={ph.startsWith('http') ? ph : `${API}${ph}`} alt="" className="w-12 h-12 object-cover rounded-lg border border-black/10" />
                  ))}
                </div>
              )}
              {n.status === 'ASSIGNED' && (
                respondFor?.id === n.id ? (
                  <form onSubmit={sendResponse} className="mt-3 space-y-2" data-testid={`cooper-respond-form-${n.reference}`}>
                    <div className="grid grid-cols-2 gap-2">
                      <input required type="number" min="1" step="0.01" value={resp.price_eur}
                        onChange={(e) => setResp({ ...resp, price_eur: e.target.value })}
                        placeholder="Prix proposé (€) *" data-testid="cooper-respond-price"
                        className="h-9 px-2.5 rounded-lg text-sm bg-white/70 border border-black/10" />
                      <input type="number" min="1" value={resp.delay_days}
                        onChange={(e) => setResp({ ...resp, delay_days: e.target.value })}
                        placeholder="Délai (jours)" data-testid="cooper-respond-delay"
                        className="h-9 px-2.5 rounded-lg text-sm bg-white/70 border border-black/10" />
                    </div>
                    <input value={resp.note} onChange={(e) => setResp({ ...resp, note: e.target.value })}
                      placeholder="Note (optionnel)" data-testid="cooper-respond-note"
                      className="w-full h-9 px-2.5 rounded-lg text-sm bg-white/70 border border-black/10" />
                    <div className="flex gap-2">
                      <button type="submit" disabled={busy} data-testid="cooper-respond-submit"
                        className="px-3 py-1.5 rounded-lg text-xs font-bold text-white bg-[#6FA82E] disabled:opacity-60">
                        {busy ? '…' : "Envoyer l'offre"}
                      </button>
                      <button type="button" onClick={() => setRespondFor(null)}
                        className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-black/5">Annuler</button>
                    </div>
                  </form>
                ) : (
                  <button type="button" onClick={() => setRespondFor(n)} data-testid={`cooper-respond-btn-${n.reference}`}
                    className="mt-3 px-3 py-1.5 rounded-lg text-xs font-bold text-white bg-[#6FA82E] hover:opacity-90">
                    Répondre (prix & délai)
                  </button>
                )
              )}
              {n.vendor_price_eur && (
                <p className="text-xs font-semibold text-emerald-700 mt-2 m-0">
                  Offre envoyée : {n.vendor_price_eur} €{n.vendor_delay_days ? ` · ${n.vendor_delay_days} j` : ''}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
