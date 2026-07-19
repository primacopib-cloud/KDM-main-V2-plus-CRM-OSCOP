import { useState, useEffect, useCallback, Fragment } from 'react';
import { BookUser, Loader2, ShoppingBag, Store, FileDown, FileText, Ban, RotateCcw, AlertTriangle, History } from 'lucide-react';
import { toast } from 'sonner';
import { apiCallV2, BACKEND_URL } from '../../services/http';

const TYPES = [
  { value: 'BUYER_PRO', label: 'Acheteurs pro', icon: ShoppingBag, color: '#5B9BD5' },
  { value: 'VENDOR_PRO', label: 'Vendeurs pro', icon: Store, color: '#8CC63E' },
];

const STATUS_STYLES = {
  ACTIVE: { label: 'ACTIF', cls: 'bg-green-500/15 text-green-700 border-green-500/30' },
  SUSPENDED: { label: 'SUSPENDU', cls: 'bg-amber-500/15 text-amber-700 border-amber-500/30' },
  RADIE: { label: 'RADIÉ', cls: 'bg-red-500/15 text-red-600 border-red-500/30' },
};

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

  const [historyOpen, setHistoryOpen] = useState(null);

  const changeStatus = async (m, status, actionLabel) => {
    const reason = window.prompt(`Motif de la ${actionLabel} de « ${m.legal_name} » (obligatoire) :`);
    if (!reason || reason.trim().length < 3) {
      if (reason !== null) toast.error('Motif obligatoire (3 caractères minimum)');
      return;
    }
    try {
      await apiCallV2(`/admin/member-registry/${m.org_id}/status`, {
        method: 'PATCH', body: JSON.stringify({ status, reason: reason.trim() }),
      });
      toast.success(`Membre ${STATUS_STYLES[status].label.toLowerCase()} — motif enregistré`);
      load();
    } catch (e) {
      toast.error(e.message || 'Erreur');
    }
  };

  const viewExtract = async (m) => {
    try {
      toast.info('Récupération de l\'extrait d\'immatriculation…');
      const r = await fetch(`${BACKEND_URL}/api/v2/admin/member-registry/extract/${m.siret}`, { credentials: 'include' });
      if (!r.ok) {
        const d = await r.json().catch(() => ({}));
        throw new Error(d.detail || 'Extrait indisponible');
      }
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      window.open(url, '_blank');
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (e) {
      toast.error(e.message);
    }
  };

  const exportRegistry = async (format) => {
    try {
      const r = await fetch(`${BACKEND_URL}/api/v2/admin/member-registry/export?member_type=${type}&format=${format}`, { credentials: 'include' });
      if (!r.ok) throw new Error('Export impossible');
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `registre-${type.toLowerCase()}-${new Date().toISOString().slice(0, 10)}.${format}`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success(`Export ${format.toUpperCase()} téléchargé`);
    } catch (e) {
      toast.error(e.message);
    }
  };

  return (
    <div className="space-y-4" data-testid="member-registry-tab">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h2 className="text-lg font-semibold flex items-center gap-2 text-[#4C2A6E]">
          <BookUser className="w-5 h-5 text-[#D9B35A]" /> Registres des membres
        </h2>
        <div className="flex gap-2 flex-wrap">
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
          <button onClick={() => exportRegistry('csv')} className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold bg-white text-[#4C2A6E] border border-[#E9DCC0] hover:border-[#D9B35A]/50 transition-colors" data-testid="registry-export-csv">
            <FileDown className="w-3.5 h-3.5" /> CSV
          </button>
          <button onClick={() => exportRegistry('pdf')} className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold bg-white text-[#4C2A6E] border border-[#E9DCC0] hover:border-[#D9B35A]/50 transition-colors" data-testid="registry-export-pdf">
            <FileText className="w-3.5 h-3.5" /> PDF
          </button>
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
                <th className="px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {members.map((m) => {
                const st = STATUS_STYLES[m.status] || STATUS_STYLES.ACTIVE;
                return (
                <Fragment key={m.org_id}>
                <tr className="border-b border-[#F3EBD8] last:border-0 hover:bg-[#FBF6EC] transition-colors" data-testid={`registry-row-${m.org_id}`}>
                  <td className="px-4 py-3 font-medium text-[#3D2E1E]">{m.legal_name}</td>
                  <td className="px-4 py-3 text-[#7A6850] font-mono text-xs">{m.siret}</td>
                  <td className="px-4 py-3 text-[#7A6850]">{m.territory}</td>
                  <td className="px-4 py-3 text-[#7A6850]">
                    {m.contact_name || '—'}
                    {m.contact_email && <span className="block text-xs text-[#A8977C]">{m.contact_email}</span>}
                  </td>
                  <td className="px-4 py-3 text-[#7A6850]">{m.registered_at ? new Date(m.registered_at).toLocaleDateString('fr-FR') : '—'}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${st.cls}`} data-testid={`registry-status-${m.org_id}`}>
                      {st.label}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-1.5 flex-wrap">
                      {m.siret && (
                        <button onClick={() => viewExtract(m)} title="Extrait d'immatriculation (PDF)"
                          className="p-1.5 rounded-lg text-[#B8860B] bg-[#D9B35A]/10 border border-[#D9B35A]/40 hover:bg-[#D9B35A]/20"
                          data-testid={`registry-extract-${m.org_id}`}>
                          <FileText className="w-3.5 h-3.5" />
                        </button>
                      )}
                      {m.status !== 'SUSPENDED' && m.status !== 'RADIE' && (
                        <button onClick={() => changeStatus(m, 'SUSPENDED', 'suspension')} title="Suspendre"
                          className="p-1.5 rounded-lg text-amber-700 bg-amber-500/10 border border-amber-500/30 hover:bg-amber-500/20"
                          data-testid={`registry-suspend-${m.org_id}`}>
                          <AlertTriangle className="w-3.5 h-3.5" />
                        </button>
                      )}
                      {m.status !== 'RADIE' && (
                        <button onClick={() => changeStatus(m, 'RADIE', 'radiation')} title="Radier"
                          className="p-1.5 rounded-lg text-red-600 bg-red-500/10 border border-red-500/30 hover:bg-red-500/20"
                          data-testid={`registry-radiate-${m.org_id}`}>
                          <Ban className="w-3.5 h-3.5" />
                        </button>
                      )}
                      {m.status && m.status !== 'ACTIVE' && (
                        <button onClick={() => changeStatus(m, 'ACTIVE', 'réactivation')} title="Réactiver"
                          className="p-1.5 rounded-lg text-green-700 bg-green-500/10 border border-green-500/30 hover:bg-green-500/20"
                          data-testid={`registry-reactivate-${m.org_id}`}>
                          <RotateCcw className="w-3.5 h-3.5" />
                        </button>
                      )}
                      {(m.history || []).length > 0 && (
                        <button onClick={() => setHistoryOpen(historyOpen === m.org_id ? null : m.org_id)} title="Historique"
                          className="p-1.5 rounded-lg text-[#4C2A6E] bg-[#4C2A6E]/8 border border-[#4C2A6E]/20 hover:bg-[#4C2A6E]/15"
                          data-testid={`registry-history-${m.org_id}`}>
                          <History className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
                {historyOpen === m.org_id && (m.history || []).length > 0 && (
                  <tr className="bg-[#FBF6EC]">
                    <td colSpan={7} className="px-6 py-3">
                      <p className="text-[11px] font-bold uppercase text-[#8A785F] mb-1.5">Historique du membre</p>
                      {m.history.map((h, i) => (
                        <p key={`${m.org_id}-h${i}`} className="text-xs text-[#5C4B36]" data-testid={`registry-history-entry-${m.org_id}-${i}`}>
                          • <strong>{(STATUS_STYLES[h.action] || {}).label || h.action}</strong> — {new Date(h.at).toLocaleString('fr-FR')} — par {h.by} — motif : {h.reason}
                        </p>
                      ))}
                    </td>
                  </tr>
                )}
                </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
