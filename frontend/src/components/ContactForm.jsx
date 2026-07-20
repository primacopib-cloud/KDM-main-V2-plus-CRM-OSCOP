import React, { useState } from 'react';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Textarea } from './ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Send, CheckCircle2, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { quoteAPI } from '../services/api';
import i18n from '@/i18n';
import { LANGS, PHONE_COUNTRIES, LEGAL_STATUSES, FORM_T } from './contactFormData';

const inputCls = 'h-12 bg-white/[0.04] border-white/10 text-white placeholder:text-white/40 rounded-xl focus:border-[#D9B35A]/50 focus:ring-[#D9B35A]/20';
const EMPTY = { company: '', legalStatus: '', firstName: '', lastName: '', email: '', phoneCountry: 'GP', phone: '', message: '' };

const ContactForm = () => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [lang, setLang] = useState(FORM_T[i18n.language] ? i18n.language : 'fr');
  const [formData, setFormData] = useState(EMPTY);
  const t = FORM_T[lang];
  const country = PHONE_COUNTRIES.find((c) => c.code === formData.phoneCountry) || PHONE_COUNTRIES[0];

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await quoteAPI.create({
        company: formData.company,
        legalStatus: formData.legalStatus,
        firstName: formData.firstName,
        lastName: formData.lastName,
        email: formData.email,
        phone: formData.phone,
        phoneCountry: country.dial,
        lang,
        message: formData.message,
      });
      setIsSubmitted(true);
      toast.success(t.toast_success);
      setTimeout(() => {
        setIsSubmitted(false);
        setFormData(EMPTY);
      }, 3000);
    } catch (error) {
      toast.error(error.message || t.toast_error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const LangSwitcher = (
    <div className="flex justify-end gap-1.5 mb-1" data-testid="quote-lang-switcher">
      {LANGS.map((l) => (
        <button key={l.code} type="button" onClick={() => setLang(l.code)} title={l.label}
          data-testid={`quote-lang-${l.code}`}
          className={`px-2.5 py-1.5 rounded-lg text-lg leading-none border transition-colors ${lang === l.code
            ? 'bg-[#D9B35A]/20 border-[#D9B35A]/60'
            : 'bg-white/[0.04] border-white/10 opacity-55 hover:opacity-100'}`}>
          {l.flag}
        </button>
      ))}
    </div>
  );

  if (isSubmitted) {
    return (
      <div className="glass-panel rounded-[22px] p-12 text-center" data-testid="quote-success">
        <div className="w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-6" style={{ background: 'rgba(212,175,55,0.15)', border: '1px solid rgba(212,175,55,0.30)' }}>
          <CheckCircle2 className="w-10 h-10 text-[#D4AF37]" />
        </div>
        <h3 className="text-2xl font-bold mb-4">{t.sent_title}</h3>
        <p className="text-white/70">{t.sent_desc}</p>
      </div>
    );
  }

  return (
    <div className="glass-panel rounded-[22px] p-6">
      {LangSwitcher}
      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="grid md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="company" className="text-white/80 text-sm">{t.company_label}</Label>
            <Input id="company" name="company" value={formData.company} onChange={handleChange}
              placeholder={t.company_placeholder} required className={inputCls} data-testid="quote-company-input" />
          </div>
          <div className="space-y-2">
            <Label className="text-white/80 text-sm">{t.legal_label}</Label>
            <Select value={formData.legalStatus} onValueChange={(v) => setFormData((p) => ({ ...p, legalStatus: v }))} required>
              <SelectTrigger className="h-12 bg-white/[0.04] border-white/10 text-white rounded-xl focus:border-[#D9B35A]/50" data-testid="quote-legal-select">
                <SelectValue placeholder={t.legal_placeholder} />
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
            <Label htmlFor="firstName" className="text-white/80 text-sm">{t.firstname_label}</Label>
            <Input id="firstName" name="firstName" value={formData.firstName} onChange={handleChange}
              placeholder={t.firstname_placeholder} required className={inputCls} data-testid="quote-firstname-input" />
          </div>
          <div className="space-y-2">
            <Label htmlFor="lastName" className="text-white/80 text-sm">{t.lastname_label}</Label>
            <Input id="lastName" name="lastName" value={formData.lastName} onChange={handleChange}
              placeholder={t.lastname_placeholder} required className={inputCls} data-testid="quote-lastname-input" />
          </div>
        </div>

        <div className="grid md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="email" className="text-white/80 text-sm">{t.email_label}</Label>
            <Input id="email" name="email" type="email" value={formData.email} onChange={handleChange}
              placeholder="contact@entreprise.fr" required className={inputCls} data-testid="quote-email-input" />
          </div>
          <div className="space-y-2">
            <Label htmlFor="phone" className="text-white/80 text-sm">{t.phone_label}</Label>
            <div className="flex gap-2">
              <Select value={formData.phoneCountry} onValueChange={(v) => setFormData((p) => ({ ...p, phoneCountry: v }))}>
                <SelectTrigger className="h-12 w-[130px] flex-shrink-0 bg-white/[0.04] border-white/10 text-white rounded-xl focus:border-[#D9B35A]/50" data-testid="quote-phone-country-select">
                  <SelectValue>
                    <span className="flex items-center gap-1.5"><span className="text-base">{country.flag}</span><span className="text-sm">{country.dial}</span></span>
                  </SelectValue>
                </SelectTrigger>
                <SelectContent className="bg-[#0d1117] border-white/10 max-h-64">
                  {PHONE_COUNTRIES.map((c) => (
                    <SelectItem key={c.code} value={c.code} className="text-white/80 focus:bg-white/10 focus:text-white">
                      <span className="flex items-center gap-2"><span className="text-base">{c.flag}</span>{c.name} <span className="text-white/45">{c.dial}</span></span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Input id="phone" name="phone" type="tel" value={formData.phone} onChange={handleChange}
                placeholder={t.phone_placeholder} required className={`${inputCls} flex-1`} data-testid="quote-phone-input" />
            </div>
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="message" className="text-white/80 text-sm">{t.message_label}</Label>
          <Textarea id="message" name="message" value={formData.message} onChange={handleChange}
            placeholder={t.message_placeholder} rows={4}
            className="resize-none bg-white/[0.04] border-white/10 text-white placeholder:text-white/40 rounded-xl focus:border-[#D9B35A]/50 focus:ring-[#D9B35A]/20"
            data-testid="quote-message-input" />
        </div>

        <button type="submit" disabled={isSubmitting} data-testid="quote-submit-btn"
          className="btn-gold w-full h-14 inline-flex items-center justify-center gap-2.5 rounded-[14px] text-base font-semibold disabled:opacity-50">
          {isSubmitting ? (<><Loader2 className="w-5 h-5 animate-spin" />{t.sending}</>) : (<><Send className="w-5 h-5" />{t.send}</>)}
        </button>

        <p className="text-xs text-white/50 text-center">{t.disclaimer}</p>
      </form>
    </div>
  );
};

export default ContactForm;
