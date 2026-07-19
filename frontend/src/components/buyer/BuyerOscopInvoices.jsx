import { useEffect, useState } from 'react';
import { Download, FileText } from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent } from '../ui/card';
import { Button } from '../ui/button';

const API = process.env.REACT_APP_BACKEND_URL;
const eur = (c) => `${((c || 0) / 100).toFixed(2).replace('.', ',')} €`;

export const BuyerOscopInvoices = () => {
  const [items, setItems] = useState([]);

  useEffect(() => {
    Promise.all([
      fetch(`${API}/api/vendor/my-invoices`, { credentials: 'include' }).then((r) => (r.ok ? r.json() : { items: [] })),
      fetch(`${API}/api/cpc/me/invoices`, { credentials: 'include' }).then((r) => (r.ok ? r.json() : { items: [] })),
    ]).then(([adh, cpc]) => {
      const merged = [
        ...(adh.items || []).map((i) => ({ ...i, _dl: `/api/vendor/my-invoices/${i.number}/pdf`, _kind: 'Adhésion / abonnement' })),
        ...(cpc.items || []).map((i) => ({ ...i, _dl: `/api/cpc/me/invoices/${i.number}/pdf`, _kind: 'Pack CPC' })),
      ].sort((a, b) => String(b.date).localeCompare(String(a.date)));
      setItems(merged);
    }).catch(() => {});
  }, []);

  const dl = async (inv) => {
    const r = await fetch(`${API}${inv._dl}`, { credentials: 'include' });
    if (!r.ok) return toast.error('Téléchargement impossible');
    const url = URL.createObjectURL(await r.blob());
    const a = document.createElement('a');
    a.href = url; a.download = `${inv.number}.pdf`; a.click();
    URL.revokeObjectURL(url);
  };

  if (!items.length) return null;
  return (
    <Card className="bg-white/[0.04] border-white/[0.08]" data-testid="buyer-oscop-invoices">
      <CardContent className="p-4">
        <div className="flex items-center gap-2 mb-3">
          <FileText className="w-4 h-4 text-[#D9B35A]" />
          <h3 className="text-sm font-bold text-white">Factures de services</h3>
          <span className="px-2 py-0.5 rounded-full text-[9px] font-bold bg-[#D9B35A]/20 text-[#E9CF8E] border border-[#D9B35A]/40">ÉMETTEUR : O'SCOP</span>
          <span className="text-[10px] text-white/40">Abonnements, adhésions et packs CPC — distinctes des factures de marchandises KDMARCHÉ</span>
        </div>
        <div className="space-y-1.5">
          {items.map((inv) => (
            <div key={inv.number} className="flex flex-wrap items-center gap-2 text-xs py-1.5 border-b border-white/5 last:border-0" data-testid={`oscop-invoice-${inv.number}`}>
              <span className="font-bold text-white">{inv.number}</span>
              <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-white/10 text-white/60">{inv._kind}</span>
              <span className="flex-1 text-white/50 truncate">{inv.label}</span>
              <span className="text-white/40">{String(inv.date).slice(0, 10)}</span>
              <span className="text-white/70">{eur(inv.ht_cents)} HT · TVA {inv.vat_rate}%</span>
              <span className="font-bold text-white">{eur(inv.ttc_cents)} TTC</span>
              <Button variant="outline" size="sm" className="h-7 px-2 border-white/15 bg-transparent text-white/70 hover:text-white" onClick={() => dl(inv)} data-testid={`oscop-invoice-dl-${inv.number}`}>
                <Download className="w-3 h-3" />
              </Button>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};
