import { useState } from 'react';
import { LifeBuoy, Send, Loader2, CheckCircle2, Mail, HelpCircle } from 'lucide-react';
import { toast } from 'sonner';
import Header from '../components/Header';
import Footer from '../components/Footer';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '../components/ui/accordion';
import { apiCall } from '../services/http';
import { MySupportTickets } from '../components/support/MySupportTickets';

const CATEGORIES = [
  { value: 'GENERAL', label: 'Question générale' },
  { value: 'COMPTE', label: 'Compte & connexion' },
  { value: 'COMMANDE', label: 'Commandes & livraison' },
  { value: 'PAIEMENT', label: 'Paiement & facturation' },
  { value: 'CREDISCOP', label: "CREDI'SCOP & crédits" },
  { value: 'TECHNIQUE', label: 'Problème technique' },
];

const FAQ_ITEMS = [
  {
    q: 'Comment devenir membre Acheteur pro ou Vendeur pro ?',
    a: "Créez votre compte puis complétez le formulaire d'adhésion B2B avec votre SIRET, votre territoire et votre statut (Acheteur pro ou Vendeur pro). Après validation par nos équipes, vous êtes automatiquement inscrit au registre des membres et recevez 100 crédits de bienvenue.",
  },
  {
    q: 'Comment acheter des crédits CREDI\'SCOP ?',
    a: "Les crédits sont payables exclusivement par carte bancaire via Stripe. Cliquez sur le badge CREDI'SCOP dans la barre de navigation ou sur le bouton « + » de votre espace, choisissez un pack et réglez en toute sécurité.",
  },
  {
    q: 'Comment fonctionnent les commandes groupées et la livraison ?',
    a: "Les commandes passent par le catalogue B2B mutualisé de votre territoire. Les prix sont négociés collectivement (EXW). Vous êtes prévenu automatiquement si un prix change ou si un produit devient indisponible dans votre panier.",
  },
  {
    q: 'Puis-je payer ma commande en plusieurs fois ?',
    a: "Oui, le paiement en 4 fois est disponible par carte bancaire pour les paniers dépassant le montant minimum affiché au moment du règlement.",
  },
  {
    q: 'Comment diffuser un spot vidéo pour mes produits ?',
    a: "En tant que Vendeur pro, l'AI Studio vous permet de générer des spots vidéo multilingues (FR/EN/ES). Vous pouvez ensuite réserver un créneau dans la grille de diffusion, payable en crédits coopératifs (CC).",
  },
  {
    q: 'Sous quel délai vais-je recevoir une réponse du support ?',
    a: "Notre équipe coopérative répond sous 24h ouvrées. Vous recevez un email de confirmation avec un numéro de suivi, une notification dès qu'une réponse est disponible, et vous pouvez relancer un ticket fermé si besoin.",
  },
];

const storedUser = () => {
  try { return JSON.parse(localStorage.getItem('user')) || {}; } catch { return {}; }
};

export default function SupportContactPage() {
  const u = storedUser();
  const [form, setForm] = useState({
    name: u.contact_name || '', email: u.email || '',
    subject: '', category: 'GENERAL', message: '',
  });
  const [sending, setSending] = useState(false);
  const [sentTicket, setSentTicket] = useState(null);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSending(true);
    try {
      const res = await apiCall('/support/contact', { method: 'POST', body: JSON.stringify(form) });
      setSentTicket(res.ticket_number);
      toast.success('Message envoyé ! Un email de confirmation vous a été adressé.');
    } catch (err) {
      toast.error(err.message || "Erreur lors de l'envoi");
    } finally {
      setSending(false);
    }
  };

  const inputCls = 'w-full h-11 px-4 rounded-xl bg-white/[0.04] border border-white/10 text-sm focus:outline-none focus:border-[#D9B35A]/60';

  return (
    <div className="min-h-screen" data-testid="support-contact-page">
      <Header />
      <main className="pt-24 pb-16 max-w-[680px] mx-auto px-5">
        <div className="text-center mb-8">
          <div className="w-14 h-14 mx-auto mb-4 rounded-2xl flex items-center justify-center"
            style={{ background: 'rgba(217,179,90,0.14)', border: '1px solid rgba(217,179,90,0.45)' }}>
            <LifeBuoy className="w-7 h-7 text-[#D9B35A]" />
          </div>
          <h1 className="font-display text-4xl sm:text-5xl lg:text-6xl tracking-tight mb-3">Contacter le support</h1>
          <p className="text-white/60 text-base">
            Notre équipe coopérative vous répond sous 24h ouvrées.
          </p>
        </div>

        <div className="mb-10" data-testid="support-faq">
          <h2 className="text-base md:text-lg font-semibold mb-3 flex items-center gap-2">
            <HelpCircle className="w-5 h-5 text-[#D9B35A]" /> Questions fréquentes
          </h2>
          <Accordion type="single" collapsible className="glass-panel-soft rounded-[20px] px-5">
            {FAQ_ITEMS.map((item, i) => (
              <AccordionItem key={`faq-${i}`} value={`faq-${i}`} className="border-white/10">
                <AccordionTrigger className="text-sm text-left hover:no-underline" data-testid={`faq-trigger-${i}`}>
                  {item.q}
                </AccordionTrigger>
                <AccordionContent className="text-sm text-white/65">{item.a}</AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
          <p className="text-xs text-white/40 mt-3 text-center">Vous n'avez pas trouvé votre réponse ? Envoyez-nous un message ci-dessous.</p>
        </div>

        {sentTicket ? (
          <div className="glass-panel-soft rounded-[20px] p-8 text-center" data-testid="support-success-panel">
            <CheckCircle2 className="w-12 h-12 mx-auto mb-4 text-[#6FA82E]" />
            <h2 className="text-lg font-semibold mb-2">Message envoyé !</h2>
            <p className="text-white/70 text-sm mb-1">Référence de votre demande :</p>
            <p className="text-[#D9B35A] font-bold text-xl mb-4" data-testid="support-ticket-number">{sentTicket}</p>
            <p className="text-white/60 text-sm mb-6">Un email de confirmation vous a été envoyé. Nous reviendrons vers vous rapidement.</p>
            <button
              onClick={() => { setSentTicket(null); setForm((f) => ({ ...f, subject: '', message: '' })); }}
              className="btn-ghost rounded-xl px-5 py-2.5 text-sm font-medium"
              data-testid="support-new-message-btn"
            >
              Envoyer un autre message
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="glass-panel-soft rounded-[20px] p-6 sm:p-8 space-y-5" data-testid="support-contact-form">
            <div className="grid sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs uppercase tracking-wider text-white/60 mb-2">Nom complet *</label>
                <input required minLength={2} value={form.name} onChange={set('name')} className={inputCls} data-testid="support-name-input" placeholder="Votre nom" />
              </div>
              <div>
                <label className="block text-xs uppercase tracking-wider text-white/60 mb-2">Email *</label>
                <input required type="email" value={form.email} onChange={set('email')} className={inputCls} data-testid="support-email-input" placeholder="vous@entreprise.fr" />
              </div>
            </div>

            <div className="grid sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs uppercase tracking-wider text-white/60 mb-2">Catégorie *</label>
                <select value={form.category} onChange={set('category')} className={inputCls} data-testid="support-category-select">
                  {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs uppercase tracking-wider text-white/60 mb-2">Sujet *</label>
                <input required minLength={3} value={form.subject} onChange={set('subject')} className={inputCls} data-testid="support-subject-input" placeholder="Résumé de votre demande" />
              </div>
            </div>

            <div>
              <label className="block text-xs uppercase tracking-wider text-white/60 mb-2">Message *</label>
              <textarea required minLength={10} rows={6} value={form.message} onChange={set('message')}
                className="w-full px-4 py-3 rounded-xl bg-white/[0.04] border border-white/10 text-sm focus:outline-none focus:border-[#D9B35A]/60 resize-y"
                data-testid="support-message-input" placeholder="Décrivez votre demande en détail (min. 10 caractères)…" />
            </div>

            <button type="submit" disabled={sending}
              className="btn-gold w-full h-12 rounded-xl inline-flex items-center justify-center gap-2 text-sm font-semibold disabled:opacity-60"
              data-testid="support-submit-btn">
              {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              {sending ? 'Envoi en cours…' : 'Envoyer le message'}
            </button>

            <p className="text-xs text-white/40 text-center flex items-center justify-center gap-1.5">
              <Mail className="w-3.5 h-3.5" /> Vous recevrez une confirmation par email avec votre numéro de suivi.
            </p>
          </form>
        )}

        {u.email && <MySupportTickets refreshKey={sentTicket || ''} />}
      </main>
      <Footer />
    </div>
  );
}
