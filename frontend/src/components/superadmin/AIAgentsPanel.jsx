import { useCallback, useEffect, useState } from 'react';
import { Bot, Sparkles, Gavel, Loader2, Store } from 'lucide-react';
import { toast } from 'sonner';
import { Switch } from '../ui/switch';
import { ProspectiaStudio } from './ProspectiaStudio';
import { SocialProofPanel } from './SocialProofPanel';
import { ProspectiaPipeline } from './ProspectiaPipeline';
import { AIUsagePanel } from './AIUsagePanel';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const AIAgentsPanel = () => {
  const [settings, setSettings] = useState(null);
  const [reports, setReports] = useState([]);

  const load = useCallback(() => {
    fetch(`${API}/admin/ai-agents`, { credentials: 'include' })
      .then((r) => r.json()).then(setSettings).catch(() => {});
    fetch(`${API}/admin/ai-agents/encheria/reports`, { credentials: 'include' })
      .then((r) => r.json()).then((d) => setReports(d.items || [])).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const toggle = async (key, value) => {
    const r = await fetch(`${API}/admin/ai-agents`, {
      method: 'PUT', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ [key]: value }),
    });
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    setSettings(d);
    toast.success(value ? 'Agent activé' : 'Agent désactivé');
  };

  if (!settings) return <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 animate-spin text-[#D9B35A]" /></div>;

  return (
    <div className="space-y-6" data-testid="ai-agents-panel">
      <div className="grid md:grid-cols-3 gap-4">
        <div className="glass-panel-soft rounded-[18px] p-5" data-testid="prospectia-card">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-display text-lg text-white flex items-center gap-2">
              <Sparkles size={16} style={{ color: '#D9B35A' }} /> PROSPECT'IA
            </h3>
            <Switch checked={!!settings.prospectia_enabled}
              onCheckedChange={(v) => toggle('prospectia_enabled', v)} data-testid="prospectia-switch" />
          </div>
          <p className="text-xs text-white/50">
            Agent de prospection autonome : rédige emails, messages et scripts vidéo (storyboard illustré),
            envoie seul vos campagnes (A/B test, relances J+3/J+7, pipeline de vente organisé) et gère la preuve
            sociale (témoignages : invitation, relance J+7, reformulation, traduction EN/ES).
          </p>
        </div>
        <div className="glass-panel-soft rounded-[18px] p-5" data-testid="encheria-card">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-display text-lg text-white flex items-center gap-2">
              <Gavel size={16} style={{ color: '#D9B35A' }} /> ENCHÈR'IA
            </h3>
            <Switch checked={!!settings.encheria_enabled}
              onCheckedChange={(v) => toggle('encheria_enabled', v)} data-testid="encheria-switch" />
          </div>
          <p className="text-xs text-white/50">
            Agent des enchères inversées : relance automatiquement les vendeurs sans offre à J-2 de la clôture,
            puis produit un rapport d'adjudication IA (analyse des offres, risques, recommandation) à la clôture.
          </p>
        </div>
        <div className="glass-panel-soft rounded-[18px] p-5" data-testid="ventia-card">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-display text-lg text-white flex items-center gap-2">
              <Store size={16} style={{ color: '#D9B35A' }} /> VENT'IA
            </h3>
            <Switch checked={!!settings.ventia_enabled}
              onCheckedChange={(v) => toggle('ventia_enabled', v)} data-testid="ventia-switch" />
          </div>
          <p className="text-xs text-white/50">
            Assistant de vente des vendeurs : génère les descriptions produits et conseils de prix par IA
            dans le formulaire produit, et relance automatiquement par email les paniers abandonnés depuis 24h.
          </p>
        </div>
      </div>

      <AIUsagePanel />

      {settings.prospectia_enabled && <ProspectiaPipeline />}
      {settings.prospectia_enabled && <ProspectiaStudio />}
      {settings.prospectia_enabled && <SocialProofPanel />}

      {settings.encheria_enabled && (
        <div className="glass-panel-soft rounded-[18px] p-5" data-testid="encheria-reports">
          <h3 className="font-display text-base text-white flex items-center gap-2 mb-3">
            <Bot size={15} style={{ color: '#D9B35A' }} /> Rapports d'adjudication ENCHÈR'IA
            <span className="text-sm font-normal text-white/50">({reports.length})</span>
          </h3>
          {reports.length ? (
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {reports.map((r) => (
                <div key={r.id} className="p-3 rounded-xl bg-white/[0.04] border border-white/10">
                  <p className="text-sm text-white font-medium mb-1">{r.title} <span className="text-white/40 text-xs">· {r.bids_count} offre(s) · {new Date(r.created_at).toLocaleString('fr-FR')}</span></p>
                  <p className="text-xs text-white/60 whitespace-pre-line">{r.report}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-white/40">Aucun rapport pour le moment — ils sont générés automatiquement à la clôture de chaque consultation.</p>
          )}
        </div>
      )}
    </div>
  );
};
