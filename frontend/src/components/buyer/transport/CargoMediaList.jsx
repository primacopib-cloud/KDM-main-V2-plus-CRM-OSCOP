import { useEffect, useState } from 'react';
import { Camera, Download } from 'lucide-react';
import { API, getAuthHeaders, getSessionToken } from '../../../services/http';
import { downloadTransportPdf } from './LogiscopSubscribeCard';

const STAGE_LABEL = { PRISE_EN_CHARGE: 'Prise en charge', TRANSIT: 'Transit', LIVRAISON: 'Livraison' };

export const CargoMediaList = ({ otId }) => {
  const [media, setMedia] = useState(null);

  useEffect(() => {
    fetch(`${API}/logiscop-transport/orders/${otId}/media`, {
      credentials: 'include',
      headers: { Authorization: `Bearer ${getSessionToken()}`, ...getAuthHeaders() },
    }).then((r) => (r.ok ? r.json() : [])).then(setMedia).catch(() => setMedia([]));
  }, [otId]);

  if (media === null) return <p className="text-[10px] text-white/40 p-2">Chargement…</p>;

  return (
    <div className="rounded-lg p-3 my-1 bg-white/[0.04] border border-white/[0.08]" data-testid={`cargo-media-${otId}`}>
      <p className="text-[11px] font-bold text-[#93C5FD] mb-1.5 flex items-center gap-1.5">
        <Camera size={12} /> Médias cargaison transmis par le transporteur ({media.length})
      </p>
      {media.length === 0 ? (
        <p className="text-[10px] text-white/40">Aucun média transmis pour le moment.</p>
      ) : (
        <div className="space-y-1">
          {media.map((m) => (
            <div key={m.id} className="flex flex-wrap items-center gap-2 text-[10px] text-white/60">
              <span className="px-1.5 py-0.5 rounded bg-white/10 font-bold text-white/70">{STAGE_LABEL[m.stage] || m.stage}</span>
              <span className="text-white/80">{m.name}</span>
              <span className="text-white/35">{(m.uploaded_at || '').slice(0, 16).replace('T', ' ')} · {m.operator_name}</span>
              {m.ged_doc_id && <span className="text-white/35">GED ✓</span>}
              <button type="button" data-testid={`media-dl-${m.id}`}
                onClick={() => downloadTransportPdf(`/logiscop-transport/media/${m.id}/download`, m.name)}
                className="text-white/50 hover:text-[#E9CF8E]"><Download size={12} /></button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
