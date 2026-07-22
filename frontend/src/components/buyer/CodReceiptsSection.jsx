import { useEffect, useState } from 'react';
import { HandCoins, Download } from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent } from '../ui/card';
import { Button } from '../ui/button';

const API = process.env.REACT_APP_BACKEND_URL;
const eur = (c) => `${((c || 0) / 100).toFixed(2)} €`;

export const CodReceiptsSection = () => {
  const [items, setItems] = useState([]);

  useEffect(() => {
    fetch(`${API}/api/v2/checkout/cod-receipts`, { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : { items: [] }))
      .then((d) => setItems(d.items || [])).catch(() => {});
  }, []);

  const download = async (r) => {
    try {
      const resp = await fetch(`${API}/api/v2/checkout/cod-receipts/${r.id}/pdf`, { credentials: 'include' });
      if (!resp.ok) throw new Error('Téléchargement impossible');
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `recu-${r.order_number}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      toast.error(e.message);
    }
  };

  if (!items.length) return null;
  return (
    <Card className="bg-white/[0.04] border-white/[0.08]" data-testid="cod-receipts-section">
      <CardContent className="p-4">
        <div className="flex items-center gap-2 mb-3">
          <HandCoins className="w-4 h-4 text-[#D9B35A]" />
          <h3 className="text-sm font-bold text-white">Reçus d'encaissement (paiement à la livraison)</h3>
          <span className="px-2 py-0.5 rounded-full text-[9px] font-bold bg-[#D9B35A]/15 text-[#E9CF8E] border border-[#D9B35A]/40">{items.length}</span>
        </div>
        <div className="space-y-2">
          {items.map((r) => (
            <div key={r.id} className="flex items-center gap-3 flex-wrap p-2.5 rounded-lg bg-white/[0.03] border border-white/[0.06] text-xs" data-testid={`cod-receipt-${r.id}`}>
              <span className="text-white font-medium">{r.receipt_number || r.order_number}</span>
              <span className="text-white/50">Commande {r.order_number}</span>
              <span className="text-[#E9CF8E] font-semibold">{eur(r.amount_paid_cents)}</span>
              {r.paid_at && <span className="text-white/40">{new Date(r.paid_at).toLocaleDateString('fr-FR')}</span>}
              <Button variant="outline" size="sm" onClick={() => download(r)} data-testid={`cod-receipt-dl-${r.id}`}
                className="ml-auto h-7 px-2 text-xs border-white/15 text-white/80">
                <Download className="w-3 h-3 mr-1" /> Reçu PDF
              </Button>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};
