import { useState, useEffect } from 'react';
import { Boxes, Search, Download } from 'lucide-react';
import { toast } from 'sonner';
import { getAuthHeaders } from '../../services/http';
import { Input } from '../ui/input';
import { ZoneStockButton } from './ZoneStockDialog';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const exportHistoryCsv = async () => {
  try {
    const res = await fetch(`${API_URL}/api/catalog/admin/stock-history/export`, { headers: getAuthHeaders() });
    if (!res.ok) throw new Error();
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `historique_stocks_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success('Historique des stocks exporté en CSV');
  } catch {
    toast.error("Échec de l'export CSV");
  }
};

// Stocks par territoire — produits du catalogue V2 (BTP, agriculture, alimentaire…)
export const StockTerritoryPanel = () => {
  const [products, setProducts] = useState([]);
  const [search, setSearch] = useState('');
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open || products.length) return;
    fetch(`${API_URL}/api/catalog/admin/stock-products`, { headers: getAuthHeaders() })
      .then((r) => r.json())
      .then((d) => setProducts(d.products || []))
      .catch(() => {});
  }, [open, products.length]);

  const filtered = products.filter((p) =>
    `${p.name} ${p.sku || ''}`.toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="rounded-xl bg-white/[0.02] border border-white/[0.08] mb-4" data-testid="stock-territory-panel">
      <button type="button" onClick={() => setOpen(!open)} data-testid="stock-territory-toggle"
        className="w-full flex items-center gap-2 px-4 py-3 text-left text-sm font-semibold text-[#E9CF8E] hover:bg-white/[0.03] rounded-xl transition-colors">
        <Boxes className="w-4 h-4" /> Stocks par territoire (catalogue V2)
        <span className="ml-auto text-xs text-white/40">{open ? 'Réduire' : 'Ouvrir'}</span>
      </button>
      {open && (
        <div className="px-4 pb-4 space-y-2">
          <div className="flex items-center gap-3 flex-wrap">
            <div className="relative w-72">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
              <Input value={search} onChange={(e) => setSearch(e.target.value)}
                placeholder="Rechercher un produit (ex: BTP-CIM-001)…"
                data-testid="stock-territory-search"
                className="pl-9 h-9 bg-white/[0.04] border-white/10 text-white placeholder:text-white/40" />
            </div>
            <button type="button" onClick={exportHistoryCsv} data-testid="stock-history-export-csv"
              className="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-xs font-semibold text-[#E9CF8E] bg-[#D9B35A]/10 border border-[#D9B35A]/30 hover:bg-[#D9B35A]/20 transition-colors">
              <Download className="w-3.5 h-3.5" /> Export CSV historique
            </button>
          </div>
          <div className="max-h-72 overflow-y-auto space-y-1.5">
            {filtered.map((p) => (
              <div key={p.id} className="flex items-center gap-3 px-3 py-2 rounded-lg bg-white/[0.02] border border-white/[0.06]">
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-white/90 truncate">{p.name}</p>
                  <p className="text-xs text-white/40 font-mono">{p.sku} · {p.category}</p>
                </div>
                <ZoneStockButton product={p} />
              </div>
            ))}
            {!filtered.length && <p className="text-xs text-white/40 py-2">Aucun produit.</p>}
          </div>
        </div>
      )}
    </div>
  );
};
