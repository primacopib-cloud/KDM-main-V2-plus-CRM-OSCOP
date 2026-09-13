import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import i18n from '@/i18n';
import { API, getAuthHeaders } from '../../services/http';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';

// Dialogue gagnant : choix retrait relais LOLODRIVE ou livraison
export const WinnerDialog = ({ auction, onClose, onDone }) => {
  const [mode, setMode] = useState('PICKUP');
  const [points, setPoints] = useState([]);
  const [pointId, setPointId] = useState('');
  const [address, setAddress] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetch(`${API}/auctions/points`).then((r) => r.json()).then((d) => setPoints(d.items || [])).catch(() => {});
  }, []);

  const confirm = async () => {
    setBusy(true);
    try {
      const res = await fetch(`${API}/auctions/${auction.id}/fulfillment`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        credentials: 'include',
        body: JSON.stringify({ mode, lolo_point_id: pointId || null, address: address || null }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Erreur');
      toast.success('✓');
      onDone?.();
      onClose();
    } catch (e) {
      toast.error(String(e.message || e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="bg-[#2A1045] border-[#D9B35A]/30 text-white max-w-md" data-testid="winner-dialog">
        <DialogHeader>
          <DialogTitle className="text-[#E9CF8E]">{i18n.t('auction.you_won')}</DialogTitle>
        </DialogHeader>
        <p className="text-sm text-white/70">{auction.title} — {Number(auction.winner_price_eur ?? auction.price_eur).toFixed(2)} €</p>
        <p className="text-xs text-white/55">{i18n.t('auction.choose_fulfillment')}</p>
        <div className="flex gap-2">
          {[['PICKUP', 'pickup'], ['DELIVERY', 'delivery']].map(([v, k]) => (
            <button key={v} type="button" onClick={() => setMode(v)} data-testid={`winner-mode-${v}`}
              className={`flex-1 h-9 rounded-lg text-xs font-bold border transition-colors ${
                mode === v ? 'bg-[#D9B35A] text-[#2A1045] on-gold border-[#D9B35A]' : 'bg-white/[0.05] text-white/60 border-white/15'}`}>
              {i18n.t(`auction.${k}`)}
            </button>
          ))}
        </div>
        {mode === 'PICKUP' ? (
          <Select value={pointId} onValueChange={setPointId}>
            <SelectTrigger className="bg-white/[0.05] border-white/15" data-testid="winner-point-select">
              <SelectValue placeholder={i18n.t('auction.choose_point')} />
            </SelectTrigger>
            <SelectContent>
              {points.map((p) => (
                <SelectItem key={p.id} value={p.id}>{p.name} ({p.code})</SelectItem>
              ))}
            </SelectContent>
          </Select>
        ) : (
          <textarea value={address} onChange={(e) => setAddress(e.target.value)} rows={3}
            placeholder={i18n.t('auction.address')} data-testid="winner-address-input"
            className="w-full rounded-lg bg-white/[0.05] border border-white/15 text-xs text-white p-2 outline-none focus:border-[#D9B35A]/60" />
        )}
        <button type="button" disabled={busy || (mode === 'PICKUP' ? !pointId : !address.trim())}
          onClick={confirm} data-testid="winner-confirm-btn"
          className="h-9 rounded-lg text-sm font-bold text-[#2A1045] on-gold disabled:opacity-40"
          style={{ background: 'linear-gradient(135deg, #D9B35A, #F2D07A)' }}>
          {i18n.t('auction.confirm')}
        </button>
      </DialogContent>
    </Dialog>
  );
};
