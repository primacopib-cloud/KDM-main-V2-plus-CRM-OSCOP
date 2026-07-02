import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Plus,
  Pencil,
  Trash2,
  X,
  Save,
  Search,
  Loader2,
  Coins,
  Layers,
  Settings2,
  CheckCircle2,
  XCircle,
  Star,
  TrendingUp,
  Users,
  Package,
  CreditCard,
} from 'lucide-react';
import { toast } from 'sonner';
import NavBar from '../components/NavBar';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';
import { Textarea } from '../components/ui/textarea';
import { Switch } from '../components/ui/switch';
import { Label } from '../components/ui/label';
import { authAPI, adminPlansAPI } from '../services/api';

const EMPTY_PLAN = {
  name: '',
  description: '',
  price_cents: 0,
  period: 'mois',
  default_credits: 100,
  features: [],
  popular: false,
  active: true,
  sort_order: 0,
  max_zones: 1,
  max_users: 1,
  color: '#D9B35A',
};

const EMPTY_OPTION = {
  name: '',
  description: '',
  price_cents: 0,
  period: 'mois',
  credits_included: 0,
  compatible_plans: [],
  active: true,
  sort_order: 0,
};

const formatPrice = (cents) => `${(cents / 100).toFixed(2)} €`;

const PlanFormModal = ({ open, onClose, onSave, initialData, isEdit }) => {
  const [data, setData] = useState(initialData || EMPTY_PLAN);
  const [featuresText, setFeaturesText] = useState(
    (initialData?.features || []).join('\n')
  );
  const [saving, setSaving] = useState(false);
  const [priceEur, setPriceEur] = useState(
    ((initialData?.price_cents || 0) / 100).toString()
  );

  useEffect(() => {
    setData(initialData || EMPTY_PLAN);
    setFeaturesText((initialData?.features || []).join('\n'));
    setPriceEur(((initialData?.price_cents || 0) / 100).toString());
  }, [initialData]);

  if (!open) return null;

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload = {
        ...data,
        price_cents: Math.round(parseFloat(priceEur || 0) * 100),
        features: featuresText
          .split('\n')
          .map((s) => s.trim())
          .filter(Boolean),
      };
      await onSave(payload);
      onClose();
    } catch (e) {
      toast.error(e.message || 'Erreur lors de l\'enregistrement');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.7)' }}
      data-testid="plan-form-modal"
    >
      <div
        className="rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
        style={{ background: '#0f1623', border: '1px solid rgba(217,179,90,0.3)' }}
      >
        <div className="flex items-center justify-between p-5 border-b border-white/10">
          <h2 className="text-xl font-bold text-white">
            {isEdit ? 'Modifier le plan' : 'Nouveau plan d\'abonnement'}
          </h2>
          <button
            onClick={onClose}
            className="text-white/60 hover:text-white"
            data-testid="plan-modal-close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          <div>
            <Label className="text-white/80">Nom du plan</Label>
            <Input
              data-testid="plan-name-input"
              value={data.name}
              onChange={(e) => setData({ ...data, name: e.target.value })}
              placeholder="ex. ESS PREMIUM"
              className="bg-white/5 border-white/10 text-white"
            />
          </div>

          <div>
            <Label className="text-white/80">Description</Label>
            <Textarea
              data-testid="plan-description-input"
              value={data.description || ''}
              onChange={(e) => setData({ ...data, description: e.target.value })}
              placeholder="Description courte du plan"
              className="bg-white/5 border-white/10 text-white"
              rows={2}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label className="text-white/80">Prix (€)</Label>
              <Input
                data-testid="plan-price-input"
                type="number"
                step="0.01"
                value={priceEur}
                onChange={(e) => setPriceEur(e.target.value)}
                className="bg-white/5 border-white/10 text-white"
              />
            </div>
            <div>
              <Label className="text-white/80">Période</Label>
              <select
                data-testid="plan-period-select"
                value={data.period}
                onChange={(e) => setData({ ...data, period: e.target.value })}
                className="w-full px-3 py-2 rounded-md bg-white/5 border border-white/10 text-white"
              >
                <option value="mois">mois</option>
                <option value="an">an</option>
                <option value="unique">unique</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <Label className="text-white/80">Crédits par défaut</Label>
              <Input
                data-testid="plan-credits-input"
                type="number"
                value={data.default_credits}
                onChange={(e) =>
                  setData({ ...data, default_credits: parseInt(e.target.value || 0) })
                }
                className="bg-white/5 border-white/10 text-white"
              />
            </div>
            <div>
              <Label className="text-white/80">Zones max</Label>
              <Input
                type="number"
                value={data.max_zones}
                onChange={(e) =>
                  setData({ ...data, max_zones: parseInt(e.target.value || 1) })
                }
                className="bg-white/5 border-white/10 text-white"
              />
            </div>
            <div>
              <Label className="text-white/80">Utilisateurs max</Label>
              <Input
                type="number"
                value={data.max_users}
                onChange={(e) =>
                  setData({ ...data, max_users: parseInt(e.target.value || 1) })
                }
                className="bg-white/5 border-white/10 text-white"
              />
            </div>
          </div>

          <div>
            <Label className="text-white/80">Fonctionnalités (une par ligne)</Label>
            <Textarea
              data-testid="plan-features-input"
              value={featuresText}
              onChange={(e) => setFeaturesText(e.target.value)}
              placeholder="Accès catalogue&#10;Crédits inclus&#10;..."
              className="bg-white/5 border-white/10 text-white font-mono text-sm"
              rows={6}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label className="text-white/80">Ordre d'affichage</Label>
              <Input
                type="number"
                value={data.sort_order}
                onChange={(e) =>
                  setData({ ...data, sort_order: parseInt(e.target.value || 0) })
                }
                className="bg-white/5 border-white/10 text-white"
              />
            </div>
            <div>
              <Label className="text-white/80">Couleur</Label>
              <Input
                type="color"
                value={data.color || '#D9B35A'}
                onChange={(e) => setData({ ...data, color: e.target.value })}
                className="bg-white/5 border-white/10 text-white h-10"
              />
            </div>
          </div>

          <div className="flex items-center justify-between gap-4 pt-2">
            <div className="flex items-center gap-2">
              <Switch
                data-testid="plan-popular-switch"
                checked={data.popular}
                onCheckedChange={(v) => setData({ ...data, popular: v })}
              />
              <Label className="text-white/80">Plan populaire</Label>
            </div>
            <div className="flex items-center gap-2">
              <Switch
                data-testid="plan-active-switch"
                checked={data.active}
                onCheckedChange={(v) => setData({ ...data, active: v })}
              />
              <Label className="text-white/80">Actif</Label>
            </div>
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 p-5 border-t border-white/10">
          <Button
            variant="ghost"
            onClick={onClose}
            data-testid="plan-modal-cancel"
            className="text-white/70"
          >
            Annuler
          </Button>
          <Button
            onClick={handleSave}
            disabled={saving || !data.name}
            data-testid="plan-modal-save"
            style={{ background: '#D9B35A', color: '#070A10' }}
          >
            {saving ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Save className="w-4 h-4 mr-2" />
            )}
            Enregistrer
          </Button>
        </div>
      </div>
    </div>
  );
};

const OptionFormModal = ({ open, onClose, onSave, initialData, isEdit, plans }) => {
  const [data, setData] = useState(initialData || EMPTY_OPTION);
  const [priceEur, setPriceEur] = useState(
    ((initialData?.price_cents || 0) / 100).toString()
  );
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setData(initialData || EMPTY_OPTION);
    setPriceEur(((initialData?.price_cents || 0) / 100).toString());
  }, [initialData]);

  if (!open) return null;

  const togglePlan = (planId) => {
    const list = data.compatible_plans || [];
    setData({
      ...data,
      compatible_plans: list.includes(planId)
        ? list.filter((p) => p !== planId)
        : [...list, planId],
    });
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload = {
        ...data,
        price_cents: Math.round(parseFloat(priceEur || 0) * 100),
      };
      await onSave(payload);
      onClose();
    } catch (e) {
      toast.error(e.message || 'Erreur lors de l\'enregistrement');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.7)' }}
      data-testid="option-form-modal"
    >
      <div
        className="rounded-2xl max-w-xl w-full max-h-[90vh] overflow-y-auto"
        style={{ background: '#0f1623', border: '1px solid rgba(217,179,90,0.3)' }}
      >
        <div className="flex items-center justify-between p-5 border-b border-white/10">
          <h2 className="text-xl font-bold text-white">
            {isEdit ? 'Modifier l\'option' : 'Nouvelle option / addon'}
          </h2>
          <button
            onClick={onClose}
            className="text-white/60 hover:text-white"
            data-testid="option-modal-close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          <div>
            <Label className="text-white/80">Nom de l'option</Label>
            <Input
              data-testid="option-name-input"
              value={data.name}
              onChange={(e) => setData({ ...data, name: e.target.value })}
              placeholder="ex. Zone supplémentaire"
              className="bg-white/5 border-white/10 text-white"
            />
          </div>

          <div>
            <Label className="text-white/80">Description</Label>
            <Textarea
              value={data.description || ''}
              onChange={(e) => setData({ ...data, description: e.target.value })}
              className="bg-white/5 border-white/10 text-white"
              rows={2}
            />
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <Label className="text-white/80">Prix (€)</Label>
              <Input
                data-testid="option-price-input"
                type="number"
                step="0.01"
                value={priceEur}
                onChange={(e) => setPriceEur(e.target.value)}
                className="bg-white/5 border-white/10 text-white"
              />
            </div>
            <div>
              <Label className="text-white/80">Période</Label>
              <select
                value={data.period}
                onChange={(e) => setData({ ...data, period: e.target.value })}
                className="w-full px-3 py-2 rounded-md bg-white/5 border border-white/10 text-white"
              >
                <option value="mois">mois</option>
                <option value="an">an</option>
                <option value="unique">unique</option>
              </select>
            </div>
            <div>
              <Label className="text-white/80">Crédits inclus</Label>
              <Input
                type="number"
                value={data.credits_included}
                onChange={(e) =>
                  setData({ ...data, credits_included: parseInt(e.target.value || 0) })
                }
                className="bg-white/5 border-white/10 text-white"
              />
            </div>
          </div>

          <div>
            <Label className="text-white/80">
              Plans compatibles (vide = tous les plans)
            </Label>
            <div className="flex flex-wrap gap-2 mt-2">
              {(plans || []).map((p) => {
                const checked = (data.compatible_plans || []).includes(p.id);
                return (
                  <button
                    type="button"
                    key={p.id}
                    onClick={() => togglePlan(p.id)}
                    className="px-3 py-1.5 rounded-full text-sm transition"
                    style={{
                      background: checked ? '#D9B35A' : 'rgba(255,255,255,0.05)',
                      color: checked ? '#070A10' : 'rgba(255,255,255,0.7)',
                      border: '1px solid rgba(217,179,90,0.3)',
                    }}
                    data-testid={`option-plan-toggle-${p.slug}`}
                  >
                    {p.name}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="flex items-center gap-2 pt-2">
            <Switch
              checked={data.active}
              onCheckedChange={(v) => setData({ ...data, active: v })}
            />
            <Label className="text-white/80">Active</Label>
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 p-5 border-t border-white/10">
          <Button
            variant="ghost"
            onClick={onClose}
            className="text-white/70"
            data-testid="option-modal-cancel"
          >
            Annuler
          </Button>
          <Button
            onClick={handleSave}
            disabled={saving || !data.name}
            data-testid="option-modal-save"
            style={{ background: '#D9B35A', color: '#070A10' }}
          >
            {saving ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Save className="w-4 h-4 mr-2" />
            )}
            Enregistrer
          </Button>
        </div>
      </div>
    </div>
  );
};

const CreditAdjustModal = ({ open, onClose, onSave, user }) => {
  const [amount, setAmount] = useState('');
  const [reason, setReason] = useState('');
  const [reference, setReference] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      setAmount('');
      setReason('');
      setReference('');
    }
  }, [open]);

  if (!open || !user) return null;

  const handleSave = async () => {
    const amt = parseInt(amount);
    if (!amt || !reason) {
      toast.error('Montant et raison sont requis');
      return;
    }
    setSaving(true);
    try {
      await onSave({ amount: amt, reason, reference: reference || null });
      onClose();
    } catch (e) {
      toast.error(e.message || 'Erreur lors de l\'ajustement');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.7)' }}
      data-testid="credit-adjust-modal"
    >
      <div
        className="rounded-2xl max-w-md w-full"
        style={{ background: '#0f1623', border: '1px solid rgba(217,179,90,0.3)' }}
      >
        <div className="flex items-center justify-between p-5 border-b border-white/10">
          <h2 className="text-lg font-bold text-white">Ajuster crédits</h2>
          <button onClick={onClose} className="text-white/60 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          <div
            className="p-3 rounded-lg"
            style={{ background: 'rgba(217,179,90,0.08)' }}
          >
            <div className="text-sm text-white/70">Utilisateur</div>
            <div className="text-white font-medium">{user.email}</div>
            <div className="text-xs text-white/50">
              {user.company_name || '—'} · Solde actuel:{' '}
              <span className="text-[#D9B35A] font-bold">
                {user.credits_balance} crédits
              </span>
            </div>
          </div>

          <div>
            <Label className="text-white/80">
              Montant (positif = ajout, négatif = déduction)
            </Label>
            <Input
              data-testid="credit-amount-input"
              type="number"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="ex. 100 ou -50"
              className="bg-white/5 border-white/10 text-white"
            />
          </div>

          <div>
            <Label className="text-white/80">Raison</Label>
            <Input
              data-testid="credit-reason-input"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="ex. Bonus fidélité"
              className="bg-white/5 border-white/10 text-white"
            />
          </div>

          <div>
            <Label className="text-white/80">Référence (optionnel)</Label>
            <Input
              value={reference}
              onChange={(e) => setReference(e.target.value)}
              placeholder="ex. Facture #2025-001"
              className="bg-white/5 border-white/10 text-white"
            />
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 p-5 border-t border-white/10">
          <Button variant="ghost" onClick={onClose} className="text-white/70">
            Annuler
          </Button>
          <Button
            onClick={handleSave}
            disabled={saving}
            data-testid="credit-adjust-save"
            style={{ background: '#D9B35A', color: '#070A10' }}
          >
            {saving ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Coins className="w-4 h-4 mr-2" />
            )}
            Appliquer
          </Button>
        </div>
      </div>
    </div>
  );
};

const StatsCard = ({ icon: Icon, label, value, color = '#D9B35A' }) => (
  <div
    className="p-4 rounded-xl"
    style={{
      background: 'rgba(255,255,255,0.03)',
      border: '1px solid rgba(255,255,255,0.08)',
    }}
  >
    <div className="flex items-center gap-3">
      <div
        className="w-10 h-10 rounded-lg flex items-center justify-center"
        style={{ background: `${color}22` }}
      >
        <Icon className="w-5 h-5" style={{ color }} />
      </div>
      <div>
        <div className="text-xs text-white/60">{label}</div>
        <div className="text-2xl font-bold text-white">{value}</div>
      </div>
    </div>
  </div>
);

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
          toast.error('Accès réservé aux administrateurs');
          navigate('/dashboard');
          return;
        }
        await loadAll();
      } catch (e) {
        toast.error('Erreur de chargement');
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
      toast.success('Plan mis à jour');
    } else {
      await adminPlansAPI.createPlan(data);
      toast.success('Plan créé');
    }
    await loadAll();
  };
  const handleDeletePlan = async (plan) => {
    if (!window.confirm(`Supprimer / désactiver le plan "${plan.name}" ?`)) return;
    try {
      const force = plan.subscribers_count === 0;
      const res = await adminPlansAPI.deletePlan(plan.id, force);
      toast.success(res.message || 'Plan supprimé');
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
      toast.success('Option mise à jour');
    } else {
      await adminPlansAPI.createOption(data);
      toast.success('Option créée');
    }
    await loadAll();
  };
  const handleDeleteOption = async (opt) => {
    if (!window.confirm(`Supprimer l'option "${opt.name}" ?`)) return;
    try {
      await adminPlansAPI.deleteOption(opt.id);
      toast.success('Option supprimée');
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
    toast.success(res.message || 'Crédits ajustés');
    await handleSearchUsers();
    await adminPlansAPI.getStats().then(setStats).catch(() => {});
  };

  if (loading) {
    return (
      <div
        className="min-h-screen flex items-center justify-center"
        style={{ background: '#070A10' }}
      >
        <Loader2 className="w-10 h-10 animate-spin" style={{ color: '#D9B35A' }} />
      </div>
    );
  }

  return (
    <div style={{ background: '#070A10', minHeight: '100vh' }}>
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
              <ArrowLeft className="w-4 h-4" /> Retour Super Admin
            </button>
            <h1 className="text-3xl sm:text-4xl font-bold text-white">
              Plans, Options & Crédits
            </h1>
            <p className="text-white/60 text-sm mt-1">
              Gérez dynamiquement les tarifs, options et crédits utilisateurs
            </p>
          </div>
        </div>

        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <StatsCard
              icon={Layers}
              label="Plans actifs"
              value={`${stats.plans.active} / ${stats.plans.total}`}
            />
            <StatsCard
              icon={Settings2}
              label="Options actives"
              value={`${stats.options.active} / ${stats.options.total}`}
              color="#7AB7FF"
            />
            <StatsCard
              icon={Users}
              label="Abonnements"
              value={stats.subscriptions.active}
              color="#9CFF7A"
            />
            <StatsCard
              icon={Coins}
              label="Crédits distribués"
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
            { id: 'plans', label: "Plans d'abonnement", icon: Layers },
            { id: 'options', label: 'Options / Addons', icon: Settings2 },
            { id: 'credits', label: 'Crédits utilisateurs', icon: Coins },
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

        {/* Plans tab */}
        {activeTab === 'plans' && (
          <div data-testid="plans-tab">
            <div className="flex justify-end mb-4">
              <Button
                onClick={handleCreatePlan}
                data-testid="create-plan-btn"
                style={{ background: '#D9B35A', color: '#070A10' }}
              >
                <Plus className="w-4 h-4 mr-2" /> Nouveau plan
              </Button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {plans.map((p) => (
                <div
                  key={p.id}
                  className="rounded-2xl p-5 relative"
                  style={{
                    background: 'rgba(255,255,255,0.03)',
                    border: `1px solid ${p.popular ? '#D9B35A' : 'rgba(255,255,255,0.08)'}`,
                  }}
                  data-testid={`plan-card-${p.slug}`}
                >
                  {p.popular && (
                    <div
                      className="absolute -top-3 right-4 px-2 py-1 rounded-full text-xs font-bold flex items-center gap-1"
                      style={{ background: '#D9B35A', color: '#070A10' }}
                    >
                      <Star className="w-3 h-3" /> Populaire
                    </div>
                  )}
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="text-xs text-white/50">{p.slug}</div>
                      <h3 className="text-lg font-bold text-white">{p.name}</h3>
                    </div>
                    <div
                      className="px-2 py-0.5 rounded text-xs"
                      style={{
                        background: p.active ? 'rgba(154,255,122,0.15)' : 'rgba(255,87,87,0.15)',
                        color: p.active ? '#9CFF7A' : '#FF8787',
                      }}
                    >
                      {p.active ? 'Actif' : 'Inactif'}
                    </div>
                  </div>
                  {p.description && (
                    <p className="text-white/60 text-sm mt-1">{p.description}</p>
                  )}
                  <div className="mt-3">
                    <span className="text-3xl font-bold" style={{ color: p.color || '#D9B35A' }}>
                      {formatPrice(p.price_cents)}
                    </span>
                    <span className="text-white/60 text-sm">/ {p.period}</span>
                  </div>
                  <div className="text-xs text-white/50 mt-1">
                    {p.default_credits} crédits · {p.max_zones} zone(s) · {p.max_users} user(s)
                  </div>
                  <ul className="space-y-1 mt-3 text-sm text-white/70">
                    {(p.features || []).slice(0, 4).map((f) => (
                      <li key={`feat-${p.id || p.code}-${f}`} className="flex items-start gap-2">
                        <CheckCircle2 className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" style={{ color: '#D9B35A' }} />
                        <span>{f}</span>
                      </li>
                    ))}
                    {(p.features || []).length > 4 && (
                      <li className="text-xs text-white/40">
                        +{p.features.length - 4} autres
                      </li>
                    )}
                  </ul>
                  <div className="mt-4 flex items-center justify-between border-t border-white/10 pt-3">
                    <div className="text-xs text-white/50">
                      {p.subscribers_count} abonné(s)
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleEditPlan(p)}
                        data-testid={`edit-plan-${p.slug}`}
                        className="p-2 rounded hover:bg-white/10"
                        title="Modifier"
                      >
                        <Pencil className="w-4 h-4 text-white/70" />
                      </button>
                      <button
                        onClick={() => handleDeletePlan(p)}
                        data-testid={`delete-plan-${p.slug}`}
                        className="p-2 rounded hover:bg-white/10"
                        title="Supprimer"
                      >
                        <Trash2 className="w-4 h-4 text-red-400" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
              {plans.length === 0 && (
                <div className="col-span-full text-center text-white/50 py-12">
                  Aucun plan créé. Cliquez sur "Nouveau plan" pour commencer.
                </div>
              )}
            </div>
          </div>
        )}

        {/* Options tab */}
        {activeTab === 'options' && (
          <div data-testid="options-tab">
            <div className="flex justify-end mb-4">
              <Button
                onClick={handleCreateOption}
                data-testid="create-option-btn"
                style={{ background: '#D9B35A', color: '#070A10' }}
              >
                <Plus className="w-4 h-4 mr-2" /> Nouvelle option
              </Button>
            </div>
            <div
              className="rounded-xl overflow-hidden"
              style={{
                background: 'rgba(255,255,255,0.03)',
                border: '1px solid rgba(255,255,255,0.08)',
              }}
            >
              <table className="w-full text-sm">
                <thead style={{ background: 'rgba(255,255,255,0.05)' }}>
                  <tr className="text-left text-white/60">
                    <th className="p-3">Nom</th>
                    <th className="p-3">Prix</th>
                    <th className="p-3">Crédits inclus</th>
                    <th className="p-3">Plans compatibles</th>
                    <th className="p-3">Statut</th>
                    <th className="p-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {options.map((o) => (
                    <tr
                      key={o.id}
                      className="border-t border-white/5 text-white/80"
                      data-testid={`option-row-${o.id}`}
                    >
                      <td className="p-3">
                        <div className="font-medium text-white">{o.name}</div>
                        {o.description && (
                          <div className="text-xs text-white/50">{o.description}</div>
                        )}
                      </td>
                      <td className="p-3">
                        {formatPrice(o.price_cents)} <span className="text-white/40">/ {o.period}</span>
                      </td>
                      <td className="p-3">{o.credits_included}</td>
                      <td className="p-3 text-xs">
                        {(o.compatible_plans || []).length === 0
                          ? 'Tous les plans'
                          : o.compatible_plans.join(', ')}
                      </td>
                      <td className="p-3">
                        {o.active ? (
                          <span className="text-[#9CFF7A] flex items-center gap-1">
                            <CheckCircle2 className="w-3.5 h-3.5" /> Active
                          </span>
                        ) : (
                          <span className="text-red-400 flex items-center gap-1">
                            <XCircle className="w-3.5 h-3.5" /> Inactive
                          </span>
                        )}
                      </td>
                      <td className="p-3 text-right">
                        <button
                          onClick={() => handleEditOption(o)}
                          data-testid={`edit-option-${o.id}`}
                          className="p-2 rounded hover:bg-white/10 inline-flex"
                        >
                          <Pencil className="w-4 h-4 text-white/70" />
                        </button>
                        <button
                          onClick={() => handleDeleteOption(o)}
                          data-testid={`delete-option-${o.id}`}
                          className="p-2 rounded hover:bg-white/10 inline-flex"
                        >
                          <Trash2 className="w-4 h-4 text-red-400" />
                        </button>
                      </td>
                    </tr>
                  ))}
                  {options.length === 0 && (
                    <tr>
                      <td colSpan={6} className="p-8 text-center text-white/50">
                        Aucune option créée
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Credits tab */}
        {activeTab === 'credits' && (
          <div data-testid="credits-tab">
            <div className="flex gap-2 mb-4">
              <div className="relative flex-1 max-w-md">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
                <Input
                  value={creditSearch}
                  onChange={(e) => setCreditSearch(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearchUsers()}
                  placeholder="Rechercher par email, nom, société..."
                  className="pl-9 bg-white/5 border-white/10 text-white"
                  data-testid="credit-search-input"
                />
              </div>
              <Button
                onClick={handleSearchUsers}
                data-testid="credit-search-btn"
                style={{ background: '#D9B35A', color: '#070A10' }}
              >
                Rechercher
              </Button>
            </div>

            <div
              className="rounded-xl overflow-hidden"
              style={{
                background: 'rgba(255,255,255,0.03)',
                border: '1px solid rgba(255,255,255,0.08)',
              }}
            >
              <table className="w-full text-sm">
                <thead style={{ background: 'rgba(255,255,255,0.05)' }}>
                  <tr className="text-left text-white/60">
                    <th className="p-3">Utilisateur</th>
                    <th className="p-3">Société</th>
                    <th className="p-3">Rôle</th>
                    <th className="p-3">Solde crédits</th>
                    <th className="p-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.users.map((u) => (
                    <tr
                      key={u.user_id}
                      className="border-t border-white/5 text-white/80"
                      data-testid={`user-credit-row-${u.user_id}`}
                    >
                      <td className="p-3">
                        <div className="text-white">{u.email}</div>
                        <div className="text-xs text-white/50">
                          {u.first_name || ''} {u.last_name || ''}
                        </div>
                      </td>
                      <td className="p-3">{u.company_name || '—'}</td>
                      <td className="p-3">
                        <span
                          className="px-2 py-0.5 rounded text-xs"
                          style={{
                            background: 'rgba(217,179,90,0.15)',
                            color: '#D9B35A',
                          }}
                        >
                          {u.role || 'buyer'}
                        </span>
                      </td>
                      <td className="p-3">
                        <span
                          className="text-lg font-bold"
                          style={{ color: '#D9B35A' }}
                        >
                          {u.credits_balance}
                        </span>{' '}
                        <span className="text-xs text-white/40">crédits</span>
                      </td>
                      <td className="p-3 text-right">
                        <Button
                          onClick={() => handleOpenAdjust(u)}
                          data-testid={`adjust-credits-${u.user_id}`}
                          size="sm"
                          variant="outline"
                          className="bg-white/5 border-white/10 text-white hover:bg-white/10"
                        >
                          <Coins className="w-3.5 h-3.5 mr-1" /> Ajuster
                        </Button>
                      </td>
                    </tr>
                  ))}
                  {users.users.length === 0 && (
                    <tr>
                      <td colSpan={5} className="p-8 text-center text-white/50">
                        Aucun utilisateur trouvé
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            <div className="text-xs text-white/40 mt-2">
              Total: {users.total} utilisateur(s)
            </div>
          </div>
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
