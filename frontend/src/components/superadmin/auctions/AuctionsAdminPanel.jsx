import { useCallback, useEffect, useState } from 'react';
import { Gavel, Plus, Settings2, XCircle, Pencil } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../../services/http';
import { Button } from '../../ui/button';
import { Badge } from '../../ui/badge';
import { Countdown } from '../../auctions/AuctionCard';
import { AuctionFormDialog } from './AuctionFormDialog';
import { AuctionSettingsDialog } from './AuctionSettingsDialog';
import { AuctionStats } from './AuctionStats';

const STATUS_STYLE = {
  SCHEDULED: 'bg-sky-500/20 text-sky-300', LIVE: 'bg-emerald-500/20 text-emerald-300',
  WON: 'bg-[#D9B35A]/20 text-[#E9CF8E]', EXPIRED: 'bg-white/10 text-white/50',
  CANCELLED: 'bg-red-500/20 text-red-300',
};
const REC_LABELS = { NONE: '', DAILY: '🔁 Quotidienne', MONTHLY: '🔁 Mensuelle', YEARLY: '🔁 Annuelle' };

export const AuctionsAdminPanel = () => {
  const [data, setData] = useState({ items: [], labels: {} });
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [settingsOpen, setSettingsOpen] = useState(false);

  const load = useCallback(async () => {
    const res = await fetch(`${API}/admin/auctions`, { headers: getAuthHeaders(), credentials: 'include' });
    if (res.ok) setData(await res.json());
  }, []);

  useEffect(() => { load(); }, [load]);

  const cancel = async (a) => {
    const res = await fetch(`${API}/admin/auctions/${a.id}/cancel`, {
      method: 'POST', headers: getAuthHeaders(), credentials: 'include' });
    const d = await res.json();
    if (!res.ok) { toast.error(d.detail || 'Erreur'); return; }
    toast.success(`COOP'ACT ${a.reference} annulé`);
    load();
  };

  return (
    <div className="glass-panel-soft rounded-[22px] p-5 mt-6" data-testid="auctions-admin-panel">
      <div className="flex items-center justify-between flex-wrap gap-3 mb-1">
        <div>
          <h3 className="text-lg font-bold text-white flex items-center gap-2">
            <Gavel className="w-5 h-5 text-[#D9B35A]" /> COOP'ACT produits — prix descendant
          </h3>
          <p className="text-white/60 text-xs mt-1">
            BOURSE COOPÉRATIVE — COOP'ACT, agir ensemble pour la juste valeur. Publiez des produits LOLODRIVE
            ou vendeurs, programmez dates et récurrence, gérez plans CREDI'SCOP-COOP'ACT, catégories et types.
            Salle membre : /encheres
          </p>
        </div>
        <div className="flex gap-2">
          <Button size="sm" variant="outline" onClick={() => setSettingsOpen(true)}
            data-testid="auction-settings-btn" className="border-white/15 text-white/70">
            <Settings2 className="w-4 h-4 mr-1" /> Catégories · Types · Plans
          </Button>
          <Button size="sm" onClick={() => { setEditing(null); setFormOpen(true); }}
            data-testid="new-auction-btn"
            className="bg-[#D9B35A] text-[#2A1045] on-gold hover:bg-[#F2D07A] font-semibold">
            <Plus className="w-4 h-4 mr-1" /> Nouveau COOP'ACT
          </Button>
        </div>
      </div>

      <AuctionStats refreshKey={data.items.length} />

      {data.items.length === 0 ? (
        <p className="text-white/45 text-sm py-6" data-testid="auctions-admin-empty">
          Aucun COOP'ACT programmé pour le moment.
        </p>
      ) : (
        <div className="space-y-2 mt-3">
          {data.items.map((a) => (
            <div key={a.id} className="rounded-[14px] p-3 bg-white/[0.03] border border-white/[0.08]"
              data-testid={`admin-auction-row-${a.reference}`}>
              <div className="flex items-center gap-3 flex-wrap">
                {a.image_url && <img src={a.image_url} alt="" className="w-9 h-9 rounded-lg object-contain bg-white/90" />}
                <span className="text-sm font-bold text-white">{a.title}</span>
                <Badge className={`${STATUS_STYLE[a.status] || 'bg-white/10'} border-0 text-[10px]`}>{a.status}</Badge>
                <span className="text-[10px] text-white/45">{a.reference}</span>
                {a.source_visible
                  ? <Badge className="bg-[#D9B35A]/15 text-[#E9CF8E] border-0 text-[10px]">{a.source}</Badge>
                  : <Badge className="bg-white/10 text-white/45 border-0 text-[10px]">provenance masquée ({a.source})</Badge>}
                {REC_LABELS[a.recurrence] && <span className="text-[10px] text-sky-300">{REC_LABELS[a.recurrence]}</span>}
                <div className="ml-auto flex items-center gap-3 text-xs">
                  <span className="text-[#E9CF8E] font-bold">{Number(a.current_price_eur).toFixed(2)} € · {a.price_credits} cr.</span>
                  <span className="text-white/45">plancher {Number(a.floor_eur).toFixed(2)} €</span>
                  <span className="text-white/45">{a.bids_count} mise(s)</span>
                  <span className="text-red-300 font-semibold" data-testid={`admin-auction-countdown-${a.reference}`}>
                    {a.status === 'SCHEDULED' && <Countdown target={a.starts_at} prefix="départ" />}
                    {a.status === 'LIVE' && <Countdown target={a.ends_at} prefix="fin" />}
                  </span>
                  {(a.status === 'SCHEDULED' || a.status === 'LIVE') && (
                    <>
                      <button type="button" onClick={() => { setEditing(a); setFormOpen(true); }}
                        data-testid={`edit-auction-${a.reference}`}
                        className="p-1 rounded text-white/60 hover:bg-white/10"><Pencil className="w-3.5 h-3.5" /></button>
                      <button type="button" onClick={() => cancel(a)}
                        data-testid={`cancel-auction-${a.reference}`}
                        className="p-1 rounded text-red-400 hover:bg-red-500/10"><XCircle className="w-3.5 h-3.5" /></button>
                    </>
                  )}
                </div>
              </div>
              {a.winner && (
                <p className="text-[11px] text-[#E9CF8E] mt-1.5" data-testid={`admin-auction-winner-${a.reference}`}>
                  🏆 {a.winner.name} ({a.winner.email}) — {Number(a.winner.price_eur).toFixed(2)} € / {a.winner.price_credits} cr.
                  {a.fulfillment && (
                    <span className="text-white/60"> · {a.fulfillment.mode === 'PICKUP'
                      ? `Retrait : ${a.fulfillment.point_name}` : `Livraison : ${a.fulfillment.address}`}</span>
                  )}
                  {!a.fulfillment && <span className="text-white/45"> · en attente du choix retrait/livraison</span>}
                </p>
              )}
            </div>
          ))}
        </div>
      )}

      {formOpen && (
        <AuctionFormDialog auction={editing} onClose={() => setFormOpen(false)}
          onSaved={() => { setFormOpen(false); load(); }} />
      )}
      {settingsOpen && (
        <AuctionSettingsDialog onClose={() => setSettingsOpen(false)} onChanged={load} />
      )}
    </div>
  );
};
