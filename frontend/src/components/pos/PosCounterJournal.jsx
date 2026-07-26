import { useEffect, useState } from 'react';
import { Receipt } from 'lucide-react';
import { lolodriveAPI } from '../../services/api';

export const PosCounterJournal = ({ refreshKey }) => {
  const [journal, setJournal] = useState(null);
  useEffect(() => {
    lolodriveAPI.posCounterJournal().then(setJournal).catch(() => {});
  }, [refreshKey]);
  if (!journal || journal.count === 0) return null;
  return (
    <div className="mb-4 rounded-xl border border-emerald-400/30 bg-emerald-400/[0.05] px-4 py-2.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs"
      data-testid="counter-journal">
      <span className="flex items-center gap-1.5 font-bold text-emerald-300">
        <Receipt className="w-3.5 h-3.5" /> Caisse du jour ({journal.date})
      </span>
      <span data-testid="journal-count">{journal.count} vente{journal.count > 1 ? 's' : ''}</span>
      <span className="font-mono" data-testid="journal-cash">💵 Espèces : <b>{(journal.cash_cents / 100).toFixed(2)} €</b></span>
      <span className="font-mono" data-testid="journal-card">💳 CB : <b>{(journal.card_cents / 100).toFixed(2)} €</b></span>
      <span className="font-mono text-emerald-300" data-testid="journal-total">Total : <b>{(journal.total_cents / 100).toFixed(2)} €</b></span>
    </div>
  );
};
