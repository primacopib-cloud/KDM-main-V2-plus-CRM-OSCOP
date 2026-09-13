import { useEffect, useState } from 'react';
import { FolderLock, FileDown, Users } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';

const TYPE_FR = { DATAROOM: 'Data room', INVESTOR_COMMITMENT: "Bon d'Engagement" };

export const DataroomAdminPanel = () => {
  const [ops, setOps] = useState(null);

  useEffect(() => {
    fetch(`${API}/investor/admin/dataroom`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => (r.ok ? r.json() : { operations: [] }))
      .then((d) => setOps(d.operations || []))
      .catch(() => setOps([]));
  }, []);

  const download = async (doc) => {
    try {
      const res = await fetch(`${API}/investor/documents/${doc.id}/pdf`,
        { headers: getAuthHeaders(), credentials: 'include' });
      if (!res.ok) throw new Error('Téléchargement refusé');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = `${doc.doc_number}.pdf`; a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      toast.error(String(e.message || e));
    }
  };

  if (!ops) return null;
  return (
    <div className="glass-panel-soft rounded-[22px] p-5" data-testid="admin-dataroom-panel">
      <h3 className="text-lg font-bold text-white flex items-center gap-2 mb-1">
        <FolderLock className="w-5 h-5 text-[#D9B35A]" /> Data room investisseurs
      </h3>
      <p className="text-white/60 text-xs mb-4">
        Accès superadmin complet : consultez les packs data room et bons d'engagement de chaque opération.
        La génération des documents et l'acceptation des investisseurs se font depuis le détail de l'opération ci-dessus.
      </p>
      {ops.length === 0 ? (
        <p className="text-white/45 text-sm" data-testid="admin-dataroom-empty">
          Aucun document de data room archivé pour le moment.
        </p>
      ) : (
        <div className="space-y-3">
          {ops.map((op) => (
            <div key={op.id} className="rounded-[14px] p-4 bg-white/[0.03] border border-white/[0.08]"
              data-testid={`admin-dataroom-op-${op.reference}`}>
              <div className="flex items-center justify-between gap-2 flex-wrap mb-2">
                <span className="text-sm font-bold text-white">{op.reference}
                  {op.linked_product_name && (
                    <span className="text-white/60 font-normal"> · {op.linked_product_name}</span>
                  )}
                </span>
                <span className="text-[11px] text-white/55">
                  {op.status}{op.territory_id ? ` · ${op.territory_id}` : ''}
                </span>
              </div>
              {op.accepted_investors?.length > 0 && (
                <p className="text-[11px] text-white/50 mb-2 flex items-center gap-1"
                  data-testid={`admin-dataroom-investors-${op.reference}`}>
                  <Users className="w-3 h-3" /> Investisseurs retenus :{' '}
                  {op.accepted_investors.map((i) => i.investor_name).join(', ')}
                </p>
              )}
              <div className="flex flex-wrap gap-2">
                {op.documents.map((d) => (
                  <button key={d.id} type="button" onClick={() => download(d)}
                    data-testid={`admin-dataroom-doc-${d.doc_number}`}
                    className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] font-semibold border border-[#D9B35A]/30 text-[#E9CF8E] hover:bg-[#D9B35A]/10 transition-colors">
                    <FileDown className="w-3.5 h-3.5" /> {TYPE_FR[d.doc_type] || d.doc_type} — {d.doc_number}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
