import i18n from '@/i18n';
import React, { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  ShoppingCart, Plus, Search, Calendar, CalendarDays, CalendarRange,
  CalendarCheck, Settings, Trash2, Copy, Play, Edit2, Package,
  ArrowLeft, RefreshCw, MoreVertical, Check, X, Clock
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../components/ui/select';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription,
} from '../components/ui/dialog';
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator,
} from '../components/ui/dropdown-menu';
import NavBar from '../components/NavBar';
import Footer from '../components/Footer';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;
import {
  frequencyIcons, frequencyLabels, frequencyColors, COLOR_OPTIONS,
} from '../components/shopping-lists/shoppingListConstants';
import { ShoppingListDialogs } from '../components/shopping-lists/ShoppingListDialogs';
import { ShoppingListFilters } from '../components/shopping-lists/ShoppingListFilters';


function formatPrice(cents) {
  if (!cents) return '—';
  return new Intl.NumberFormat(i18n.language, {
    style: 'currency',
    currency: 'EUR'
  }).format(cents / 100);
}

function formatDate(dateStr) {
  if (!dateStr) return 'Jamais';
  const date = new Date(dateStr);
  return date.toLocaleDateString(i18n.language, {
    day: 'numeric',
    month: 'short',
    year: 'numeric'
  });
}

export default function ShoppingListsPage() {
  const navigate = useNavigate();
  const [lists, setLists] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterFrequency, setFilterFrequency] = useState('all');
  const [sortBy, setSortBy] = useState('created_at');
  
  // Dialog states
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [editingList, setEditingList] = useState(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(null);
  
  // Form state
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    frequency: 'custom',
    color: '#D9B35A'
  });

  const getAuthHeaders = () => {
    const token = localStorage.getItem('token');
    return {
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : ''
    };
  };

  const fetchLists = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);

    try {
      const params = new URLSearchParams({ sort_by: sortBy, sort_order: 'desc' });
      if (filterFrequency !== 'all') {
        params.append('frequency', filterFrequency);
      }

      const token = localStorage.getItem('token');
      const res = await fetch(`${API_URL}/api/shopping-lists?${params}`, {
        headers: { 'Authorization': token ? `Bearer ${token}` : '' }
      });

      if (res.ok) {
        const data = await res.json();
        setLists(data || []);
      }
    } catch (error) {
      console.error('Error fetching lists:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [sortBy, filterFrequency]);

  useEffect(() => {
    fetchLists();
  }, [fetchLists]);

  const handleCreate = async () => {
    if (!formData.name.trim()) {
      toast.error('Le nom est requis');
      return;
    }

    try {
      const res = await fetch(`${API_URL}/api/shopping-lists`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(formData)
      });

      if (res.ok) {
        const newList = await res.json();
        setLists(prev => [newList, ...prev]);
        setShowCreateDialog(false);
        setFormData({ name: '', description: '', frequency: 'custom', color: '#D9B35A' });
        toast.success(i18n.t('lists.toast_creee'), { icon: '📋' });
      } else {
        const err = await res.json();
        toast.error(err.detail || i18n.t('lists.toast_erreur_creation'));
      }
    } catch (error) {
      console.error('Error creating list:', error);
      toast.error(i18n.t('lists.toast_erreur_creation'));
    }
  };

  const handleUpdate = async () => {
    if (!editingList) return;

    try {
      const res = await fetch(`${API_URL}/api/shopping-lists/${editingList.id}`, {
        method: 'PATCH',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          name: formData.name,
          description: formData.description,
          frequency: formData.frequency,
          color: formData.color
        })
      });

      if (res.ok) {
        const updated = await res.json();
        setLists(prev => prev.map(l => l.id === updated.id ? { ...l, ...updated } : l));
        setShowEditDialog(false);
        setEditingList(null);
        toast.success(i18n.t('lists.toast_maj'));
      }
    } catch (error) {
      console.error('Error updating list:', error);
      toast.error(i18n.t('lists.toast_erreur_maj'));
    }
  };

  const handleDelete = async (listId) => {
    try {
      const res = await fetch(`${API_URL}/api/shopping-lists/${listId}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
      });

      if (res.ok) {
        setLists(prev => prev.filter(l => l.id !== listId));
        setShowDeleteConfirm(null);
        toast.info(i18n.t('lists.toast_supprimee'));
      }
    } catch (error) {
      console.error('Error deleting list:', error);
      toast.error('Erreur lors de la suppression');
    }
  };

  const handleDuplicate = async (listId) => {
    try {
      const res = await fetch(`${API_URL}/api/shopping-lists/${listId}/duplicate`, {
        method: 'POST',
        headers: getAuthHeaders()
      });

      if (res.ok) {
        const newList = await res.json();
        setLists(prev => [newList, ...prev]);
        toast.success(i18n.t('lists.toast_dupliquee'), { icon: '📋' });
      }
    } catch (error) {
      console.error('Error duplicating list:', error);
      toast.error('Erreur lors de la duplication');
    }
  };

  const handleUseList = async (list) => {
    try {
      const res = await fetch(`${API_URL}/api/shopping-lists/${list.id}/use`, {
        method: 'POST',
        headers: getAuthHeaders()
      });

      if (res.ok) {
        const data = await res.json();
        // Update the list's use count and last_used_at locally
        setLists(prev => prev.map(l => 
          l.id === list.id 
            ? { ...l, use_count: (l.use_count || 0) + 1, last_used_at: new Date().toISOString() }
            : l
        ));
        toast.success(i18n.t('lists.toast_prets', { count: data.items_count }), {
          icon: '🛒',
          action: {
            label: 'Voir le panier',
            onClick: () => navigate('/catalogue')
          }
        });
      }
    } catch (error) {
      console.error('Error using list:', error);
      toast.error('Erreur lors de l\'utilisation');
    }
  };

  const openEditDialog = (list) => {
    setEditingList(list);
    setFormData({
      name: list.name,
      description: list.description || '',
      frequency: list.frequency,
      color: list.color
    });
    setShowEditDialog(true);
  };

  // Filter lists by search
  const filteredLists = lists.filter(list => {
    if (!searchQuery.trim()) return true;
    const query = searchQuery.toLowerCase();
    return (
      list.name.toLowerCase().includes(query) ||
      list.description?.toLowerCase().includes(query)
    );
  });
  const colorOptions = COLOR_OPTIONS;
  return (
    <div className="min-h-screen bg-[#070A10] text-white">
      <NavBar />

      <main className="pt-24 pb-16">
        <div className="max-w-6xl mx-auto px-4 lg:px-6">
          {/* Header */}
          <div className="flex items-center gap-4 mb-8">
            <Link
              to="/catalogue"
              className="p-2 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div className="flex-1">
              <h1 className="text-2xl font-bold flex items-center gap-3">
                <ShoppingCart className="w-7 h-7 text-[#D9B35A]" />
                {i18n.t('lists.mes_listes_d_achats')}
              </h1>
              <p className="text-white/60">
                {i18n.t('lists.organisez_vos_commandes_recurrentes')}
              </p>
            </div>
            <Button
              onClick={() => setShowCreateDialog(true)}
              className="bg-[#D9B35A] hover:bg-[#C9A34A] text-black"
              data-testid="create-list-btn"
            >
              <Plus className="w-4 h-4 mr-2" />
              {i18n.t('lists.nouvelle_liste')}
            </Button>
          </div>

          <ShoppingListFilters
            lists={lists}
            searchQuery={searchQuery}
            setSearchQuery={setSearchQuery}
            sortBy={sortBy}
            setSortBy={setSortBy}
            refreshing={refreshing}
            fetchLists={fetchLists}
            filterFrequency={filterFrequency}
            setFilterFrequency={setFilterFrequency}
          />

          {/* Lists Grid */}
          {loading ? (
            <div className="py-20 text-center">
              <div className="w-10 h-10 border-2 border-[#D9B35A] border-t-transparent rounded-full animate-spin mx-auto mb-4" />
              <p className="text-white/50">{i18n.t('lists.chargement_des_listes')}</p>
            </div>
          ) : filteredLists.length === 0 ? (
            <div
              className="py-20 text-center rounded-2xl"
              style={{
                background: 'linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.01))',
                border: '1px solid rgba(255,255,255,0.08)'
              }}
            >
              <ShoppingCart className="w-16 h-16 text-white/20 mx-auto mb-4" />
              <h2 className="text-xl font-semibold mb-2">{i18n.t('lists.aucune_liste_d_achats')}</h2>
              <p className="text-white/50 mb-6">
                {i18n.t('lists.creez_votre_premiere_liste')}
              </p>
              <Button
                onClick={() => setShowCreateDialog(true)}
                className="bg-[#D9B35A] hover:bg-[#C9A34A] text-black"
              >
                <Plus className="w-4 h-4 mr-2" />
                {i18n.t('lists.creer_ma_premiere_liste')}
              </Button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredLists.map((list) => {
                const FreqIcon = frequencyIcons[list.frequency] || Settings;
                const freqColor = frequencyColors[list.frequency] || '#D9B35A';
                
                return (
                  <div
                    key={list.id}
                    className="group rounded-xl overflow-hidden transition-all hover:ring-1 hover:ring-white/20"
                    style={{
                      background: 'linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02))',
                      border: '1px solid rgba(255,255,255,0.08)'
                    }}
                    data-testid={`shopping-list-${list.id}`}
                  >
                    {/* Header */}
                    <div 
                      className="p-4 border-b border-white/[0.06]"
                      style={{ borderLeftWidth: 4, borderLeftColor: list.color }}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <h3 className="font-semibold truncate">{list.name}</h3>
                          {list.description && (
                            <p className="text-sm text-white/50 truncate mt-1">
                              {list.description}
                            </p>
                          )}
                        </div>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <button className="p-1 rounded hover:bg-white/10">
                              <MoreVertical className="w-4 h-4 text-white/60" />
                            </button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end" className="bg-[#0A0E17] border-white/10">
                            <DropdownMenuItem onClick={() => navigate(`/listes-achats/${list.id}`)}>
                              <Edit2 className="w-4 h-4 mr-2" />
                              {i18n.t('lists.modifier_les_produits')}
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => openEditDialog(list)}>
                              <Settings className="w-4 h-4 mr-2" />
                              {i18n.t('lists.parametres')}
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => handleDuplicate(list.id)}>
                              <Copy className="w-4 h-4 mr-2" />
                              {i18n.t('lists.dupliquer')}
                            </DropdownMenuItem>
                            <DropdownMenuSeparator className="bg-white/10" />
                            <DropdownMenuItem 
                              onClick={() => setShowDeleteConfirm(list.id)}
                              className="text-red-400 focus:text-red-400"
                            >
                              <Trash2 className="w-4 h-4 mr-2" />
                              {i18n.t('lists.supprimer')}
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </div>
                    </div>

                    {/* Body */}
                    <div className="p-4 space-y-3">
                      {/* Frequency badge */}
                      <div className="flex items-center gap-2">
                        <Badge 
                          variant="outline" 
                          className="border-white/20"
                          style={{ color: freqColor }}
                        >
                          <FreqIcon className="w-3 h-3 mr-1" />
                          {frequencyLabels[list.frequency]}
                        </Badge>
                      </div>

                      {/* Stats */}
                      <div className="grid grid-cols-2 gap-3 text-sm">
                        <div>
                          <p className="text-white/40">{i18n.t('lists.produits')}</p>
                          <p className="font-medium">{list.items_count} article{list.items_count !== 1 ? 's' : ''}</p>
                        </div>
                        <div>
                          <p className="text-white/40">{i18n.t('lists.total_ht')}</p>
                          <p className="font-medium text-[#D9B35A]">
                            {formatPrice(list.total_ht_cents)}
                          </p>
                        </div>
                        <div>
                          <p className="text-white/40">{i18n.t('lists.utilisations')}</p>
                          <p className="font-medium">{list.use_count || 0}x</p>
                        </div>
                        <div>
                          <p className="text-white/40">{i18n.t('lists.derniere_utilisation')}</p>
                          <p className="font-medium text-xs">{formatDate(list.last_used_at)}</p>
                        </div>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="p-4 pt-0">
                      <Button
                        onClick={() => handleUseList(list)}
                        className="w-full bg-[#D9B35A] hover:bg-[#C9A34A] text-black"
                        disabled={list.items_count === 0}
                        data-testid={`use-list-${list.id}`}
                      >
                        <Play className="w-4 h-4 mr-2" />
                        {i18n.t('lists.utiliser_cette_liste')}
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </main>

      <Footer />

      <ShoppingListDialogs
        showCreateDialog={showCreateDialog}
        setShowCreateDialog={setShowCreateDialog}
        showEditDialog={showEditDialog}
        setShowEditDialog={setShowEditDialog}
        formData={formData}
        setFormData={setFormData}
        handleCreate={handleCreate}
        handleUpdate={handleUpdate}
        handleDelete={handleDelete}
        showDeleteConfirm={showDeleteConfirm}
        setShowDeleteConfirm={setShowDeleteConfirm}
      />
    </div>
  );
}
