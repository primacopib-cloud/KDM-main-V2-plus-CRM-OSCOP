import { useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import { Sparkles, Wand2, Clapperboard, Loader2, Coins, X } from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const TABS = [
  { key: 'generate', label: 'Générer une image', icon: Sparkles, action: 'ai_image_generation' },
  { key: 'enhance', label: 'Améliorer une photo', icon: Wand2, action: 'ai_image_enhance' },
  { key: 'video', label: 'Spot vidéo', icon: Clapperboard, action: 'ai_video_generation' },
];

export const AIStudioModal = ({ product, vendorId, onClose, onMediaAdded }) => {
  const [tab, setTab] = useState('generate');
  const [prompt, setPrompt] = useState('');
  const [selectedImage, setSelectedImage] = useState((product.images || [])[0]?.url || '');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [credits, setCredits] = useState(null);
  const [pricing, setPricing] = useState({});
  const [videoEnabled, setVideoEnabled] = useState(false);
  const [videoJob, setVideoJob] = useState(null);

  const refreshCredits = useCallback(async () => {
    const r = await fetch(`${API_URL}/api/vendor/credits/${vendorId}`);
    if (r.ok) {
      const d = await r.json();
      setCredits(d.credits);
      setPricing(Object.fromEntries((d.pricing || []).map((p) => [p.action, p.cost])));
    }
  }, [vendorId]);

  useEffect(() => {
    refreshCredits();
    fetch(`${API_URL}/api/vendor/ai/status`).then((r) => r.ok && r.json()).then((d) => d && setVideoEnabled(d.video));
  }, [refreshCredits]);

  useEffect(() => {
    if (!videoJob || videoJob.status !== 'RUNNING') return undefined;
    const t = setInterval(async () => {
      const r = await fetch(`${API_URL}/api/vendor/ai/video-jobs/${videoJob.id}`);
      if (r.ok) {
        const j = await r.json();
        setVideoJob(j);
        if (j.status !== 'RUNNING') clearInterval(t);
      }
    }, 5000);
    return () => clearInterval(t);
  }, [videoJob]);

  const run = async () => {
    setBusy(true);
    setResult(null);
    try {
      let url = `${API_URL}/api/vendor/ai/${vendorId}/${product.id}/`;
      let body = {};
      if (tab === 'generate') { url += 'generate-image'; body = { prompt }; }
      if (tab === 'enhance') { url += 'enhance-image'; body = { image_url: selectedImage, instructions: prompt }; }
      if (tab === 'video') { url += 'generate-video'; body = { prompt, image_url: selectedImage || null }; }
      const r = await fetch(url, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
      });
      const data = await r.json();
      if (!r.ok) { toast.error(typeof data.detail === 'string' ? data.detail : 'Erreur'); return; }
      if (tab === 'video') {
        setVideoJob({ id: data.job_id, status: 'RUNNING' });
        toast.success('Génération du spot lancée — cela peut prendre quelques minutes');
      } else {
        setResult(data.image_url);
        toast.success(data.attached ? 'Image ajoutée aux photos du produit' : 'Image générée (3 photos max déjà atteintes)');
        onMediaAdded?.();
      }
      refreshCredits();
    } finally { setBusy(false); }
  };

  const cost = pricing[TABS.find((t) => t.key === tab)?.action] ?? '—';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm" onClick={onClose} data-testid="ai-studio-modal">
      <div className="rounded-[20px] p-6 max-w-xl w-full max-h-[88vh] overflow-y-auto bg-white" onClick={(e) => e.stopPropagation()}
        style={{ boxShadow: '0 24px 64px rgba(76,42,110,0.3)' }}>
        <div className="flex items-start justify-between mb-1">
          <h3 className="font-display text-xl text-[#1F2A3A] flex items-center gap-2">
            <Sparkles size={18} className="text-purple-600" /> Studio IA — {product.name}
          </h3>
          <button type="button" onClick={onClose} data-testid="ai-studio-close" className="opacity-50 hover:opacity-100 p-1"><X size={18} /></button>
        </div>
        <p className="text-xs opacity-60 mb-4 flex items-center gap-1.5" data-testid="ai-studio-credits">
          <Coins size={12} className="text-amber-500" /> Solde : <strong>{credits ?? '…'} crédits</strong> · Cette action coûte <strong>{cost} crédits</strong>
        </p>

        <div className="flex gap-2 mb-4">
          {TABS.map((t) => {
            const Icon = t.icon;
            return (
              <button key={t.key} type="button" onClick={() => { setTab(t.key); setResult(null); }}
                data-testid={`ai-tab-${t.key}`}
                className={`flex-1 h-10 rounded-lg text-xs font-medium inline-flex items-center justify-center gap-1.5 border transition-all ${
                  tab === t.key ? 'border-purple-500 bg-purple-50 text-purple-700' : 'border-gray-200 text-gray-500 hover:border-gray-300'
                }`}>
                <Icon size={13} /> {t.label}
              </button>
            );
          })}
        </div>

        {tab !== 'generate' && (product.images || []).length > 0 && (
          <div className="mb-3">
            <p className="text-xs opacity-60 mb-1.5">
              {tab === 'enhance' ? 'Photo à améliorer :' : 'Générer le spot à partir d\u2019une photo du produit (rendu fidèle) :'}
            </p>
            <div className="flex gap-2 flex-wrap">
              {(product.images || []).map((img) => (
                <button key={img.url} type="button" onClick={() => setSelectedImage(img.url)}
                  data-testid={`ai-ref-image-${img.url.split('/').pop()}`}
                  className={`w-16 h-16 rounded-lg overflow-hidden border-2 ${selectedImage === img.url ? 'border-purple-500' : 'border-transparent opacity-60'}`}>
                  <img src={`${API_URL}${img.url}`} alt="" className="w-full h-full object-cover" />
                </button>
              ))}
              {tab === 'video' && (
                <button type="button" onClick={() => setSelectedImage('')}
                  data-testid="ai-ref-image-none"
                  className={`w-16 h-16 rounded-lg border-2 text-[10px] font-medium flex items-center justify-center text-center leading-tight px-1 ${
                    !selectedImage ? 'border-purple-500 bg-purple-50 text-purple-700' : 'border-gray-200 text-gray-400'}`}>
                  Sans photo (100% IA)
                </button>
              )}
            </div>
            {tab === 'video' && selectedImage && (
              <p className="text-[11px] text-purple-700 mt-1.5" data-testid="ai-video-from-photo-hint">
                🎬 Le spot sera animé à partir de la photo sélectionnée — le produit restera identique à la réalité.
              </p>
            )}
          </div>
        )}

        <textarea
          value={prompt} onChange={(e) => setPrompt(e.target.value)}
          data-testid="ai-studio-prompt"
          placeholder={tab === 'generate'
            ? 'Décrivez la mise en scène souhaitée (ex : bouteille sur plage de sable blanc au coucher du soleil)…'
            : tab === 'enhance' ? 'Instructions (optionnel) : ambiance, fond, éclairage…'
            : 'Décrivez le spot publicitaire (~20 s, moins de 20% de texte à l\u2019écran)…'}
          className="w-full h-24 p-3 rounded-lg border border-gray-200 text-sm text-[#1F2A3A] mb-3"
        />

        {tab === 'video' && !videoEnabled && (
          <p className="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded-lg p-3 mb-3" data-testid="ai-video-key-warning">
            ⚠️ La génération vidéo (Veo 3 via fal.ai) nécessite une clé API FAL_KEY. Demandez à l&apos;administrateur de la configurer (fal.ai/dashboard/keys).
          </p>
        )}

        <button type="button" onClick={run}
          disabled={busy || (tab === 'generate' && !prompt) || (tab === 'enhance' && !selectedImage) || (tab === 'video' && (!prompt || !videoEnabled))}
          data-testid="ai-studio-run"
          className="w-full h-11 rounded-lg bg-purple-600 hover:bg-purple-700 text-white text-sm font-semibold inline-flex items-center justify-center gap-2 disabled:opacity-40">
          {busy ? <Loader2 size={15} className="animate-spin" /> : <Sparkles size={15} />}
          {busy ? 'Création en cours (qualité studio)…' : `Lancer (−${cost} crédits)`}
        </button>

        {result && (
          <div className="mt-4" data-testid="ai-studio-result">
            <img src={`${API_URL}${result}`} alt="Résultat IA" className="w-full rounded-xl border" />
          </div>
        )}
        {videoJob && (
          <div className="mt-4 text-sm" data-testid="ai-video-job">
            {videoJob.status === 'RUNNING' && <p className="flex items-center gap-2 text-purple-700"><Loader2 size={14} className="animate-spin" /> Spot en cours de génération…</p>}
            {videoJob.status === 'DONE' && videoJob.video_url && (
              <video src={videoJob.video_url} controls className="w-full rounded-xl" data-testid="ai-video-player" />
            )}
            {videoJob.status === 'ERROR' && <p className="text-red-600">Échec : {videoJob.error} (crédits remboursés)</p>}
          </div>
        )}
      </div>
    </div>
  );
};
