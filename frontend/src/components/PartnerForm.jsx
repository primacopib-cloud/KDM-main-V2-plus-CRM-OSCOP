import { useEffect, useState } from 'react';
import { CheckCircle2, Loader2, Send } from 'lucide-react';
import { toast } from 'sonner';
import i18n from '@/i18n';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Textarea } from './ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { LEGAL_STATUSES, PHONE_COUNTRIES } from './contactFormData';
import { Flag } from './Flag';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const inputCls = 'h-12 bg-white/[0.04] border-white/10 text-white placeholder:text-white/40 rounded-xl focus:border-[#D9B35A]/50 focus:ring-[#D9B35A]/20';
const EMPTY = { type: '', name: '', company: '', legal_status: '', email: '', phoneCountry: 'GP', phone: '', message: '' };

export const PartnerForm = () => {
  const [types, setTypes] = useState([]);
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [f, setF] = useState(EMPTY);
  const country = PHONE_COUNTRIES.find((c) => c.code === f.phoneCountry) || PHONE_COUNTRIES[0];

  useEffect(() => {
    fetch(`${API}/partners/types`)
      .then((r) => r.json())
      .then((d) => { setTypes(d.items || []); if (d.items?.length) setF((p) => ({ ...p, type: p.type || d.items[0].code })); })
      .catch(() => {});
  }, []);

  const submit = async (e) => {
    e.preventDefault();
    setSending(true);
    try {
      const lang = i18n.language?.startsWith('gcf') ? 'gcf' : (i18n.language || 'fr').slice(0, 2);
      const r = await fetch(`${API}/partners/apply`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: f.type, name: f.name, company: f.company, legal_status: f.legal_status,
          email: f.email, phone: f.phone ? `${country.dial} ${f.phone}`.trim() : '',
          message: f.message, lang,
        }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || "Erreur lors de l'envoi");
      setSent(true);
      toast.success('Candidature envoyée — nous revenons vers vous rapidement');
    } catch (err) { toast.error(err.message); } finally { setSending(false); }
  };

  if (sent) {
    return (
      <div className="glass-panel rounded-[22px] p-12 text-center" data-testid="partner-form-success">
        <div className="w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-6"
          style={{ background: 'rgba(212,175,55,0.15)', border: '1px solid rgba(212,175,55,0.30)' }}>
          <CheckCircle2 className="w-10 h-10 text-[#D4AF37]" />
        </div>
        <h3 className="text-2xl font-bold mb-4 text-white">Candidature transmise !</h3>
        <p className="text-white/70">Merci ! Votre candidature a bien été transmise à la coopérative — un accusé de réception détaillé vous a été envoyé par email.</p>
      </div>
    );
  }

  return (
    <div className="glass-panel rounded-[22px] p-6" data-testid="footer-partner-form">
      <form onSubmit={submit} className="space-y-5">
        <div className="space-y-2">
          <Label className="text-white/80 text-sm">Type de partenariat *</Label>
          <Select value={f.type} onValueChange={(v) => setF((p) => ({ ...p, type: v }))} required>
            <SelectTrigger className="h-12 bg-white/[0.04] border-white/10 text-white rounded-xl focus:border-[#D9B35A]/50" data-testid="partner-form-type">
              <SelectValue placeholder="Choisissez un type de partenariat" />
            </SelectTrigger>
            <SelectContent className="bg-[#0d1117] border-white/10 max-h-64">
              {types.map((tp) => (
                <SelectItem key={tp.code} value={tp.code} className="text-white/80 focus:bg-white/10 focus:text-white">{tp.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="grid md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="partner-company" className="text-white/80 text-sm">Raison sociale</Label>
            <Input id="partner-company" value={f.company} onChange={(e) => setF({ ...f, company: e.target.value })}
              placeholder="Nom légal de votre entreprise" className={inputCls} data-testid="partner-form-company" />
          </div>
          <div className="space-y-2">
            <Label className="text-white/80 text-sm">Statut juridique</Label>
            <Select value={f.legal_status} onValueChange={(v) => setF((p) => ({ ...p, legal_status: v }))}>
              <SelectTrigger className="h-12 bg-white/[0.04] border-white/10 text-white rounded-xl focus:border-[#D9B35A]/50" data-testid="partner-form-legal">
                <SelectValue placeholder="Sélectionnez un statut" />
              </SelectTrigger>
              <SelectContent className="bg-[#0d1117] border-white/10 max-h-64">
                {LEGAL_STATUSES.map((s) => (
                  <SelectItem key={s} value={s} className="text-white/80 focus:bg-white/10 focus:text-white">{s}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="grid md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="partner-name" className="text-white/80 text-sm">Nom complet *</Label>
            <Input id="partner-name" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })}
              placeholder="Jean Dupont" required className={inputCls} data-testid="partner-form-name" />
          </div>
          <div className="space-y-2">
            <Label htmlFor="partner-email" className="text-white/80 text-sm">Email professionnel *</Label>
            <Input id="partner-email" type="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })}
              placeholder="contact@entreprise.fr" required className={inputCls} data-testid="partner-form-email" />
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="partner-phone" className="text-white/80 text-sm">Téléphone</Label>
          <div className="flex gap-2">
            <Select value={f.phoneCountry} onValueChange={(v) => setF((p) => ({ ...p, phoneCountry: v }))}>
              <SelectTrigger className="h-12 w-[130px] flex-shrink-0 bg-white/[0.04] border-white/10 text-white rounded-xl focus:border-[#D9B35A]/50" data-testid="partner-form-phone-country">
                <SelectValue>
                  <span className="flex items-center gap-1.5"><Flag code={country.code} className="w-5 h-auto rounded-[2px]" /><span className="text-sm">{country.dial}</span></span>
                </SelectValue>
              </SelectTrigger>
              <SelectContent className="bg-[#0d1117] border-white/10 max-h-64">
                {PHONE_COUNTRIES.map((c) => (
                  <SelectItem key={c.code} value={c.code} className="text-white/80 focus:bg-white/10 focus:text-white">
                    <span className="flex items-center gap-2"><Flag code={c.code} className="w-5 h-auto rounded-[2px]" />{c.name} <span className="text-white/45">{c.dial}</span></span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Input id="partner-phone" type="tel" value={f.phone} onChange={(e) => setF({ ...f, phone: e.target.value })}
              placeholder="690 00 00 00" className={`${inputCls} flex-1`} data-testid="partner-form-phone" />
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="partner-message" className="text-white/80 text-sm">Votre projet</Label>
          <Textarea id="partner-message" value={f.message} onChange={(e) => setF({ ...f, message: e.target.value })}
            placeholder="Décrivez votre activité et le partenariat envisagé…" rows={4}
            className="resize-none bg-white/[0.04] border-white/10 text-white placeholder:text-white/40 rounded-xl focus:border-[#D9B35A]/50 focus:ring-[#D9B35A]/20"
            data-testid="partner-form-message" />
        </div>

        <button type="submit" disabled={sending} data-testid="partner-form-submit"
          className="btn-gold w-full h-14 inline-flex items-center justify-center gap-2.5 rounded-[14px] text-base font-semibold disabled:opacity-50">
          {sending ? (<><Loader2 className="w-5 h-5 animate-spin" />Envoi en cours…</>) : (<><Send className="w-5 h-5" />Envoyer ma candidature</>)}
        </button>

        <p className="text-xs text-white/50 text-center">Votre candidature est étudiée par la coopérative — réponse sous 48 h ouvrées.</p>
      </form>
    </div>
  );
};
