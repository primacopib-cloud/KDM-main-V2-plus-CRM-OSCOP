import i18n from '@/i18n';
import React from 'react';
import { Trash2, Check } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../ui/select';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription,
} from '../ui/dialog';
import { Textarea } from '../ui/textarea';
import { COLOR_OPTIONS } from './shoppingListConstants';

export const ShoppingListDialogs = ({
  showCreateDialog, setShowCreateDialog, showEditDialog, setShowEditDialog,
  formData, setFormData, handleCreate, handleUpdate, handleDelete,
  showDeleteConfirm, setShowDeleteConfirm,
}) => {
  const colorOptions = COLOR_OPTIONS;
  return (
  <>
      {/* Create Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="bg-[#0A0E17] border-white/10 text-white">
          <DialogHeader>
            <DialogTitle>{i18n.t('lists.nouvelle_liste_d_achats')}</DialogTitle>
            <DialogDescription className="text-white/60">
              Créez une liste pour organiser vos commandes récurrentes
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label>{i18n.t('lists.nom_de_la_liste')}</Label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Ex: Commande mensuelle"
                className="bg-white/[0.04] border-white/10"
                data-testid="list-name-input"
              />
            </div>
            <div>
              <Label>{i18n.t('lists.description')}</Label>
              <Input
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Ex: Produits de base pour la cuisine"
                className="bg-white/[0.04] border-white/10"
              />
            </div>
            <div>
              <Label>{i18n.t('lists.frequence')}</Label>
              <Select 
                value={formData.frequency} 
                onValueChange={(v) => setFormData({ ...formData, frequency: v })}
              >
                <SelectTrigger className="bg-white/[0.04] border-white/10">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="weekly">{i18n.t('lists.hebdomadaire')}</SelectItem>
                  <SelectItem value="biweekly">{i18n.t('lists.bi_mensuel')}</SelectItem>
                  <SelectItem value="monthly">{i18n.t('lists.mensuel')}</SelectItem>
                  <SelectItem value="quarterly">{i18n.t('lists.trimestriel')}</SelectItem>
                  <SelectItem value="one_time">{i18n.t('lists.ponctuel')}</SelectItem>
                  <SelectItem value="custom">{i18n.t('lists.personnalise')}</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>{i18n.t('lists.couleur')}</Label>
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
            <DialogTitle>{i18n.t('lists.modifier_la_liste')}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label>{i18n.t('lists.nom_de_la_liste')}</Label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="bg-white/[0.04] border-white/10"
              />
            </div>
            <div>
              <Label>{i18n.t('lists.description')}</Label>
              <Input
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="bg-white/[0.04] border-white/10"
              />
            </div>
            <div>
              <Label>{i18n.t('lists.frequence')}</Label>
              <Select 
                value={formData.frequency} 
                onValueChange={(v) => setFormData({ ...formData, frequency: v })}
              >
                <SelectTrigger className="bg-white/[0.04] border-white/10">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="weekly">{i18n.t('lists.hebdomadaire')}</SelectItem>
                  <SelectItem value="biweekly">{i18n.t('lists.bi_mensuel')}</SelectItem>
                  <SelectItem value="monthly">{i18n.t('lists.mensuel')}</SelectItem>
                  <SelectItem value="quarterly">{i18n.t('lists.trimestriel')}</SelectItem>
                  <SelectItem value="one_time">{i18n.t('lists.ponctuel')}</SelectItem>
                  <SelectItem value="custom">{i18n.t('lists.personnalise')}</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>{i18n.t('lists.couleur')}</Label>
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
            <DialogTitle>{i18n.t('lists.supprimer_la_liste')}</DialogTitle>
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
  </>
  );
};
