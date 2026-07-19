import i18n from '@/i18n';
import { useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import { ShieldCheck, UserMinus } from 'lucide-react';
import { GrantRoleForm, CreateMemberForm } from './TeamMemberForms';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const ROLE_COLORS = {
  SUPER_ADMIN: '#E64432', OSCOP_SUPER_ADMIN: '#E64432',
  ADMIN: '#B8860B', COOPER: '#6FA82E', EXPERT: '#5B2E8C',
};

export const TeamRolesTab = () => {
  const [members, setMembers] = useState([]);
  const [roles, setRoles] = useState([]);

  const refresh = useCallback(async () => {
    const [teamR, rolesR] = await Promise.all([
      fetch(`${API}/admin/team`, { credentials: 'include' }),
      fetch(`${API}/admin/team/roles`, { credentials: 'include' }),
    ]);
    if (teamR.ok) setMembers((await teamR.json()).members || []);
    if (rolesR.ok) setRoles((await rolesR.json()).roles || []);
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const revoke = async (userId) => {
    const r = await fetch(`${API}/admin/team/revoke`, {
      method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId }),
    });
    const data = await r.json();
    if (r.ok) { toast.success(i18n.t('adm.team_revoked_ok')); refresh(); }
    else toast.error(typeof data.detail === 'string' ? data.detail : 'ERROR');
  };

  const isSuper = (m) => (m.role || '').toUpperCase().includes('SUPER_ADMIN') || m.is_admin;

  return (
    <div className="space-y-6" data-testid="team-roles-tab">
      <div>
        <h2 className="text-xl font-bold text-[#1F2A3A] flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-[#D9B35A]" />
          {i18n.t('adm.team_title')}
        </h2>
        <p className="text-sm opacity-60 mt-1">{i18n.t('adm.team_subtitle')}</p>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <GrantRoleForm roles={roles} onDone={refresh} />
        <CreateMemberForm roles={roles} onDone={refresh} />
      </div>

      <div className="glass-panel-soft rounded-[18px] p-5" data-testid="team-members-list">
        <h3 className="font-display text-lg mb-4 text-[#1F2A3A]">
          {i18n.t('adm.team_members')} <span className="text-sm font-normal opacity-50">({members.length})</span>
        </h3>
        <div className="divide-y divide-black/5">
          {members.map((m) => {
            const color = ROLE_COLORS[(m.role || '').toUpperCase()] || '#5B7A9A';
            return (
              <div key={m.id} className="flex items-center justify-between gap-3 py-2.5" data-testid={`team-member-${m.id}`}>
                <div className="min-w-0">
                  <p className="text-sm font-medium text-[#1F2A3A] truncate">{m.contact_name || m.email}</p>
                  <p className="text-xs opacity-50 truncate">
                    {m.email}
                    {m.role_granted_by && <span> · {i18n.t('adm.team_granted_by')} {m.role_granted_by}</span>}
                  </p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span
                    className="text-[10px] font-bold px-2.5 py-1 rounded-full uppercase tracking-wide"
                    style={{ color, background: `${color}22`, border: `1px solid ${color}66` }}
                    data-testid={`team-role-badge-${m.id}`}
                  >
                    {m.role || 'ADMIN'}
                  </span>
                  {!isSuper(m) && (
                    <button
                      type="button" onClick={() => revoke(m.id)}
                      data-testid={`team-revoke-${m.id}`}
                      title={i18n.t('adm.team_revoke')}
                      className="p-1.5 rounded-lg opacity-40 hover:opacity-100 hover:bg-red-500/10 text-red-500 transition-all"
                    >
                      <UserMinus size={14} />
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
