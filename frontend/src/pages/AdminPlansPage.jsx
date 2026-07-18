import i18n from '@/i18n';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Loader2, Coins, Layers, Settings2, Users } from 'lucide-react';
import { toast } from 'sonner';
import NavBar from '../components/NavBar';
import { authAPI, adminPlansAPI } from '../services/api';
import { StatsCard } from '../components/admin/plans/shared';
import { PlanFormModal } from '../components/admin/plans/PlanFormModal';
import { OptionFormModal } from '../components/admin/plans/OptionFormModal';
import { CreditAdjustModal } from '../components/admin/plans/CreditAdjustModal';
import { PlansTab } from '../components/admin/plans/PlansTab';
import { OptionsTab } from '../components/admin/plans/OptionsTab';
import { CreditsTab } from '../components/admin/plans/CreditsTab';

const AdminPlansPage = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('plans');
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);

  // Plans
  const [plans, setPlans] = useState([]);
  const [planModalOpen, setPlanModalOpen] = useState(false);
  const [editingPlan, setEditingPlan] = useState(null);

  // Options
  const [options, setOptions] = useState([]);
  const [optionModalOpen, setOptionModalOpen] = useState(false);
  const [editingOption, setEditingOption] = useState(null);

  // Credits
  const [users, setUsers] = useState({ users: [], total: 0, page: 1, has_more: false });
  const [creditSearch, setCreditSearch] = useState('');
  const [creditModalOpen, setCreditModalOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);

  // Guard
  useEffect(() => {
    const check = async () => {
      if (!authAPI.isAuthenticated()) {
        navigate('/connexion');
        return;
      }
      try {
        const me = await authAPI.getMe();
        const isAdmin = me?.is_admin || me?.role === 'admin' || me?.email?.includes('admin');
        if (!isAdmin) {
          toast.error(i18n.t('adm.acces_reserve_aux_administrateurs'));
          navigate('/dashboard');
          return;
        }
        await loadAll();
      } catch (e) {
        toast.error(i18n.t('adm.erreur_de_chargement'));
        navigate('/dashboard');
      }
    };
    check();
    // eslint-disable-next-line
  }, [navigate]);

  const loadAll = async () => {
    setLoading(true);
    try {
      const [s, p, o, u] = await Promise.all([
        adminPlansAPI.getStats(),
        adminPlansAPI.listPlans(true),
        adminPlansAPI.listOptions(true),
        adminPlansAPI.listUsersWithCredits('', 1, 20),
      ]);
      setStats(s);
      setPlans(p);
      setOptions(o);
      setUsers(u);
    } catch (e) {
      toast.error(e.message || 'Erreur de chargement');
    } finally {
      setLoading(false);
    }
  };

  // --- Plan handlers ---
  const handleCreatePlan = () => {
    setEditingPlan(null);
    setPlanModalOpen(true);
  };
  const handleEditPlan = (plan) => {
    setEditingPlan(plan);
    setPlanModalOpen(true);
  };
  const handleSavePlan = async (data) => {
    if (editingPlan) {
      await adminPlansAPI.updatePlan(editingPlan.id, data);
      toast.success(i18n.t('adm.plan_mis_a_jour'));
    } else {
      await adminPlansAPI.createPlan(data);
      toast.success(i18n.t('adm.plan_cree'));
    }
    await loadAll();
  };
  const handleDeletePlan = async (plan) => {
    if (!window.confirm(i18n.t('adm.supprimer_desactiver_plan', { name: plan.name }))) return;
    try {
      const force = plan.subscribers_count === 0;
      const res = await adminPlansAPI.deletePlan(plan.id, force);
      toast.success(res.message || i18n.t('adm.plan_supprime'));
      await loadAll();
    } catch (e) {
      toast.error(e.message || 'Erreur');
    }
  };
  const handleToggleVisible = async (plan) => {
    try {
      await adminPlansAPI.updatePlan(plan.id, { visible: plan.visible === false });
      toast.success(plan.visible === false ? 'Plan affiché sur la page publique' : 'Plan masqué de la page publique');
      await loadAll();
    } catch (e) {
      toast.error(e.message || 'Erreur');
    }
  };

  // --- Option handlers ---
  const handleCreateOption = () => {
    setEditingOption(null);
    setOptionModalOpen(true);
  };
  const handleEditOption = (opt) => {
    setEditingOption(opt);
    setOptionModalOpen(true);
  };
  const handleSaveOption = async (data) => {
    if (editingOption) {
      await adminPlansAPI.updateOption(editingOption.id, data);
      toast.success(i18n.t('adm.option_mise_a_jour'));
    } else {
      await adminPlansAPI.createOption(data);
      toast.success(i18n.t('adm.option_creee'));
    }
    await loadAll();
  };
  const handleDeleteOption = async (opt) => {
    if (!window.confirm(`Supprimer l'option "${opt.name}" ?`)) return;
    try {
      await adminPlansAPI.deleteOption(opt.id);
      toast.success(i18n.t('adm.option_supprimee'));
      await loadAll();
    } catch (e) {
      toast.error(e.message || 'Erreur');
    }
  };

  // --- Credits handlers ---
  const handleSearchUsers = async () => {
    try {
      const u = await adminPlansAPI.listUsersWithCredits(creditSearch, 1, 20);
      setUsers(u);
    } catch (e) {
      toast.error(e.message || 'Erreur de recherche');
    }
  };
  const handleOpenAdjust = (user) => {
    setSelectedUser(user);
    setCreditModalOpen(true);
  };
  const handleSaveAdjust = async (data) => {
    const res = await adminPlansAPI.adjustUserCredits(selectedUser.user_id, data);
    toast.success(res.message || i18n.t('adm.credits_ajustes'));
    await handleSearchUsers();
    await adminPlansAPI.getStats().then(setStats).catch(() => {});
  };

  if (loading) {
    return (
      <div
        className="min-h-screen flex items-center justify-center"
        style={{ background: '#0B1220' }}
      >
        <Loader2 className="w-10 h-10 animate-spin" style={{ color: '#D9B35A' }} />
      </div>
    );
  }

  return (
    <div className="on-dark" style={{ background: 'linear-gradient(180deg, #0B1220 0%, #0E1526 60%, #0B1220 100%)', minHeight: '100vh' }}>
      <NavBar />
      <div className="pt-24 pb-12 px-4 sm:px-6 lg:px-12 max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <button
              onClick={() => navigate('/superadmin')}
              className="flex items-center gap-2 text-sm text-white/60 hover:text-white mb-2"
              data-testid="back-to-superadmin"
            >
              <ArrowLeft className="w-4 h-4" /> {i18n.t('adm.retour_super_admin')}
            </button>
            <h1 className="text-3xl sm:text-4xl font-bold text-white">
              {i18n.t('adm.plans_options_credits')}
            </h1>
            <p className="text-white/75 text-sm mt-1">
              {i18n.t('adm.gerez_dynamiquement')}
            </p>
          </div>
        </div>

        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <StatsCard
              icon={Layers}
              label={i18n.t('adm.plans_actifs')}
              value={`${stats.plans.active} / ${stats.plans.total}`}
            />
            <StatsCard
              icon={Settings2}
              label={i18n.t('adm.options_actives')}
              value={`${stats.options.active} / ${stats.options.total}`}
              color="#7AB7FF"
            />
            <StatsCard
              icon={Users}
              label={i18n.t('adm.abonnement')}
              value={stats.subscriptions.active}
              color="#9CFF7A"
            />
            <StatsCard
              icon={Coins}
              label={i18n.t('adm.credits_distribues')}
              value={stats.credits.total_distributed}
              color="#FFB347"
            />
          </div>
        )}

        {/* Tabs */}
        <div
          className="flex gap-2 mb-6 p-1 rounded-xl w-fit"
          style={{ background: 'rgba(255,255,255,0.05)' }}
        >
          {[
            { id: 'plans', label: i18n.t('adm.plans_d_abonnement'), icon: Layers },
            { id: 'options', label: i18n.t('adm.options_addons'), icon: Settings2 },
            { id: 'credits', label: i18n.t('adm.credits_utilisateurs'), icon: Coins },
          ].map((t) => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              data-testid={`tab-${t.id}`}
              className="px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition"
              style={{
                background: activeTab === t.id ? '#D9B35A' : 'transparent',
                color: activeTab === t.id ? '#070A10' : 'rgba(255,255,255,0.7)',
              }}
            >
              <t.icon className="w-4 h-4" /> {t.label}
            </button>
          ))}
        </div>

        {activeTab === 'plans' && (
          <PlansTab
            plans={plans}
            onCreate={handleCreatePlan}
            onEdit={handleEditPlan}
            onDelete={handleDeletePlan}
            onToggleVisible={handleToggleVisible}
          />
        )}

        {activeTab === 'options' && (
          <OptionsTab
            options={options}
            onCreate={handleCreateOption}
            onEdit={handleEditOption}
            onDelete={handleDeleteOption}
          />
        )}

        {activeTab === 'credits' && (
          <CreditsTab
            users={users}
            creditSearch={creditSearch}
            setCreditSearch={setCreditSearch}
            onSearch={handleSearchUsers}
            onAdjust={handleOpenAdjust}
          />
        )}
      </div>

      {/* Modals */}
      <PlanFormModal
        open={planModalOpen}
        onClose={() => setPlanModalOpen(false)}
        onSave={handleSavePlan}
        initialData={editingPlan}
        isEdit={!!editingPlan}
      />
      <OptionFormModal
        open={optionModalOpen}
        onClose={() => setOptionModalOpen(false)}
        onSave={handleSaveOption}
        initialData={editingOption}
        isEdit={!!editingOption}
        plans={plans}
      />
      <CreditAdjustModal
        open={creditModalOpen}
        onClose={() => setCreditModalOpen(false)}
        onSave={handleSaveAdjust}
        user={selectedUser}
      />
    </div>
  );
};

export default AdminPlansPage;
