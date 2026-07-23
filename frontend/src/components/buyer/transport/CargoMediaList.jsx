import { useEffect, useState } from 'react';
import { Camera, Download, Film } from 'lucide-react';
import { API, getAuthHeaders, getSessionToken } from '../../../services/http';
import { downloadTransportPdf } from './LogiscopSubscribeCard';

const STAGE_LABEL = { PRISE_EN_CHARGE: 'Prise en charge', TRANSIT: 'Transit', LIVRAISON: 'Livraison' };

const Thumb = ({ m }) => {
  const [url, setUrl] = useState(null);
  useEffect(() => {
    let objectUrl = null;
    fetch(`${API}/logiscop-transport/media/${m.id}/download`, {
      credentials: 'include',
      headers: { Authorization: `Bearer ${getSessionToken()}`, ...getAuthHeaders() },
    }).then((r) => (r.ok ? r.blob() : null))
      .then((b) => { if (b) { objectUrl = URL.createObjectURL(b); setUrl(objectUrl); } })
      .catch(() => {});
    return () => { if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [m.id]);
  if (!url) return <span className="w-20 h-16 rounded-lg bg-white/10 animate-pulse inline-block" />;
  return (
    <a href={url} target="_blank" rel="noreferrer" title={m.name} data-testid={`media-thumb-${m.id}`}>
      <img src={url} alt={m.name} className="w-20 h-16 object-cover rounded-lg border border-white/15 hover:border-[#D9B35A] transition-colors" />
    </a>
  );
};

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
      <p className="text-[11px] font-bold text-[#93C5FD] mb-2 flex items-center gap-1.5">
        <Camera size={12} /> Médias cargaison transmis par le transporteur ({media.length})
      </p>
      {media.length === 0 ? (
        <p className="text-[10px] text-white/40">Aucun média transmis pour le moment.</p>
      ) : (
        <div className="flex flex-wrap gap-3">
          {media.map((m) => (
            <div key={m.id} className="flex flex-col gap-1" style={{ maxWidth: 96 }}>
              {m.mime?.startsWith('image/') ? (
                <Thumb m={m} />
              ) : (
                <button type="button" onClick={() => downloadTransportPdf(`/logiscop-transport/media/${m.id}/download`, m.name)}
                  className="w-20 h-16 rounded-lg bg-white/[0.06] border border-white/15 flex items-center justify-center text-white/50 hover:text-[#93C5FD]"
                  title={m.name} data-testid={`media-video-${m.id}`}>
                  <Film size={20} />
                </button>
              )}
              <span className="text-[9px] text-white/55 leading-tight">
                <b className="text-white/75">{STAGE_LABEL[m.stage] || m.stage}</b><br />
                {(m.uploaded_at || '').slice(5, 16).replace('T', ' ')}{m.ged_doc_id ? ' · GED ✓' : ''}
                <button type="button" data-testid={`media-dl-${m.id}`}
                  onClick={() => downloadTransportPdf(`/logiscop-transport/media/${m.id}/download`, m.name)}
                  className="ml-1 text-white/40 hover:text-[#E9CF8E] align-middle"><Download size={10} /></button>
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
