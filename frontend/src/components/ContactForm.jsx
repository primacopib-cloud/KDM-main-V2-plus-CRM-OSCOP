import React, { useState } from 'react';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Textarea } from './ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { subscriptionPlans } from '../data/mock';
import { Send, CheckCircle2, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { quoteAPI } from '../services/api';
import i18n from '@/i18n';

const ContactForm = () => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [formData, setFormData] = useState({
    company: '',
    contactName: '',
    email: '',
    phone: '',
    plan: '',
    message: ''
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handlePlanChange = (value) => {
    setFormData(prev => ({ ...prev, plan: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    
    try {
      await quoteAPI.create(formData);
      setIsSubmitted(true);
      toast.success(i18n.t('contact.toast_success'));
      
      // Reset after 3 seconds
      setTimeout(() => {
        setIsSubmitted(false);
        setFormData({
          company: '',
          contactName: '',
          email: '',
          phone: '',
          plan: '',
          message: ''
        });
      }, 3000);
    } catch (error) {
      toast.error(error.message || i18n.t('contact.toast_error'));
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isSubmitted) {
    return (
      <div className="glass-panel rounded-[22px] p-12 text-center">
        <div className="w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-6" style={{ background: 'rgba(212,175,55,0.15)', border: '1px solid rgba(212,175,55,0.30)' }}>
          <CheckCircle2 className="w-10 h-10 text-[#D4AF37]" />
        </div>
        <h3 className="text-2xl font-bold mb-4">{i18n.t('contact.sent_title')}</h3>
        <p className="text-white/70">
          {i18n.t('contact.sent_desc')}
        </p>
      </div>
    );
  }

  return (
    <div className="glass-panel rounded-[22px] p-6">
      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="grid md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="company" className="text-white/80 text-sm">{i18n.t('contact.company_label')}</Label>
            <Input
              id="company"
              name="company"
              value={formData.company}
              onChange={handleChange}
              placeholder={i18n.t('contact.company_placeholder')}
              required
              className="h-12 bg-white/[0.04] border-white/10 text-white placeholder:text-white/40 rounded-xl focus:border-[#D9B35A]/50 focus:ring-[#D9B35A]/20"
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="contactName" className="text-white/80 text-sm">{i18n.t('contact.contact_label')}</Label>
            <Input
              id="contactName"
              name="contactName"
              value={formData.contactName}
              onChange={handleChange}
              placeholder={i18n.t('contact.contact_placeholder')}
              required
              className="h-12 bg-white/[0.04] border-white/10 text-white placeholder:text-white/40 rounded-xl focus:border-[#D9B35A]/50 focus:ring-[#D9B35A]/20"
            />
          </div>
        </div>

        <div className="grid md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="email" className="text-white/80 text-sm">{i18n.t('contact.email_label')}</Label>
            <Input
              id="email"
              name="email"
              type="email"
              value={formData.email}
              onChange={handleChange}
              placeholder="contact@entreprise.fr"
              required
              className="h-12 bg-white/[0.04] border-white/10 text-white placeholder:text-white/40 rounded-xl focus:border-[#D9B35A]/50 focus:ring-[#D9B35A]/20"
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="phone" className="text-white/80 text-sm">{i18n.t('contact.phone_label')}</Label>
            <Input
              id="phone"
              name="phone"
              type="tel"
              value={formData.phone}
              onChange={handleChange}
              placeholder="06 00 00 00 00"
              required
              className="h-12 bg-white/[0.04] border-white/10 text-white placeholder:text-white/40 rounded-xl focus:border-[#D9B35A]/50 focus:ring-[#D9B35A]/20"
            />
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="plan" className="text-white/80 text-sm">{i18n.t('contact.plan_label')}</Label>
          <Select value={formData.plan} onValueChange={handlePlanChange}>
            <SelectTrigger className="h-12 bg-white/[0.04] border-white/10 text-white rounded-xl focus:border-[#D9B35A]/50 focus:ring-[#D9B35A]/20">
              <SelectValue placeholder={i18n.t('contact.select_offer')} />
            </SelectTrigger>
            <SelectContent className="bg-[#0d1117] border-white/10">
              {subscriptionPlans.map((plan) => (
                <SelectItem key={plan.id} value={plan.id} className="text-white/80 focus:bg-white/10 focus:text-white">
                  {plan.name} - {plan.price}€ HT/{i18n.t('common.month')}
                </SelectItem>
              ))}
              <SelectItem value="undecided" className="text-white/80 focus:bg-white/10 focus:text-white">{i18n.t('contact.undecided')}</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="message" className="text-white/80 text-sm">{i18n.t('contact.message_label')}</Label>
          <Textarea
            id="message"
            name="message"
            value={formData.message}
            onChange={handleChange}
            placeholder={i18n.t('contact.message_placeholder')}
            rows={4}
            className="resize-none bg-white/[0.04] border-white/10 text-white placeholder:text-white/40 rounded-xl focus:border-[#D9B35A]/50 focus:ring-[#D9B35A]/20"
          />
        </div>

        <button 
          type="submit" 
          disabled={isSubmitting}
          className="btn-gold w-full h-14 inline-flex items-center justify-center gap-2.5 rounded-[14px] text-base font-semibold disabled:opacity-50"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              {i18n.t('contact.sending')}
            </>
          ) : (
            <>
              <Send className="w-5 h-5" />
              {i18n.t('contact.send')}
            </>
          )}
        </button>

        <p className="text-xs text-white/50 text-center">
          {i18n.t('contact.disclaimer')}
        </p>
      </form>
    </div>
  );
};

export default ContactForm;
