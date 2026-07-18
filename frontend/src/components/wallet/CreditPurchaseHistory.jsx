import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { FileDown, Receipt, CheckCircle2, XCircle, Clock } from 'lucide-react';
import { paymentAPI } from '../../services/api';
import { API, getAuthHeaders } from '../../services/http';

const STATUS = {
  paid: { icon: CheckCircle2, cls: 'text-emerald-500', label: 'Payé' },
  unpaid: { icon: Clock, cls: 'text-amber-500', label: 'En attente' },
};

export const CreditPurchaseHistory = () => {
  const [transactions, setTransactions] = useState([]);
  const [downloading, setDownloading] = useState(null);

  useEffect(() => {
    paymentAPI.getHistory(30)
      .then((d) => setTransactions(d.transactions || []))
      .catch(() => {});
  }, []);

  const downloadReceipt = async (tx) => {
    setDownloading(tx.session_id);
    try {
      const r = await fetch(`${API}/payments/receipt/${tx.session_id}.pdf`, {
        headers: getAuthHeaders(), credentials: 'include',
      });
      if (!r.ok) throw new Error('Facture indisponible');
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `facture-credits-${tx.session_id.slice(-8)}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('Facture téléchargée');
    } catch (e) {
      toast.error(e.message || 'Erreur de téléchargement');
    } finally {
      setDownloading(null);
    }
  };

  if (transactions.length === 0) return null;

  return (
    <div className="mb-6 glass-panel-soft rounded-[18px] p-6" data-testid="credit-purchase-history">
      <h2 className="flex items-center gap-2 text-base font-semibold mb-4">
        <Receipt className="w-4 h-4 text-[#D9B35A]" />
        Mes achats de crédits
      </h2>
      <div className="space-y-2">
        {transactions.map((tx) => {
          const st = STATUS[tx.payment_status] || { icon: XCircle, cls: 'text-red-500', label: 'Échoué / expiré' };
          const StIcon = st.icon;
          return (
            <div
              key={tx.session_id}
              className="flex items-center justify-between gap-3 p-3 rounded-xl bg-white/[0.04] border border-white/[0.08]"
              data-testid={`purchase-row-${tx.session_id.slice(-8)}`}
            >
              <div className="min-w-0">
                <p className="text-sm font-medium">
                  {tx.credits} crédits — {Number(tx.amount).toFixed(2).replace('.', ',')} €
                </p>
                <p className="text-xs text-white/50">
                  {tx.created_at ? new Date(tx.created_at).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : ''}
                </p>
              </div>
              <div className="flex items-center gap-3 flex-shrink-0">
                <span className={`flex items-center gap-1 text-xs font-medium ${st.cls}`}>
                  <StIcon className="w-3.5 h-3.5" /> {st.label}
                </span>
                {tx.payment_status === 'paid' && (
                  <button
                    type="button"
                    onClick={() => downloadReceipt(tx)}
                    disabled={downloading === tx.session_id}
                    data-testid={`download-receipt-${tx.session_id.slice(-8)}`}
                    className="inline-flex items-center gap-1.5 h-8 px-3 rounded-lg text-xs font-semibold transition-colors hover:brightness-110 disabled:opacity-50"
                    style={{ background: 'rgba(217,179,90,0.14)', border: '1px solid rgba(217,179,90,0.45)', color: '#D9B35A' }}
                  >
                    <FileDown className="w-3.5 h-3.5" />
                    {downloading === tx.session_id ? '…' : 'Facture PDF'}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
