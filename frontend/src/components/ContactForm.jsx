import React, { useState } from 'react';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Textarea } from './ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { subscriptionPlans } from '../data/mock';
import { Send, CheckCircle2, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { quoteAPI } from '../services/api';

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
      toast.success('Demande envoyée avec succès !');
      
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
      toast.error(error.message || 'Erreur lors de l\'envoi');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isSubmitted) {
    return (
      <div className="glass-panel rounded-[22px] p-12 text-center">
        <div className="w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-6" style={{ background: 'rgba(87,209,154,0.15)', border: '1px solid rgba(87,209,154,0.30)' }}>
          <CheckCircle2 className="w-10 h-10 text-[#57D19A]" />
        </div>
        <h3 className="text-2xl font-bold mb-4">Demande envoyée !</h3>
        <p className="text-white/70">
          Nous avons bien reçu votre demande de devis. Notre équipe vous contactera dans les plus brefs délais.
        </p>
      </div>
    );
  }

  return (
    <div className="glass-panel rounded-[22px] p-6">
      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="grid md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="company" className="text-white/80 text-sm">Nom de l&apos;entreprise *</Label>
            <Input
              id="company"
              name="company"
              value={formData.company}
              onChange={handleChange}
              placeholder="SARL / SAS / SCOP..."
              required
              className="h-12 bg-white/[0.04] border-white/10 text-white placeholder:text-white/40 rounded-xl focus:border-[#D9B35A]/50 focus:ring-[#D9B35A]/20"
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="contactName" className="text-white/80 text-sm">Nom du contact *</Label>
            <Input
              id="contactName"
              name="contactName"
              value={formData.contactName}
              onChange={handleChange}
              placeholder="Prénom Nom"
              required
              className="h-12 bg-white/[0.04] border-white/10 text-white placeholder:text-white/40 rounded-xl focus:border-[#D9B35A]/50 focus:ring-[#D9B35A]/20"
            />
          </div>
        </div>

        <div className="grid md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="email" className="text-white/80 text-sm">Email professionnel *</Label>
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
            <Label htmlFor="phone" className="text-white/80 text-sm">Téléphone *</Label>
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
          <Label htmlFor="plan" className="text-white/80 text-sm">Offre intéressée</Label>
          <Select value={formData.plan} onValueChange={handlePlanChange}>
            <SelectTrigger className="h-12 bg-white/[0.04] border-white/10 text-white rounded-xl focus:border-[#D9B35A]/50 focus:ring-[#D9B35A]/20">
              <SelectValue placeholder="Sélectionnez une offre" />
            </SelectTrigger>
            <SelectContent className="bg-[#0d1117] border-white/10">
              {subscriptionPlans.map((plan) => (
                <SelectItem key={plan.id} value={plan.id} className="text-white/80 focus:bg-white/10 focus:text-white">
                  {plan.name} - {plan.price}€ HT/{plan.period}
                </SelectItem>
              ))}
              <SelectItem value="undecided" className="text-white/80 focus:bg-white/10 focus:text-white">Je ne sais pas encore</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="message" className="text-white/80 text-sm">Message / Besoins spécifiques</Label>
          <Textarea
            id="message"
            name="message"
            value={formData.message}
            onChange={handleChange}
            placeholder="Décrivez votre activité, vos besoins, vos questions..."
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
              Envoi en cours...
            </>
          ) : (
            <>
              <Send className="w-5 h-5" />
              Envoyer ma demande de devis
            </>
          )}
        </button>

        <p className="text-xs text-white/50 text-center">
          En soumettant ce formulaire, vous acceptez d&apos;être contacté par notre équipe commerciale.
        </p>
      </form>
    </div>
  );
};

export default ContactForm;
