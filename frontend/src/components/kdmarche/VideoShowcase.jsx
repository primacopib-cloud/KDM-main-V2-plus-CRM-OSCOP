import { useState, useEffect } from 'react';
import { Clapperboard, Sparkles } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const VideoShowcase = () => {
  const [videos, setVideos] = useState([]);

  useEffect(() => {
    fetch(`${API}/public/kdmarche-videos`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => d && setVideos(d.videos || []))
      .catch(() => {});
  }, []);

  if (!videos.length) return null;

  return (
    <section className="max-w-[1160px] mx-auto px-5 mb-14" data-testid="kdm-video-showcase">
      <p className="text-center text-[11px] uppercase tracking-[0.2em] text-[#D9B35A] mb-2">
        <Sparkles className="inline w-3.5 h-3.5 mr-1.5 -mt-0.5" />
        Studio IA Vendeurs
      </p>
      <h2 className="font-display text-2xl md:text-3xl text-center mb-2">
        Galerie des spots vidéo
      </h2>
      <p className="text-center text-white/60 text-sm max-w-[58ch] mx-auto mb-8">
        Des spots publicitaires générés par IA directement depuis l&apos;Espace Vendeur.
        Mettez vos produits en scène en quelques clics, vous aussi.
      </p>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {videos.map((v) => (
          <div key={v.id} className="glass-panel-soft rounded-[20px] overflow-hidden" data-testid={`kdm-video-card-${v.id}`}>
            <video
              src={v.video_url}
              controls
              preload="metadata"
              playsInline
              className="w-full aspect-video object-cover bg-black"
              data-testid={`kdm-video-player-${v.id}`}
            />
            <div className="p-4 flex items-start gap-3">
              <div className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
                style={{ background: '#D9B35A1c', border: '1px solid #D9B35A55' }}>
                <Clapperboard className="w-4 h-4 text-[#D9B35A]" />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-semibold truncate">{v.product_name}</p>
                <p className="text-xs text-white/55 truncate">{v.vendor_name}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
};
