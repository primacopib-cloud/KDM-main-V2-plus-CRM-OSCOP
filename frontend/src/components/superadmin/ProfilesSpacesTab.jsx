import { useCallback, useEffect, useState } from 'react';
import { UsersRound, Plus, Pencil, Trash2, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';
import { ProfileFormModal } from './ProfileFormModal';

export const ProfilesSpacesTab = () => {
  const [profiles, setProfiles] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(null); // null | 'new' | profile

  const load = useCallback(() => {
    fetch(`${API}/admin/member-profiles`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => { if (d) { setProfiles(d.profiles); setTemplates(d.convention_templates); } })
      .catch(() => toast.error('Erreur de chargement des profils'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const toggleActive = async (p) => {
    const r = await fetch(`${API}/admin/member-profiles/${p.slug}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      credentials: 'include', body: JSON.stringify({ active: !p.active }),
    });
    if (r.ok) { toast.success(p.active ? 'Profil désactivé' : 'Profil activé'); load(); }
  };

  const remove = async (p) => {
    if (!window.confirm(`Supprimer le profil « ${p.titles?.fr} » ?`)) return;
    const r = await fetch(`${API}/admin/member-profiles/${p.slug}`, {
      method: 'DELETE', headers: getAuthHeaders(), credentials: 'include',
    });
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Suppression impossible');
    toast.success('Profil supprimé');
    load();
  };

  return (
    <div className="space-y-4" data-testid="profiles-spaces-tab">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-white flex items-center gap-2">
          <UsersRound className="w-4 h-4 text-[#D9B35A]" /> Profils &amp; Espaces d'adhésion
        </h2>
        <button type="button" onClick={() => setModal('new')} data-testid="profile-create-btn"
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold"
          style={{ background: 'linear-gradient(135deg, #D9B35A 0%, #b8933e 100%)', color: '#1F0A33' }}>
          <Plus className="w-3.5 h-3.5" /> Nouveau profil
        </button>
      </div>
      <p className="text-[11px] text-white/45">
        Les profils actifs apparaissent comme cartes de choix sur la page d'adhésion publique.
        Chaque profil détermine l'espace de destination et la convention tripartite applicable.
      </p>
      {loading ? (
        <div className="flex justify-center py-10"><Loader2 className="w-6 h-6 animate-spin text-[#D9B35A]" /></div>
      ) : (
        <div className="space-y-2">
          {profiles.map((p) => (
            <div key={p.slug} className="glass-panel-soft rounded-[14px] p-3 flex flex-wrap items-center gap-3"
              data-testid={`profile-row-${p.slug}`}>
              <div className="flex-1 min-w-[200px]">
                <p className="text-sm font-bold text-white flex items-center gap-2">
                  {p.titles?.fr}
                  {p.system && <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-white/10 text-white/50">SYSTÈME</span>}
                  <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${p.active ? 'bg-[#7BC94E]/15 text-[#7BC94E]' : 'bg-red-500/15 text-red-400'}`}>
                    {p.active ? 'ACTIF' : 'INACTIF'}
                  </span>
                </p>
                <p className="text-[10.5px] text-white/45 mt-0.5">
                  {p.slug} · espace {p.space_route} · convention {p.convention_template === 'v1_5_vendor' ? 'V1.5 fournisseur' : 'V2.0 acheteur + attestation'} · {p.adhesions_count || 0} adhésion(s)
                </p>
              </div>
              <div className="flex items-center gap-1.5">
                <button type="button" onClick={() => toggleActive(p)} data-testid={`profile-toggle-${p.slug}`}
                  className="px-2.5 py-1.5 rounded-lg text-[10.5px] font-bold bg-white/10 text-white/65 hover:text-white">
                  {p.active ? 'Désactiver' : 'Activer'}
                </button>
                <button type="button" onClick={() => setModal(p)} data-testid={`profile-edit-${p.slug}`}
                  className="p-1.5 rounded-lg bg-white/10 text-white/65 hover:text-[#E9CF8E]">
                  <Pencil className="w-3.5 h-3.5" />
                </button>
                {!p.system && (
                  <button type="button" onClick={() => remove(p)} data-testid={`profile-delete-${p.slug}`}
                    className="p-1.5 rounded-lg bg-white/10 text-white/65 hover:text-red-400">
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
      {modal && (
        <ProfileFormModal initial={modal === 'new' ? null : modal} templates={templates}
          onClose={() => setModal(null)} onSaved={() => { setModal(null); load(); }} />
      )}
    </div>
  );
};
