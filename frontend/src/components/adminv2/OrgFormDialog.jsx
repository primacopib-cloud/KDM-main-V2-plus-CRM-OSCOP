import { useState, useEffect } from 'react';
import { toast } from 'sonner';
import { Loader2 } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '../ui/dialog';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../ui/select';
import { adminAPIV2 } from '../../services/api';

const TERRITORIES = ['GUADELOUPE', 'MARTINIQUE', 'GUYANE', 'REUNION', 'MAYOTTE', 'CARIBBEAN'];
const STATUSES = [
  ['DRAFT', 'Brouillon'], ['PENDING_REVIEW', 'En révision'], ['APPROVED', 'Approuvé'],
  ['SUSPENDED', 'Suspendu'], ['CLOSED', 'Fermé'],
];
const EMPTY = {
  legal_name: '', registration_id: '', territory: 'GUADELOUPE', member_type: 'BUYER_PRO',
  status: 'APPROVED', contact_name: '', contact_email: '', contact_phone: '', city: '',
};
const inputCls = 'mt-1 bg-white/[0.04] border-white/10 text-white text-sm';

export const OrgFormDialog = ({ open, onClose, org, onSaved }) => {
  const [form, setForm] = useState(EMPTY);
  const [saving, setSaving] = useState(false);
  const isEdit = Boolean(org);

  useEffect(() => {
    if (open) {
      setForm(org ? {
        legal_name: org.legal_name || '', registration_id: org.registration_id || '',
        territory: org.territory || 'GUADELOUPE', member_type: org.member_type || 'BUYER_PRO',
        status: org.status || 'APPROVED', contact_name: org.contact_name || '',
        contact_email: org.contact_email || '', contact_phone: org.contact_phone || '', city: org.city || '',
      } : EMPTY);
    }
  }, [open, org]);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async () => {
    if (form.legal_name.trim().length < 2) { toast.error('Raison sociale requise (2 car. min)'); return; }
    if (form.registration_id.trim().length < 9) { toast.error('SIRET requis (9 car. min)'); return; }
    setSaving(true);
    try {
      const payload = { ...form, legal_name: form.legal_name.trim(), registration_id: form.registration_id.trim() };
      if (isEdit) await adminAPIV2.updateOrg(org.id, payload);
      else await adminAPIV2.createOrg(payload);
      toast.success(isEdit ? 'Organisation mise à jour' : 'Organisation créée');
      onSaved();
      onClose();
    } catch (e) {
      toast.error(e.message);
    } finally { setSaving(false); }
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-lg bg-[#2A1045] border-white/15 text-white" data-testid="org-form-dialog">
        <DialogHeader>
          <DialogTitle>{isEdit ? `Modifier — ${org?.legal_name}` : 'Nouvelle organisation'}</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-white/70 text-xs">Raison sociale *</Label>
              <Input value={form.legal_name} onChange={(e) => set('legal_name', e.target.value)}
                data-testid="org-form-legal-name" className={inputCls} />
            </div>
            <div>
              <Label className="text-white/70 text-xs">SIRET *</Label>
              <Input value={form.registration_id} onChange={(e) => set('registration_id', e.target.value)}
                data-testid="org-form-siret" className={inputCls} />
            </div>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <Label className="text-white/70 text-xs">Territoire</Label>
              <Select value={form.territory} onValueChange={(v) => set('territory', v)}>
                <SelectTrigger className={inputCls} data-testid="org-form-territory"><SelectValue /></SelectTrigger>
                <SelectContent>{TERRITORIES.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-white/70 text-xs">Type</Label>
              <Select value={form.member_type} onValueChange={(v) => set('member_type', v)}>
                <SelectTrigger className={inputCls} data-testid="org-form-type"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="BUYER_PRO">Acheteur pro</SelectItem>
                  <SelectItem value="VENDOR_PRO">Vendeur pro</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-white/70 text-xs">Statut</Label>
              <Select value={form.status} onValueChange={(v) => set('status', v)}>
                <SelectTrigger className={inputCls} data-testid="org-form-status"><SelectValue /></SelectTrigger>
                <SelectContent>{STATUSES.map(([v, l]) => <SelectItem key={v} value={v}>{l}</SelectItem>)}</SelectContent>
              </Select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-white/70 text-xs">Contact</Label>
              <Input value={form.contact_name} onChange={(e) => set('contact_name', e.target.value)}
                data-testid="org-form-contact-name" className={inputCls} />
            </div>
            <div>
              <Label className="text-white/70 text-xs">Email contact</Label>
              <Input type="email" value={form.contact_email} onChange={(e) => set('contact_email', e.target.value)}
                data-testid="org-form-contact-email" className={inputCls} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-white/70 text-xs">Téléphone</Label>
              <Input value={form.contact_phone} onChange={(e) => set('contact_phone', e.target.value)}
                data-testid="org-form-contact-phone" className={inputCls} />
            </div>
            <div>
              <Label className="text-white/70 text-xs">Ville</Label>
              <Input value={form.city} onChange={(e) => set('city', e.target.value)}
                data-testid="org-form-city" className={inputCls} />
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={onClose} className="text-white/60">Annuler</Button>
          <Button onClick={submit} disabled={saving} data-testid="org-form-submit"
            className="bg-[#D9B35A] text-black hover:bg-[#c5a04b] font-semibold">
            {saving && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
            {isEdit ? 'Enregistrer' : 'Créer'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
