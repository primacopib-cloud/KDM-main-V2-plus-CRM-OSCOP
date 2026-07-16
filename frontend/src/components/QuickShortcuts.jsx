import React, { useState, useEffect, useCallback } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  Star, Plus, X, GripVertical, Settings, Trash2,
  ShoppingCart, Package, Wallet, FileText, LayoutDashboard,
  Scale, Home, CreditCard, Building2, Store, Users, Check
} from 'lucide-react';
import { Button } from './ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from './ui/dropdown-menu';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from './ui/dialog';
import { Input } from './ui/input';
import { Label } from './ui/label';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Icon mapping
import { iconMap, getIcon, colorOptions } from './shortcuts/shortcutConstants';
import { ShortcutDialogs } from './shortcuts/ShortcutDialogs';

export default function QuickShortcuts({ variant = 'navbar' }) {
  const [shortcuts, setShortcuts] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isManaging, setIsManaging] = useState(false);
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [editingShortcut, setEditingShortcut] = useState(null);
  const [newShortcut, setNewShortcut] = useState({ label: '', href: '', icon: 'Star', color: '#D9B35A' });
  const location = useLocation();

  const getAuthHeaders = () => {
    const token = localStorage.getItem('token');
    return {
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : ''
    };
  };

  const fetchShortcuts = useCallback(async () => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_URL}/api/user-prefs/shortcuts`, {
        headers: { 'Authorization': token ? `Bearer ${token}` : '' }
      });
      if (res.ok) {
        const data = await res.json();
        setShortcuts(data.shortcuts || []);
      }
    } catch (error) {
      console.error('Error fetching shortcuts:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchSuggestions = useCallback(async () => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_URL}/api/user-prefs/shortcuts/suggestions`, {
        headers: { 'Authorization': token ? `Bearer ${token}` : '' }
      });
      if (res.ok) {
        const data = await res.json();
        setSuggestions(data.suggestions || []);
      }
    } catch (error) {
      console.error('Error fetching suggestions:', error);
    }
  }, []);

  useEffect(() => {
    fetchShortcuts();
    fetchSuggestions();
  }, [fetchShortcuts, fetchSuggestions]);

  const handleAddShortcut = async (shortcutData = newShortcut) => {
    try {
      const res = await fetch(`${API_URL}/api/user-prefs/shortcuts`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(shortcutData)
      });
      if (res.ok) {
        const data = await res.json();
        setShortcuts(prev => [...prev, data]);
        setShowAddDialog(false);
        setNewShortcut({ label: '', href: '', icon: 'Star', color: '#D9B35A' });
        fetchSuggestions(); // Refresh suggestions
      }
    } catch (error) {
      console.error('Error adding shortcut:', error);
    }
  };

  const handleUpdateShortcut = async () => {
    if (!editingShortcut) return;
    
    try {
      const res = await fetch(`${API_URL}/api/user-prefs/shortcuts/${editingShortcut.id}`, {
        method: 'PATCH',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          label: editingShortcut.label,
          icon: editingShortcut.icon,
          color: editingShortcut.color
        })
      });
      if (res.ok) {
        const data = await res.json();
        setShortcuts(prev => prev.map(s => s.id === data.id ? data : s));
        setEditingShortcut(null);
      }
    } catch (error) {
      console.error('Error updating shortcut:', error);
    }
  };

  const handleDeleteShortcut = async (id) => {
    try {
      const res = await fetch(`${API_URL}/api/user-prefs/shortcuts/${id}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
      });
      if (res.ok) {
        setShortcuts(prev => prev.filter(s => s.id !== id));
        fetchSuggestions(); // Refresh suggestions
      }
    } catch (error) {
      console.error('Error deleting shortcut:', error);
    }
  };

  const handleQuickAdd = (suggestion) => {
    handleAddShortcut(suggestion);
  };

  // Loading state
  if (loading) {
    return null;
  }

  // Navbar variant - compact display
  if (variant === 'navbar') {
    return (
      <div className="flex items-center gap-1">
        {/* Shortcuts */}
        {shortcuts.slice(0, 4).map((shortcut) => {
          const Icon = getIcon(shortcut.icon);
          const isActive = location.pathname === shortcut.href;
          return (
            <Link
              key={shortcut.id}
              to={shortcut.href}
              className={`p-2 rounded-lg transition-all ${
                isActive 
                  ? 'bg-white/[0.12]' 
                  : 'hover:bg-white/[0.06]'
              }`}
              style={{ color: isActive ? shortcut.color : 'rgba(255,255,255,0.7)' }}
              title={shortcut.label}
              data-testid={`shortcut-${shortcut.id}`}
            >
              <Icon className="w-4 h-4" />
            </Link>
          );
        })}

        {/* Dropdown for more shortcuts + management */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              className="p-2 rounded-lg hover:bg-white/[0.06] transition-colors text-white/60 hover:text-white/90"
              data-testid="shortcuts-menu-trigger"
            >
              <Star className="w-4 h-4" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent 
            align="end" 
            className="w-64 bg-[#0A0E17] border-white/10"
            style={{ backdropFilter: 'blur(20px)' }}
          >
            {/* Additional shortcuts */}
            {shortcuts.slice(4).map((shortcut) => {
              const Icon = getIcon(shortcut.icon);
              return (
                <DropdownMenuItem key={shortcut.id} asChild>
                  <Link 
                    to={shortcut.href}
                    className="flex items-center gap-2 cursor-pointer"
                  >
                    <Icon className="w-4 h-4" style={{ color: shortcut.color }} />
                    <span>{shortcut.label}</span>
                  </Link>
                </DropdownMenuItem>
              );
            })}

            {shortcuts.length > 4 && <DropdownMenuSeparator className="bg-white/10" />}

            {/* Quick add from suggestions */}
            {suggestions.length > 0 && shortcuts.length < 6 && (
              <>
                <div className="px-2 py-1.5 text-xs text-white/50">Ajouter rapidement</div>
                {suggestions.slice(0, 3).map((suggestion) => {
                  const Icon = getIcon(suggestion.icon);
                  return (
                    <DropdownMenuItem
                      key={suggestion.href}
                      onClick={() => handleQuickAdd(suggestion)}
                      className="flex items-center gap-2 cursor-pointer"
                    >
                      <Icon className="w-4 h-4" style={{ color: suggestion.color }} />
                      <span>{suggestion.label}</span>
                      <Plus className="w-3 h-3 ml-auto text-white/40" />
                    </DropdownMenuItem>
                  );
                })}
                <DropdownMenuSeparator className="bg-white/10" />
              </>
            )}

            {/* Management options */}
            <DropdownMenuItem 
              onClick={() => setShowAddDialog(true)}
              className="flex items-center gap-2 cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              <span>Ajouter un raccourci</span>
            </DropdownMenuItem>
            <DropdownMenuItem 
              onClick={() => setIsManaging(true)}
              className="flex items-center gap-2 cursor-pointer"
            >
              <Settings className="w-4 h-4" />
              <span>Gérer les raccourcis</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
        <ShortcutDialogs
          showAddDialog={showAddDialog}
          setShowAddDialog={setShowAddDialog}
          isManaging={isManaging}
          setIsManaging={setIsManaging}
          newShortcut={newShortcut}
          setNewShortcut={setNewShortcut}
          shortcuts={shortcuts}
          editingShortcut={editingShortcut}
          setEditingShortcut={setEditingShortcut}
          handleAddShortcut={handleAddShortcut}
          handleDeleteShortcut={handleDeleteShortcut}
          handleUpdateShortcut={handleUpdateShortcut}
        />
      </div>
    );
  }

  // Full panel variant for settings page
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Mes raccourcis</h3>
        <Button
          size="sm"
          onClick={() => setShowAddDialog(true)}
          disabled={shortcuts.length >= 6}
          className="bg-[#D9B35A] hover:bg-[#C9A34A] text-black"
        >
          <Plus className="w-4 h-4 mr-2" />
          Ajouter
        </Button>
      </div>
      
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {shortcuts.map((shortcut) => {
          const Icon = getIcon(shortcut.icon);
          return (
            <div
              key={shortcut.id}
              className="p-4 rounded-xl bg-white/[0.04] border border-white/10 group"
            >
              <div className="flex items-start justify-between mb-3">
                <div 
                  className="w-10 h-10 rounded-xl flex items-center justify-center"
                  style={{ backgroundColor: `${shortcut.color}20` }}
                >
                  <Icon className="w-5 h-5" style={{ color: shortcut.color }} />
                </div>
                <button
                  onClick={() => handleDeleteShortcut(shortcut.id)}
                  className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-500/20 text-red-400 transition-opacity"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
              <p className="font-medium">{shortcut.label}</p>
              <p className="text-xs text-white/50 truncate">{shortcut.href}</p>
            </div>
          );
        })}
        
        {shortcuts.length < 6 && (
          <button
            onClick={() => setShowAddDialog(true)}
            className="p-4 rounded-xl border-2 border-dashed border-white/10 hover:border-white/20 transition-colors flex flex-col items-center justify-center gap-2 text-white/50 hover:text-white/70"
          >
            <Plus className="w-6 h-6" />
            <span className="text-sm">Ajouter</span>
          </button>
        )}
      </div>
    </div>
  );
}
