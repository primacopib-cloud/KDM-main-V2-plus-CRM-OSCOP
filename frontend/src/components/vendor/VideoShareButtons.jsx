import { toast } from 'sonner';
import { Download, Link2, Share2 } from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const btnCls = 'inline-flex items-center gap-1.5 h-8 px-3 rounded-lg text-xs font-medium border border-gray-200 text-gray-600 hover:border-purple-400 hover:text-purple-700 transition-colors';

export const VideoShareButtons = ({ videoUrl, productName }) => {
  const absUrl = videoUrl.startsWith('http') ? videoUrl : `${API_URL}${videoUrl}`;
  const shareText = `Découvrez le spot vidéo de « ${productName} » sur KDMARCHÉ !`;

  const copyLink = async () => {
    await navigator.clipboard.writeText(absUrl);
    toast.success('Lien du spot copié dans le presse-papiers');
  };

  const nativeShare = async () => {
    if (navigator.share) {
      try { await navigator.share({ title: shareText, url: absUrl }); } catch { /* annulé */ }
    } else {
      copyLink();
    }
  };

  return (
    <div className="flex flex-wrap gap-2 mt-3" data-testid="video-share-buttons">
      <a href={absUrl} download={`spot-${productName.toLowerCase().replace(/[^a-z0-9]+/g, '-')}.mp4`}
        className={btnCls} data-testid="video-download-btn">
        <Download size={13} /> Télécharger
      </a>
      <button type="button" onClick={copyLink} className={btnCls} data-testid="video-copy-link-btn">
        <Link2 size={13} /> Copier le lien
      </button>
      <a href={`https://wa.me/?text=${encodeURIComponent(`${shareText} ${absUrl}`)}`}
        target="_blank" rel="noopener noreferrer" className={btnCls} data-testid="video-share-whatsapp">
        WhatsApp
      </a>
      <a href={`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(absUrl)}`}
        target="_blank" rel="noopener noreferrer" className={btnCls} data-testid="video-share-facebook">
        Facebook
      </a>
      <button type="button" onClick={nativeShare} className={btnCls} data-testid="video-share-native">
        <Share2 size={13} /> Partager…
      </button>
    </div>
  );
};
