import React from 'react';
import {
  Star, Plus, X, GripVertical, Settings, Trash2, Check,
} from 'lucide-react';
import { Button } from '../ui/button';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '../ui/dialog';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { iconMap, getIcon, colorOptions } from './shortcutConstants';

export const ShortcutDialogs = ({
  showAddDialog, setShowAddDialog, isManaging, setIsManaging,
  newShortcut, setNewShortcut, shortcuts, editingShortcut, setEditingShortcut,
  handleAddShortcut, handleDeleteShortcut, handleUpdateShortcut,
}) => (
  <>
        {/* Add Dialog */}
        <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
          <DialogContent className="bg-[#0A0E17] border-white/10 text-white">
            <DialogHeader>
              <DialogTitle>Ajouter un raccourci</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div>
                <Label>Nom</Label>
                <Input
                  value={newShortcut.label}
                  onChange={(e) => setNewShortcut({ ...newShortcut, label: e.target.value })}
                  placeholder="Mon raccourci"
                  className="bg-white/[0.04] border-white/10"
                  data-testid="shortcut-label-input"
                />
              </div>
              <div>
                <Label>URL</Label>
                <Input
                  value={newShortcut.href}
                  onChange={(e) => setNewShortcut({ ...newShortcut, href: e.target.value })}
                  placeholder="/catalogue"
                  className="bg-white/[0.04] border-white/10"
                  data-testid="shortcut-href-input"
                />
              </div>
              <div>
                <Label>Couleur</Label>
                <div className="flex gap-2 mt-2">
                  {colorOptions.map((color) => (
                    <button
                      key={color.value}
                      onClick={() => setNewShortcut({ ...newShortcut, color: color.value })}
                      className={`w-8 h-8 rounded-full transition-all ${
                        newShortcut.color === color.value ? 'ring-2 ring-white ring-offset-2 ring-offset-[#0A0E17]' : ''
                      }`}
                      style={{ backgroundColor: color.value }}
                      title={color.label}
                    />
                  ))}
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button variant="ghost" onClick={() => setShowAddDialog(false)}>
                Annuler
              </Button>
              <Button 
                onClick={() => handleAddShortcut()}
                disabled={!newShortcut.label || !newShortcut.href}
                className="bg-[#D9B35A] hover:bg-[#C9A34A] text-black"
                data-testid="add-shortcut-btn"
              >
                Ajouter
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Management Dialog */}
        <Dialog open={isManaging} onOpenChange={setIsManaging}>
          <DialogContent className="bg-[#0A0E17] border-white/10 text-white max-w-md">
            <DialogHeader>
              <DialogTitle>Gérer les raccourcis</DialogTitle>
            </DialogHeader>
            <div className="space-y-2 py-4 max-h-80 overflow-y-auto">
              {shortcuts.length === 0 ? (
                <p className="text-center text-white/50 py-8">Aucun raccourci</p>
              ) : (
                shortcuts.map((shortcut) => {
                  const Icon = getIcon(shortcut.icon);
                  return (
                    <div
                      key={shortcut.id}
                      className="flex items-center gap-3 p-3 rounded-lg bg-white/[0.04] border border-white/10"
                    >
                      <GripVertical className="w-4 h-4 text-white/30 cursor-grab" />
                      <div 
                        className="w-8 h-8 rounded-lg flex items-center justify-center"
                        style={{ backgroundColor: `${shortcut.color}20` }}
                      >
                        <Icon className="w-4 h-4" style={{ color: shortcut.color }} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium truncate">{shortcut.label}</p>
                        <p className="text-xs text-white/50 truncate">{shortcut.href}</p>
                      </div>
                      <button
                        onClick={() => setEditingShortcut(shortcut)}
                        className="p-1.5 rounded hover:bg-white/[0.08] text-white/60"
                      >
                        <Settings className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleDeleteShortcut(shortcut.id)}
                        className="p-1.5 rounded hover:bg-red-500/20 text-red-400"
                        data-testid={`delete-shortcut-${shortcut.id}`}
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  );
                })
              )}
            </div>
            <DialogFooter>
              <Button variant="ghost" onClick={() => setIsManaging(false)}>
                Fermer
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Edit Dialog */}
        <Dialog open={!!editingShortcut} onOpenChange={() => setEditingShortcut(null)}>
          <DialogContent className="bg-[#0A0E17] border-white/10 text-white">
            <DialogHeader>
              <DialogTitle>Modifier le raccourci</DialogTitle>
            </DialogHeader>
            {editingShortcut && (
              <div className="space-y-4 py-4">
                <div>
                  <Label>Nom</Label>
                  <Input
                    value={editingShortcut.label}
                    onChange={(e) => setEditingShortcut({ ...editingShortcut, label: e.target.value })}
                    className="bg-white/[0.04] border-white/10"
                  />
                </div>
                <div>
                  <Label>Couleur</Label>
                  <div className="flex gap-2 mt-2">
                    {colorOptions.map((color) => (
                      <button
                        key={color.value}
                        onClick={() => setEditingShortcut({ ...editingShortcut, color: color.value })}
                        className={`w-8 h-8 rounded-full transition-all ${
                          editingShortcut.color === color.value ? 'ring-2 ring-white ring-offset-2 ring-offset-[#0A0E17]' : ''
                        }`}
                        style={{ backgroundColor: color.value }}
                        title={color.label}
                      />
                    ))}
                  </div>
                </div>
              </div>
            )}
            <DialogFooter>
              <Button variant="ghost" onClick={() => setEditingShortcut(null)}>
                Annuler
              </Button>
              <Button 
                onClick={handleUpdateShortcut}
                className="bg-[#D9B35A] hover:bg-[#C9A34A] text-black"
              >
                <Check className="w-4 h-4 mr-2" />
                Enregistrer
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
  </>
);
