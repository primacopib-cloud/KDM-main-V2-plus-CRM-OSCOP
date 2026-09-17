import { useState } from 'react';
import { toast } from 'sonner';
import { detaillantAPI } from '../../services/api.detaillant';
import { COUNTRIES } from './detaillantI18n';

const inputCls = 'w-full h-9 px-2.5 rounded-lg bg-white/[0.05] border border-white/15 text-white text-xs';

export const DetaillantProfileCard = ({ t, profile, onSaved }) => {
  const [f, setF] = useState({
    company_name: profile.company_name || '', locality: profile.locality || '',
    country_code: profile.country_code || 'GP', phone_prefix: profile.phone_prefix || '+590',
    phone: profile.phone || '', contact_email: profile.contact_email || '',
    address: profile.address || '', pickup_slots: (profile.pickup_slots || []).join('\n'),
  });
  const [saving, setSaving] = useState(false);
  const set = (k) => (e) => setF((p) => ({ ...p, [k]: e.target.value }));
  const save = async () => {
    setSaving(true);
    try {
      await detaillantAPI.updateProfile({
        ...f,
        pickup_slots: f.pickup_slots.split('\n').map((s) => s.trim()).filter(Boolean),
      });
      toast.success('✓');
      onSaved?.();
    } catch (e) { toast.error(e.message); } finally { setSaving(false); }
  };
  const country = COUNTRIES.find((c) => c.code === f.country_code);
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 space-y-3" data-testid="detaillant-profile-card">
      <h3 className="text-sm font-bold text-[#E9CF8E]">{t.company}</h3>
      <div className="grid sm:grid-cols-2 gap-3">
        <div>
          <label className="text-[10px] text-white/50 block mb-1">{t.company}</label>
          <input value={f.company_name} onChange={set('company_name')} className={inputCls} data-testid="dt-company" />
        </div>
        <div>
          <label className="text-[10px] text-white/50 block mb-1">{t.locality}</label>
          <input value={f.locality} onChange={set('locality')} className={inputCls} data-testid="dt-locality" />
        </div>
        <div>
          <label className="text-[10px] text-white/50 block mb-1">{t.country} {country?.flag}</label>
          <select value={f.country_code} onChange={set('country_code')} className={inputCls} data-testid="dt-country">
            {COUNTRIES.map((c) => <option key={c.code} value={c.code}>{c.flag} {c.name}</option>)}
          </select>
        </div>
        <div>
          <label className="text-[10px] text-white/50 block mb-1">{t.phone}</label>
          <div className="flex gap-2">
            <input value={f.phone_prefix} onChange={set('phone_prefix')} className="w-20 h-9 px-2 rounded-lg bg-white/[0.05] border border-white/15 text-white text-xs" data-testid="dt-prefix" placeholder="+590" />
            <input value={f.phone} onChange={set('phone')} className={inputCls} data-testid="dt-phone" placeholder="690 00 00 00" />
          </div>
        </div>
        <div>
          <label className="text-[10px] text-white/50 block mb-1">{t.email}</label>
          <input value={f.contact_email} onChange={set('contact_email')} className={inputCls} data-testid="dt-email" />
        </div>
        <div>
          <label className="text-[10px] text-white/50 block mb-1">{t.address}</label>
          <input value={f.address} onChange={set('address')} className={inputCls} data-testid="dt-address" />
        </div>
      </div>
      <div>
        <label className="text-[10px] text-white/50 block mb-1">{t.slots} (1 / ligne — ex. Lun-Ven 9h-17h)</label>
        <textarea value={f.pickup_slots} onChange={set('pickup_slots')} rows={2}
          className="w-full px-2.5 py-2 rounded-lg bg-white/[0.05] border border-white/15 text-white text-xs" data-testid="dt-slots" />
      </div>
      <button onClick={save} disabled={saving} data-testid="dt-save-profile"
        className="h-9 px-5 rounded-full bg-[#D9B35A] text-black text-xs font-bold hover:bg-[#E9CF8E] disabled:opacity-50">
        {t.save}
      </button>
    </div>
  );
};
