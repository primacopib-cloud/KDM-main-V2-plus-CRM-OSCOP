import { useCallback, useEffect, useState } from 'react';
import { Loader2, Ticket, Plus } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';
import { Button } from '../ui/button';
import { Input } from '../ui/input';

export const ServiceCreditsPanel = () => {
  const [catalog, setCatalog] = useState(null);
  const [accounts, setAccounts] = useState([]);
  const [newAcc, setNewAcc] = useState({ investor_name: '', investor_email: '' });
  const [ledgers, setLedgers] = useState({});
  const [entry, setEntry] = useState({ entry_type: 'ALLOCATION', units: '', service_catalog_item_id: '' });

  const load = useCallback(async () => {
    const [c, a] = await Promise.all([
      fetch(`${API}/admin/service-credits/catalog`, { headers: getAuthHeaders() }).then((r) => r.json()),
      fetch(`${API}/admin/service-credits/accounts`, { headers: getAuthHeaders() }).then((r) => r.json()),
    ]);
    setCatalog(c);
    setAccounts(a.accounts || []);
  }, []);

  useEffect(() => { load(); }, [load]);

  const post = async (url, body, okMsg) => {
    const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json', ...getAuthHeaders() }, body: JSON.stringify(body) });
    const json = await res.json();
    if (!res.ok) { toast.error(typeof json.detail === 'string' ? json.detail : 'Erreur'); return false; }
    toast.success(okMsg);
    await load();
    return true;
  };

  const updateItem = async (item, units) => {
    const res = await fetch(`${API}/admin/service-credits/catalog/${item.id}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify({ units: parseInt(units, 10) || item.units }),
    });
    if (res.ok) { toast.success('Barème mis à jour'); load(); }
  };

  const toggleLedger = async (accId) => {
    if (ledgers[accId]) { setLedgers({ ...ledgers, [accId]: null }); return; }
    const res = await fetch(`${API}/admin/service-credits/accounts/${accId}/ledger`, { headers: getAuthHeaders() });
    const json = await res.json();
    setLedgers({ ...ledgers, [accId]: json.entries || [] });
  };

  if (!catalog) return <div className="py-10 text-center"><Loader2 className="w-5 h-5 animate-spin text-[#D9B35A] mx-auto" /></div>;

  return (
    <div className="space-y-5 mt-8" data-testid="service-credits-panel">
      <div>
        <h2 className="text-xl font-bold text-white flex items-center gap-2">
          <Ticket className="w-5 h-5 text-[#D9B35A]" /> CREDI'SCOP-INVEST — Unités de services internes
        </h2>
        <p className="text-amber-200/85 text-xs mt-1 p-2 rounded bg-amber-500/10 border border-amber-400/25">{catalog.disclaimer}</p>
      </div>

      <div className="glass-panel-soft rounded-[18px] p-4">
        <p className="text-sm font-semibold text-white/85 mb-2">Catalogue fermé de services (barème administrable)</p>
        <div className="grid md:grid-cols-2 gap-1.5">
          {catalog.items.map((it) => (
            <div key={it.id} className="flex items-center justify-between gap-2 text-xs bg-white/5 rounded px-2.5 py-1.5">
              <span className="text-white/80">{it.label}</span>
              <Input defaultValue={it.units} onBlur={(e) => e.target.value !== String(it.units) && updateItem(it, e.target.value)}
                data-testid={`catalog-units-${it.code}`} className="w-16 h-7 text-xs bg-white/5 border-white/15 text-white text-center" />
            </div>
          ))}
        </div>
      </div>

      <div className="glass-panel-soft rounded-[18px] p-4">
        <p className="text-sm font-semibold text-white/85 mb-2">Compteurs investisseurs</p>
        <div className="flex gap-2 mb-3">
          <Input placeholder="Nom investisseur" value={newAcc.investor_name} data-testid="sc-new-name"
            onChange={(e) => setNewAcc({ ...newAcc, investor_name: e.target.value })} className="bg-white/5 border-white/15 text-white h-8 text-xs" />
          <Input placeholder="Email" value={newAcc.investor_email} data-testid="sc-new-email"
            onChange={(e) => setNewAcc({ ...newAcc, investor_email: e.target.value })} className="bg-white/5 border-white/15 text-white h-8 text-xs" />
          <Button size="sm" data-testid="sc-create-account" className="bg-[#D9B35A] text-[#2A1045] hover:bg-[#F2D07A]"
            onClick={() => post(`${API}/admin/service-credits/accounts`, newAcc, 'Compteur créé')}>
            <Plus className="w-4 h-4" />
          </Button>
        </div>
        {accounts.map((a) => (
          <div key={a.id} className="mb-2">
            <button type="button" onClick={() => toggleLedger(a.id)} data-testid={`sc-account-${a.investor_email}`}
              className="w-full flex justify-between items-center text-xs bg-white/5 hover:bg-white/10 rounded px-2.5 py-2 text-left">
              <span className="text-white/85">{a.investor_name} — {a.investor_email}</span>
              <span className="text-[#D9B35A]">
                {a.available_units} u. dispo · {a.reserved_units} réservées · {a.expired_units} expirées
              </span>
            </button>
            {ledgers[a.id] && (
              <div className="p-2.5 bg-black/25 rounded-b space-y-1.5">
                <div className="flex gap-1.5 flex-wrap">
                  <select value={entry.entry_type} onChange={(e) => setEntry({ ...entry, entry_type: e.target.value })}
                    data-testid="sc-entry-type" className="bg-white/5 border border-white/15 rounded px-2 py-1 text-xs text-white">
                    {['ALLOCATION', 'RESERVATION', 'DEBIT', 'RELEASE', 'EXPIRY', 'CORRECTION'].map((t) => <option key={t} className="bg-[#2A1045]">{t}</option>)}
                  </select>
                  <select value={entry.service_catalog_item_id} onChange={(e) => {
                    const it = catalog.items.find((i) => i.id === e.target.value);
                    setEntry({ ...entry, service_catalog_item_id: e.target.value, units: it ? String(it.units) : entry.units });
                  }} data-testid="sc-entry-service" className="bg-white/5 border border-white/15 rounded px-2 py-1 text-xs text-white max-w-[220px]">
                    <option value="" className="bg-[#2A1045]">— service (requis pour débit) —</option>
                    {catalog.items.map((i) => <option key={i.id} value={i.id} className="bg-[#2A1045]">{i.label} ({i.units}u)</option>)}
                  </select>
                  <Input placeholder="Unités" value={entry.units} data-testid="sc-entry-units"
                    onChange={(e) => setEntry({ ...entry, units: e.target.value })} className="w-20 h-7 text-xs bg-white/5 border-white/15 text-white" />
                  <Button size="sm" data-testid="sc-entry-submit" className="bg-white/10 hover:bg-white/20 text-white text-xs h-7"
                    onClick={async () => {
                      const ok = await post(`${API}/admin/service-credits/accounts/${a.id}/entries`, {
                        entry_type: entry.entry_type, units: parseInt(entry.units, 10) || 0,
                        service_catalog_item_id: entry.service_catalog_item_id || null,
                      }, 'Écriture enregistrée');
                      if (ok) toggleLedger(a.id).then(() => toggleLedger(a.id));
                    }}>
                    Enregistrer
                  </Button>
                </div>
                {ledgers[a.id].map((l) => (
                  <p key={l.id} className="text-[11px] text-white/60">
                    {l.created_at.slice(0, 16).replace('T', ' ')} — <b className="text-white/80">{l.entry_type}</b> {l.units} u.
                    {l.service_label ? ` · ${l.service_label}` : ''}
                  </p>
                ))}
                {ledgers[a.id].length === 0 && <p className="text-[11px] text-white/40">Aucune écriture.</p>}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
