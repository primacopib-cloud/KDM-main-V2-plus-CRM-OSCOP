import { useEffect, useState } from 'react';
import { FolderLock, FileDown } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders, getSessionToken } from '../../services/http';

const TYPE_FR = { DATAROOM: 'Data room', INVESTOR_COMMITMENT: "Bon d'Engagement" };

export const InvestorDataroom = () => {
  const [ops, setOps] = useState([]);
  const [seen, setSeen] = useState({});
  useEffect(() => {
    if (!getSessionToken()) return;
    fetch(`${API}/investor/my-dataroom`, { headers: getAuthHeaders() })
      .then((r) => (r.ok ? r.json() : { operations: [] }))
      .then((d) => setOps((d.operations || []).filter((o) => o.documents.length > 0)))
      .catch(() => {});
  }, []);

  const newCount = ops.reduce((n, o) => n + o.documents.filter((d) => d.is_new && !seen[d.id]).length, 0);

  const download = async (doc) => {
    try {
      const res = await fetch(`${API}/investor/documents/${doc.id}/pdf`, { headers: getAuthHeaders() });
      if (!res.ok) throw new Error('Téléchargement refusé');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = `${doc.doc_number}.pdf`; a.click();
      URL.revokeObjectURL(url);
      setSeen((s) => ({ ...s, [doc.id]: true }));
    } catch (e) {
      toast.error(String(e.message || e));
    }
  };

  if (ops.length === 0) return null;
  return (
    <div className="glass-panel-soft rounded-[22px] p-5 mb-8" data-testid="investor-dataroom">
      <h2 className="text-lg font-bold flex items-center gap-2 mb-1">
        <FolderLock className="w-5 h-5 text-[#D9B35A]" /> Ma data room
        {newCount > 0 && (
          <span data-testid="dataroom-new-badge"
            className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-red-500 text-white animate-pulse">
            {newCount} nouveau{newCount > 1 ? 'x' : ''}
          </span>
        )}
      </h2>
      <p className="text-white/60 text-xs mb-4">
        Documents en lecture seule des opérations pour lesquelles votre financement a été retenu.
      </p>
      <div className="space-y-3">
        {ops.map((op) => (
          <div key={op.id} className="rounded-[14px] p-4 bg-white/[0.03] border border-white/[0.08]"
            data-testid={`dataroom-op-${op.reference}`}>
            <div className="flex items-center justify-between gap-2 flex-wrap mb-2">
              <span className="text-sm font-bold text-white">{op.reference}
                {op.linked_product_name && <span className="text-white/60 font-normal"> · {op.linked_product_name}</span>}
              </span>
              <span className="text-[11px] text-white/55">{op.territory_id || ''}</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {op.documents.map((d) => (
                <button key={d.id} type="button" onClick={() => download(d)}
                  data-testid={`dataroom-doc-${d.doc_number}`}
                  className="relative inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] font-semibold border border-[#D9B35A]/30 text-[#E9CF8E] hover:bg-[#D9B35A]/10 transition-colors">
                  <FileDown className="w-3.5 h-3.5" /> {TYPE_FR[d.doc_type] || d.doc_type} — {d.doc_number}
                  {d.is_new && !seen[d.id] && (
                    <span data-testid={`new-dot-${d.doc_number}`}
                      className="absolute -top-1.5 -right-1.5 px-1.5 py-0.5 rounded-full text-[8px] font-bold bg-red-500 text-white">
                      Nouveau
                    </span>
                  )}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
