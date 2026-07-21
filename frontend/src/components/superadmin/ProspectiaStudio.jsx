import { useCallback, useEffect, useState } from 'react';
import { Sparkles, Wand2, Clapperboard, Send, Loader2, Copy, PauseCircle, PlayCircle } from 'lucide-react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const inp = 'h-10 px-3 rounded-lg bg-white/[0.06] border border-white/15 text-sm text-white placeholder:text-white/35';
const resolveImg = (u) => (u && u.startsWith('/api/') ? `${process.env.REACT_APP_BACKEND_URL}${u}` : u);

export const ProspectiaStudio = () => {
  const [form, setForm] = useState({ target: 'vendor', territory: '', sector: '', lang: 'fr', tone: '', content_type: 'email' });
  const [content, setContent] = useState('');
  const [generating, setGenerating] = useState(false);
  const [storyboard, setStoryboard] = useState([]);
  const [sbLoading, setSbLoading] = useState(false);
  const [campaign, setCampaign] = useState({ name: '', subject: '', prospects_csv: '' });
  const [campaigns, setCampaigns] = useState([]);
  const [launching, setLaunching] = useState(false);

  const loadCampaigns = useCallback(() => {
    fetch(`${API}/admin/prospectia/campaigns`, { credentials: 'include' })
      .then((r) => r.json()).then((d) => setCampaigns(d.items || [])).catch(() => {});
  }, []);
  useEffect(() => { loadCampaigns(); }, [loadCampaigns]);

  const generate = async () => {
    setGenerating(true); setStoryboard([]);
    const r = await fetch(`${API}/admin/prospectia/generate`, {
      method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form),
    });
    const d = await r.json();
    setGenerating(false);
    if (!r.ok) return toast.error(d.detail || 'Génération impossible');
    setContent(d.content);
    toast.success('Script généré par PROSPECT\'IA');
  };

  const genStoryboard = async () => {
    if (!content) return;
    setSbLoading(true);
    const r = await fetch(`${API}/admin/prospectia/storyboard`, {
      method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ script: content, hint: `${form.target} ${form.sector} ${form.territory}` }),
    });
    const d = await r.json();
    setSbLoading(false);
    if (!r.ok) return toast.error(d.detail || 'Storyboard indisponible');
    setStoryboard(d.images || []);
    toast.success(`${d.images.length} illustration(s) de storyboard générée(s)`);
  };

  const launch = async () => {
    if (!content) return toast.error("Générez d'abord un script");
    if (!campaign.subject.trim() && form.content_type === 'email') return toast.error('Objet requis');
    setLaunching(true);
    const r = await fetch(`${API}/admin/prospectia/campaigns`, {
      method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: campaign.name || 'Campagne PROSPECT\'IA', subject: campaign.subject || 'Rejoignez la Communityplace KDMARCHÉ × O\'SCOP', body: content, prospects_csv: campaign.prospects_csv }),
    });
    const d = await r.json();
    setLaunching(false);
    if (!r.ok) return toast.error(d.detail || 'Lancement impossible');
    toast.success(`Campagne lancée — ${d.sent_count} premier(s) email(s) envoyés`);
    setCampaign({ name: '', subject: '', prospects_csv: '' });
    loadCampaigns();
  };

  const pause = async (c) => {
    const r = await fetch(`${API}/admin/prospectia/campaigns/${c.id}/pause`, { method: 'POST', credentials: 'include' });
    if (r.ok) { toast.success('Statut mis à jour'); loadCampaigns(); }
  };

  return (
    <div className="glass-panel-soft rounded-[18px] p-5" data-testid="prospectia-studio">
      <h3 className="font-display text-base text-white flex items-center gap-2 mb-3">
        <Sparkles size={15} style={{ color: '#D9B35A' }} /> Studio PROSPECT'IA
      </h3>
      <div className="flex flex-wrap gap-2 mb-3">
        <select value={form.target} onChange={(e) => setForm({ ...form, target: e.target.value })} data-testid="prospectia-target" className={`${inp} w-44`}>
          <option value="vendor">Cible : Vendeurs</option>
          <option value="buyer">Cible : Acheteurs</option>
        </select>
        <select value={form.content_type} onChange={(e) => setForm({ ...form, content_type: e.target.value })} data-testid="prospectia-type" className={`${inp} w-48`}>
          <option value="email">Email de prospection</option>
          <option value="whatsapp">Message WhatsApp/LinkedIn</option>
          <option value="video_script">Script vidéo (scènes + voix off)</option>
        </select>
        <select value={form.lang} onChange={(e) => setForm({ ...form, lang: e.target.value })} className={`${inp} w-28`}>
          <option value="fr">🇫🇷 FR</option><option value="en">🇬🇧 EN</option><option value="es">🇪🇸 ES</option>
        </select>
        <input value={form.territory} onChange={(e) => setForm({ ...form, territory: e.target.value })} placeholder="Territoire (ex : Guadeloupe)" className={`${inp} w-48`} />
        <input value={form.sector} onChange={(e) => setForm({ ...form, sector: e.target.value })} placeholder="Secteur (ex : agroalimentaire)" className={`${inp} w-48`} />
        <button onClick={generate} disabled={generating} data-testid="prospectia-generate-btn"
          className="h-10 px-4 rounded-lg text-sm font-semibold text-[#1A092D] inline-flex items-center gap-1.5 disabled:opacity-50"
          style={{ background: 'linear-gradient(135deg, #D9B35A, #F2D07A)' }}>
          {generating ? <Loader2 size={14} className="animate-spin" /> : <Wand2 size={14} />} Générer
        </button>
      </div>

      {content && (
        <div className="mb-4">
          <textarea value={content} onChange={(e) => setContent(e.target.value)} rows={10} data-testid="prospectia-content"
            className="w-full p-3 rounded-xl bg-black/25 border border-white/15 text-xs text-white/85 font-mono" />
          <div className="flex gap-2 mt-2">
            <button onClick={() => { navigator.clipboard.writeText(content); toast.success('Copié'); }}
              className="h-9 px-3 rounded-lg text-xs border border-white/15 text-white/70 hover:bg-white/10 inline-flex items-center gap-1.5">
              <Copy size={12} /> Copier
            </button>
            {form.content_type === 'video_script' && (
              <button onClick={genStoryboard} disabled={sbLoading} data-testid="prospectia-storyboard-btn"
                className="h-9 px-3 rounded-lg text-xs border border-[#D9B35A]/40 text-[#E9CF8E] hover:bg-[#D9B35A]/10 inline-flex items-center gap-1.5 disabled:opacity-50">
                {sbLoading ? <Loader2 size={12} className="animate-spin" /> : <Clapperboard size={12} />} Générer le storyboard illustré
              </button>
            )}
          </div>
          {storyboard.length > 0 && (
            <div className="grid grid-cols-3 gap-2 mt-3" data-testid="prospectia-storyboard">
              {storyboard.map((u) => <img key={u} src={resolveImg(u)} alt="storyboard" className="rounded-xl border border-white/10 w-full" />)}
            </div>
          )}

          <div className="mt-4 pt-4 border-t border-white/10">
            <p className="text-xs text-white/55 mb-2 flex items-center gap-1.5"><Send size={12} className="text-[#D9B35A]" /> Envoi autonome — collez vos prospects (un par ligne : <code>email, entreprise, prénom</code>). Variables : {'{prenom} {entreprise} {lien}'}</p>
            <div className="flex flex-wrap gap-2 mb-2">
              <input value={campaign.name} onChange={(e) => setCampaign({ ...campaign, name: e.target.value })} placeholder="Nom de la campagne" className={`${inp} w-52`} data-testid="prospectia-campaign-name" />
              <input value={campaign.subject} onChange={(e) => setCampaign({ ...campaign, subject: e.target.value })} placeholder="Objet de l'email" className={`${inp} flex-1 min-w-[220px]`} data-testid="prospectia-campaign-subject" />
            </div>
            <textarea value={campaign.prospects_csv} onChange={(e) => setCampaign({ ...campaign, prospects_csv: e.target.value })} rows={3}
              placeholder={"jean@entreprise.gp, Distillerie Bel Air, Jean\nmarie@resto.mq, Le Ti Punch, Marie"}
              data-testid="prospectia-prospects" className="w-full p-3 rounded-xl bg-white/[0.05] border border-white/15 text-xs text-white placeholder:text-white/30" />
            <button onClick={launch} disabled={launching} data-testid="prospectia-launch-btn"
              className="mt-2 h-10 px-4 rounded-lg text-sm font-semibold text-[#1A092D] inline-flex items-center gap-1.5 disabled:opacity-50"
              style={{ background: 'linear-gradient(135deg, #D9B35A, #F2D07A)' }}>
              {launching ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />} Lancer la campagne
            </button>
          </div>
        </div>
      )}

      {campaigns.length > 0 && (
        <div className="space-y-2 mt-2" data-testid="prospectia-campaigns">
          <p className="text-xs text-white/55 font-semibold">Campagnes ({campaigns.length})</p>
          {campaigns.map((c) => (
            <div key={c.id} className="flex items-center gap-3 p-2.5 rounded-xl bg-white/[0.04] border border-white/10 text-xs flex-wrap">
              <span className="text-white font-medium">{c.name}</span>
              <span className="text-white/50">{c.sent_count}/{c.prospects_total} envoyés · {c.click_count} clic(s)</span>
              <span className={`px-2 py-0.5 rounded font-semibold ${c.status === 'done' ? 'bg-emerald-400/15 text-emerald-300' : c.status === 'paused' ? 'bg-white/10 text-white/50' : 'bg-[#D9B35A]/15 text-[#E9CF8E]'}`}>
                {c.status === 'done' ? 'Terminée' : c.status === 'paused' ? 'En pause' : 'En cours'}
              </span>
              {c.status !== 'done' && (
                <button onClick={() => pause(c)} className="ml-auto p-1.5 rounded-lg hover:bg-white/10 text-white/60" title={c.status === 'running' ? 'Mettre en pause' : 'Reprendre'}>
                  {c.status === 'running' ? <PauseCircle size={14} /> : <PlayCircle size={14} />}
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
