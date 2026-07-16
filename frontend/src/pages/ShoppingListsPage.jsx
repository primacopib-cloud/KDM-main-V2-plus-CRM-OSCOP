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

// Icon mapping for frequencies
const frequencyIcons = {
  weekly: Calendar,
  biweekly: Calendar,
  monthly: CalendarDays,
  quarterly: CalendarRange,
  one_time: CalendarCheck,
  custom: Settings,
};

const frequencyLabels = {
  weekly: 'Hebdomadaire',
  biweekly: 'Bi-mensuel',
  monthly: 'Mensuel',
  quarterly: 'Trimestriel',
  one_time: 'Ponctuel',
  custom: 'Personnalisé',
};

const frequencyColors = {
  weekly: '#D4AF37',
  biweekly: '#3B82F6',
  monthly: '#8B5CF6',
  quarterly: '#F59E0B',
  one_time: '#6B7280',
  custom: '#D9B35A',
};

function formatPrice(cents) {
  if (!cents) return '—';
  return new Intl.NumberFormat('fr-FR', {
    style: 'currency',
    currency: 'EUR'
  }).format(cents / 100);
}

function formatDate(dateStr) {
  if (!dateStr) return 'Jamais';
  const date = new Date(dateStr);
  return date.toLocaleDateString('fr-FR', {
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
        toast.success('Liste créée !', { icon: '📋' });
      } else {
        const err = await res.json();
        toast.error(err.detail || 'Erreur lors de la création');
      }
    } catch (error) {
      console.error('Error creating list:', error);
      toast.error('Erreur lors de la création');
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
        toast.success('Liste mise à jour');
      }
    } catch (error) {
      console.error('Error updating list:', error);
      toast.error('Erreur lors de la mise à jour');
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
        toast.info('Liste supprimée');
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
        toast.success('Liste dupliquée !', { icon: '📋' });
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
        toast.success(`${data.items_count} produit(s) prêts à être ajoutés au panier`, {
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

  const colorOptions = [
    { value: '#D9B35A', label: 'Or' },
    { value: '#D4AF37', label: 'Vert' },
    { value: '#3B82F6', label: 'Bleu' },
    { value: '#8B5CF6', label: 'Violet' },
    { value: '#EC4899', label: 'Rose' },
    { value: '#F59E0B', label: 'Orange' },
  ];

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
                Mes Listes d'Achats
              </h1>
              <p className="text-white/60">
                Organisez vos commandes récurrentes
              </p>
            </div>
            <Button
              onClick={() => setShowCreateDialog(true)}
              className="bg-[#D9B35A] hover:bg-[#C9A34A] text-black"
              data-testid="create-list-btn"
            >
              <Plus className="w-4 h-4 mr-2" />
              Nouvelle liste
            </Button>
          </div>

          {/* Filters */}
          <div
            className="p-4 rounded-2xl mb-6"
            style={{
              background: 'linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02))',
              border: '1px solid rgba(255,255,255,0.08)'
            }}
          >
            <div className="flex flex-col lg:flex-row gap-4 items-center">
              {/* Search */}
              <div className="relative flex-1 w-full">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
                <Input
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Rechercher une liste..."
                  className="pl-10 bg-white/[0.04] border-white/10"
                  data-testid="lists-search"
                />
              </div>

              {/* Frequency Filter */}
              <Select value={filterFrequency} onValueChange={setFilterFrequency}>
                <SelectTrigger className="w-full lg:w-48 bg-white/[0.04] border-white/10">
                  <Calendar className="w-4 h-4 mr-2 text-white/40" />
                  <SelectValue placeholder="Fréquence" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Toutes fréquences</SelectItem>
                  <SelectItem value="weekly">Hebdomadaire</SelectItem>
                  <SelectItem value="biweekly">Bi-mensuel</SelectItem>
                  <SelectItem value="monthly">Mensuel</SelectItem>
                  <SelectItem value="quarterly">Trimestriel</SelectItem>
                  <SelectItem value="one_time">Ponctuel</SelectItem>
                  <SelectItem value="custom">Personnalisé</SelectItem>
                </SelectContent>
              </Select>

              {/* Sort */}
              <Select value={sortBy} onValueChange={setSortBy}>
                <SelectTrigger className="w-full lg:w-40 bg-white/[0.04] border-white/10">
                  <SelectValue placeholder="Trier par" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="created_at">Date création</SelectItem>
                  <SelectItem value="last_used_at">Dernière utilisation</SelectItem>
                  <SelectItem value="use_count">Plus utilisées</SelectItem>
                  <SelectItem value="name">Nom A-Z</SelectItem>
                </SelectContent>
              </Select>

              <Button
                variant="ghost"
                size="sm"
                onClick={() => fetchLists(true)}
                disabled={refreshing}
                className="text-white/60"
              >
                <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
              </Button>
            </div>
          </div>

          {/* Lists Grid */}
          {loading ? (
            <div className="py-20 text-center">
              <div className="w-10 h-10 border-2 border-[#D9B35A] border-t-transparent rounded-full animate-spin mx-auto mb-4" />
              <p className="text-white/50">Chargement des listes...</p>
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
              <h2 className="text-xl font-semibold mb-2">Aucune liste d'achats</h2>
              <p className="text-white/50 mb-6">
                Créez votre première liste pour organiser vos commandes récurrentes.
              </p>
              <Button
                onClick={() => setShowCreateDialog(true)}
                className="bg-[#D9B35A] hover:bg-[#C9A34A] text-black"
              >
                <Plus className="w-4 h-4 mr-2" />
                Créer ma première liste
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
                              Modifier les produits
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => openEditDialog(list)}>
                              <Settings className="w-4 h-4 mr-2" />
                              Paramètres
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => handleDuplicate(list.id)}>
                              <Copy className="w-4 h-4 mr-2" />
                              Dupliquer
                            </DropdownMenuItem>
                            <DropdownMenuSeparator className="bg-white/10" />
                            <DropdownMenuItem 
                              onClick={() => setShowDeleteConfirm(list.id)}
                              className="text-red-400 focus:text-red-400"
                            >
                              <Trash2 className="w-4 h-4 mr-2" />
                              Supprimer
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
                          <p className="text-white/40">Produits</p>
                          <p className="font-medium">{list.items_count} article{list.items_count !== 1 ? 's' : ''}</p>
                        </div>
                        <div>
                          <p className="text-white/40">Total HT</p>
                          <p className="font-medium text-[#D9B35A]">
                            {formatPrice(list.total_ht_cents)}
                          </p>
                        </div>
                        <div>
                          <p className="text-white/40">Utilisations</p>
                          <p className="font-medium">{list.use_count || 0}x</p>
                        </div>
                        <div>
                          <p className="text-white/40">Dernière utilisation</p>
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
                        Utiliser cette liste
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

      {/* Create Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="bg-[#0A0E17] border-white/10 text-white">
          <DialogHeader>
            <DialogTitle>Nouvelle liste d'achats</DialogTitle>
            <DialogDescription className="text-white/60">
              Créez une liste pour organiser vos commandes récurrentes
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label>Nom de la liste *</Label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Ex: Commande mensuelle"
                className="bg-white/[0.04] border-white/10"
                data-testid="list-name-input"
              />
            </div>
            <div>
              <Label>Description</Label>
              <Input
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Ex: Produits de base pour la cuisine"
                className="bg-white/[0.04] border-white/10"
              />
            </div>
            <div>
              <Label>Fréquence</Label>
              <Select 
                value={formData.frequency} 
                onValueChange={(v) => setFormData({ ...formData, frequency: v })}
              >
                <SelectTrigger className="bg-white/[0.04] border-white/10">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="weekly">Hebdomadaire</SelectItem>
                  <SelectItem value="biweekly">Bi-mensuel</SelectItem>
                  <SelectItem value="monthly">Mensuel</SelectItem>
                  <SelectItem value="quarterly">Trimestriel</SelectItem>
                  <SelectItem value="one_time">Ponctuel</SelectItem>
                  <SelectItem value="custom">Personnalisé</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Couleur</Label>
              <div className="flex gap-2 mt-2">
                {colorOptions.map((color) => (
                  <button
                    key={color.value}
                    onClick={() => setFormData({ ...formData, color: color.value })}
                    className={`w-8 h-8 rounded-full transition-all ${
                      formData.color === color.value 
                        ? 'ring-2 ring-white ring-offset-2 ring-offset-[#0A0E17]' 
                        : ''
                    }`}
                    style={{ backgroundColor: color.value }}
                    title={color.label}
                  />
                ))}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setShowCreateDialog(false)}>
              Annuler
            </Button>
            <Button 
              onClick={handleCreate}
              className="bg-[#D9B35A] hover:bg-[#C9A34A] text-black"
              data-testid="confirm-create-list"
            >
              <Check className="w-4 h-4 mr-2" />
              Créer la liste
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={showEditDialog} onOpenChange={setShowEditDialog}>
        <DialogContent className="bg-[#0A0E17] border-white/10 text-white">
          <DialogHeader>
            <DialogTitle>Modifier la liste</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label>Nom de la liste *</Label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="bg-white/[0.04] border-white/10"
              />
            </div>
            <div>
              <Label>Description</Label>
              <Input
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="bg-white/[0.04] border-white/10"
              />
            </div>
            <div>
              <Label>Fréquence</Label>
              <Select 
                value={formData.frequency} 
                onValueChange={(v) => setFormData({ ...formData, frequency: v })}
              >
                <SelectTrigger className="bg-white/[0.04] border-white/10">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="weekly">Hebdomadaire</SelectItem>
                  <SelectItem value="biweekly">Bi-mensuel</SelectItem>
                  <SelectItem value="monthly">Mensuel</SelectItem>
                  <SelectItem value="quarterly">Trimestriel</SelectItem>
                  <SelectItem value="one_time">Ponctuel</SelectItem>
                  <SelectItem value="custom">Personnalisé</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Couleur</Label>
              <div className="flex gap-2 mt-2">
                {colorOptions.map((color) => (
                  <button
                    key={color.value}
                    onClick={() => setFormData({ ...formData, color: color.value })}
                    className={`w-8 h-8 rounded-full transition-all ${
                      formData.color === color.value 
                        ? 'ring-2 ring-white ring-offset-2 ring-offset-[#0A0E17]' 
                        : ''
                    }`}
                    style={{ backgroundColor: color.value }}
                    title={color.label}
                  />
                ))}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setShowEditDialog(false)}>
              Annuler
            </Button>
            <Button 
              onClick={handleUpdate}
              className="bg-[#D9B35A] hover:bg-[#C9A34A] text-black"
            >
              <Check className="w-4 h-4 mr-2" />
              Enregistrer
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <Dialog open={!!showDeleteConfirm} onOpenChange={() => setShowDeleteConfirm(null)}>
        <DialogContent className="bg-[#0A0E17] border-white/10 text-white">
          <DialogHeader>
            <DialogTitle>Supprimer la liste ?</DialogTitle>
            <DialogDescription className="text-white/60">
              Cette action est irréversible. Tous les produits de cette liste seront perdus.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setShowDeleteConfirm(null)}>
              Annuler
            </Button>
            <Button 
              onClick={() => handleDelete(showDeleteConfirm)}
              className="bg-red-500 hover:bg-red-600 text-white"
            >
              <Trash2 className="w-4 h-4 mr-2" />
              Supprimer
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
