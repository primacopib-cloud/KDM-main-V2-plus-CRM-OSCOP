import { useState } from 'react';
import { ChevronDown, ChevronUp, History, Trophy, Coins, Gavel } from 'lucide-react';
import i18n from '@/i18n';

const fmtDate = (iso) => new Date(iso).toLocaleString(i18n.language, { dateStyle: 'short', timeStyle: 'short' });

// Historique du membre : mises, lots remportés, relevé de crédits
export const AuctionHistoryPanel = ({ me }) => {
  const [open, setOpen] = useState(false);
  if (!me?.account) return null;
  const bids = me.bids || [];
  const wins = me.wins || [];
  const ledger = me.ledger || [];

  return (
    <div className="mt-8 rounded-2xl border border-white/10 bg-white/[0.03]" data-testid="auction-history-panel">
      <button type="button" onClick={() => setOpen((v) => !v)} data-testid="auction-history-toggle"
        className="w-full flex items-center gap-2 p-3 text-sm font-bold text-white/80 hover:bg-white/[0.04] transition-colors rounded-2xl">
        <History className="w-4 h-4 text-[#D9B35A]" /> {i18n.t('auction.history_title')}
        <span className="text-[10px] text-white/40 font-normal">
          {i18n.t('auction.history_counts', { bids: bids.length, wins: wins.length })}
        </span>
        {open ? <ChevronUp className="w-4 h-4 ml-auto" /> : <ChevronDown className="w-4 h-4 ml-auto" />}
      </button>
      {open && (
        <div className="p-4 pt-0 grid gap-4 md:grid-cols-3">
          <section data-testid="auction-history-bids">
            <h4 className="text-[11px] font-bold text-white/50 uppercase mb-2 flex items-center gap-1">
              <Gavel className="w-3 h-3" /> {i18n.t('auction.history_bids')}
            </h4>
            {bids.length === 0 ? <p className="text-xs text-white/35">—</p> : bids.map((b) => (
              <div key={b.id} className="text-[11px] text-white/65 py-1 border-b border-white/[0.05]">
                <span className="font-semibold text-white/80">{b.auction_title || b.auction_reference}</span>
                <span className="text-white/40"> · −{b.credits_spent} cr → {Number(b.price_after_eur).toFixed(2)} €</span>
                <span className="block text-white/30">{fmtDate(b.created_at)}</span>
              </div>
            ))}
          </section>
          <section data-testid="auction-history-wins">
            <h4 className="text-[11px] font-bold text-white/50 uppercase mb-2 flex items-center gap-1">
              <Trophy className="w-3 h-3" /> {i18n.t('auction.history_wins')}
            </h4>
            {wins.length === 0 ? <p className="text-xs text-white/35">—</p> : wins.map((w) => (
              <div key={w.id} className="text-[11px] text-white/65 py-1 border-b border-white/[0.05]">
                <span className="font-semibold text-[#E9CF8E]">{w.title}</span>
                <span className="text-white/40"> · {Number(w.winner_price_eur).toFixed(2)} €</span>
                <span className="block text-white/30">
                  {w.fulfillment
                    ? (w.fulfillment.mode === 'PICKUP' ? `📍 ${w.fulfillment.point_name}` : `🚚 ${i18n.t('auction.delivery')}`)
                    : i18n.t('auction.choose_fulfillment')}
                </span>
              </div>
            ))}
          </section>
          <section data-testid="auction-history-ledger">
            <h4 className="text-[11px] font-bold text-white/50 uppercase mb-2 flex items-center gap-1">
              <Coins className="w-3 h-3" /> {i18n.t('auction.history_ledger')}
            </h4>
            {ledger.length === 0 ? <p className="text-xs text-white/35">—</p> : ledger.map((l) => (
              <div key={l.id} className="text-[11px] py-1 border-b border-white/[0.05] flex justify-between gap-2">
                <span className="text-white/55 truncate">{l.label}</span>
                <span className={`font-bold shrink-0 ${l.amount > 0 ? 'text-emerald-300' : 'text-red-300'}`}>
                  {l.amount > 0 ? '+' : ''}{l.amount} cr
                </span>
              </div>
            ))}
          </section>
        </div>
      )}
    </div>
  );
};
