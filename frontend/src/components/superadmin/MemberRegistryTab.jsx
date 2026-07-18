import { useState, useEffect, useCallback } from 'react';
import { BookUser, Loader2, ShoppingBag, Store } from 'lucide-react';
import { toast } from 'sonner';
import { apiCallV2 } from '../../services/http';

const TYPES = [
  { value: 'BUYER_PRO', label: 'Acheteurs pro', icon: ShoppingBag, color: '#5B9BD5' },
  { value: 'VENDOR_PRO', label: 'Vendeurs pro', icon: Store, color: '#8CC63E' },
];

export const MemberRegistryTab = () => {
  const [members, setMembers] = useState([]);
  const [counts, setCounts] = useState({});
  const [type, setType] = useState('BUYER_PRO');
  const [loading, setLoading] = useState(true);

  const load = useCallback(async (t = type) => {
    setLoading(true);
    try {
      const data = await apiCallV2(`/admin/member-registry?member_type=${t}`);
      setMembers(data.members);
      setCounts(data.counts);
    } catch (e) {
      toast.error(e.message || 'Erreur de chargement du registre');
    } finally {
      setLoading(false);
    }
  }, [type]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="space-y-4" data-testid="member-registry-tab">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h2 className="text-lg font-semibold flex items-center gap-2 text-[#4C2A6E]">
          <BookUser className="w-5 h-5 text-[#D9B35A]" /> Registres des membres
        </h2>
        <div className="flex gap-2">
          {TYPES.map((t) => (
            <button key={t.value} onClick={() => setType(t.value)}
              className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold border transition-colors ${
                type === t.value ? 'bg-[#D9B35A]/20 text-[#B8860B] border-[#D9B35A]/40' : 'bg-white text-[#7A6850] border-[#E9DCC0] hover:border-[#D9B35A]/40'
              }`}
              data-testid={`registry-filter-${t.value.toLowerCase()}`}>
              <t.icon className="w-3.5 h-3.5" style={{ color: t.color }} />
              {t.label} ({counts[t.value] || 0})
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 animate-spin text-[#D9B35A]" /></div>
      ) : members.length === 0 ? (
        <div className="rounded-2xl bg-white border border-[#E9DCC0] p-10 text-center text-[#8A785F] text-sm" data-testid="registry-empty-state">
          Aucun membre {type === 'BUYER_PRO' ? 'Acheteur pro' : 'Vendeur pro'} enregistré pour le moment.
          <br /><span className="text-xs">Les membres sont inscrits automatiquement à la validation de leur adhésion.</span>
        </div>
      ) : (
        <div className="rounded-2xl bg-white border border-[#E9DCC0] overflow-hidden shadow-[0_4px_16px_rgba(76,42,110,0.06)]">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-[11px] uppercase tracking-wider text-[#8A785F] border-b border-[#EDE1C6] bg-[#FBF6EC]">
                <th className="px-4 py-3">Raison sociale</th>
                <th className="px-4 py-3">SIRET</th>
                <th className="px-4 py-3">Territoire</th>
                <th className="px-4 py-3">Contact</th>
                <th className="px-4 py-3">Inscrit le</th>
                <th className="px-4 py-3">Statut</th>
              </tr>
            </thead>
            <tbody>
              {members.map((m) => (
                <tr key={m.org_id} className="border-b border-[#F3EBD8] last:border-0 hover:bg-[#FBF6EC] transition-colors" data-testid={`registry-row-${m.org_id}`}>
                  <td className="px-4 py-3 font-medium text-[#3D2E1E]">{m.legal_name}</td>
                  <td className="px-4 py-3 text-[#7A6850] font-mono text-xs">{m.siret}</td>
                  <td className="px-4 py-3 text-[#7A6850]">{m.territory}</td>
                  <td className="px-4 py-3 text-[#7A6850]">
                    {m.contact_name || '—'}
                    {m.contact_email && <span className="block text-xs text-[#A8977C]">{m.contact_email}</span>}
                  </td>
                  <td className="px-4 py-3 text-[#7A6850]">{m.registered_at ? new Date(m.registered_at).toLocaleDateString('fr-FR') : '—'}</td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-green-500/15 text-green-700 border border-green-500/30">
                      {m.status || 'ACTIVE'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
