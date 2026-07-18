import { useState, useEffect } from 'react';
import { Clapperboard, Sparkles, Eye, Trophy } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const MEDALS = ['🥇', '🥈', '🥉'];

const TopSpots = ({ videos }) => {
  const top = [...videos].filter((v) => v.views > 0).sort((a, b) => b.views - a.views).slice(0, 3);
  if (!top.length) return null;
  return (
    <div className="max-w-[720px] mx-auto mb-8" data-testid="kdm-top-spots">
      <p className="text-center text-[11px] uppercase tracking-[0.2em] text-[#D9B35A] mb-3">
        <Trophy className="inline w-3.5 h-3.5 mr-1.5 -mt-0.5" /> Top des spots les plus vus
      </p>
      <div className="space-y-2">
        {top.map((v, i) => (
          <div key={v.id} className="glass-panel-soft rounded-[14px] px-4 py-2.5 flex items-center gap-3"
            data-testid={`kdm-top-spot-${i + 1}`}>
            <span className="text-xl">{MEDALS[i]}</span>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold truncate">{v.product_name}</p>
              <p className="text-xs text-white/55 truncate">{v.vendor_name}</p>
            </div>
            <span className="text-xs font-semibold text-[#D9B35A] inline-flex items-center gap-1 shrink-0">
              <Eye size={13} /> {v.views} vue{v.views > 1 ? 's' : ''}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

const VideoCard = ({ v }) => {
  const [counted, setCounted] = useState(false);
  const [views, setViews] = useState(v.views || 0);

  const trackView = () => {
    if (counted) return;
    setCounted(true);
    setViews((n) => n + 1);
    fetch(`${API}/public/kdmarche-video-view`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ product_id: v.product_id }),
    }).catch(() => {});
  };

  return (
    <div className="glass-panel-soft rounded-[20px] overflow-hidden" data-testid={`kdm-video-card-${v.id}`}>
      <video
        src={v.video_url.startsWith('http') ? v.video_url : `${process.env.REACT_APP_BACKEND_URL}${v.video_url}`}
        controls preload="metadata" playsInline onPlay={trackView}
        className="w-full aspect-video object-cover bg-black"
        data-testid={`kdm-video-player-${v.id}`}
      />
      <div className="p-4 flex items-start gap-3">
        <div className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
          style={{ background: '#D9B35A1c', border: '1px solid #D9B35A55' }}>
          <Clapperboard className="w-4 h-4 text-[#D9B35A]" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold truncate">{v.product_name}</p>
          <p className="text-xs text-white/55 truncate">{v.vendor_name}</p>
        </div>
        <span className="text-[11px] text-white/50 inline-flex items-center gap-1 shrink-0"
          data-testid={`kdm-video-views-${v.id}`}>
          <Eye size={12} /> {views}
        </span>
      </div>
    </div>
  );
};

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
      <TopSpots videos={videos} />
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {videos.map((v) => <VideoCard key={v.id} v={v} />)}
      </div>
    </section>
  );
};
