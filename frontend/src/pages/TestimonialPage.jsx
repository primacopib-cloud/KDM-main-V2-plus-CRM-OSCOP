import React, { useState } from 'react';
import { Star, Loader2, CheckCircle2 } from 'lucide-react';
import { toast } from 'sonner';
import NavBar from '../components/NavBar';
import Footer from '../components/Footer';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const inp = 'w-full h-11 px-3 rounded-lg bg-white/[0.06] border border-white/15 text-sm text-white placeholder:text-white/35 focus:outline-none focus:border-[#D9B35A]/60';

export default function TestimonialPage() {
  const [form, setForm] = useState({ name: '', company: '', role: '', territory: '', email: '', rating: 5, text: '' });
  const [sending, setSending] = useState(false);
  const [done, setDone] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (!form.name.trim() || form.text.trim().length < 15) return toast.error('Nom et témoignage (15 caractères min.) requis');
    setSending(true);
    const r = await fetch(`${API}/public/testimonials`, {
      method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(form),
    });
    const d = await r.json();
    setSending(false);
    if (!r.ok) return toast.error(d.detail || 'Envoi impossible');
    setDone(true);
  };

  return (
    <div className="min-h-screen text-white" style={{ background: 'linear-gradient(160deg, #2A1045, #451F6B)' }}>
      <NavBar />
      <main className="max-w-[620px] mx-auto px-5 py-14" data-testid="testimonial-page">
        {done ? (
          <div className="text-center py-16" data-testid="testimonial-success">
            <CheckCircle2 size={48} className="mx-auto text-emerald-300 mb-4" />
            <h1 className="text-2xl font-display font-bold mb-2">Merci pour votre témoignage !</h1>
            <p className="text-white/65 text-sm">Il sera publié sur la page d'accueil après modération par notre équipe.</p>
          </div>
        ) : (
          <>
            <h1 className="text-3xl font-display font-bold mb-2">Partagez votre <span className="text-[#D9B35A]">expérience</span></h1>
            <p className="text-white/65 text-sm mb-8">
              Votre témoignage aide la Communityplace KDMARCHÉ × O'SCOP à grandir et inspire les futurs membres. 2 minutes suffisent.
            </p>
            <form onSubmit={submit} className="space-y-4 rounded-[18px] p-6 bg-white/[0.05] border border-white/10">
              <div className="grid sm:grid-cols-2 gap-3">
                <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Votre nom *" className={inp} data-testid="testimonial-name" required />
                <input value={form.company} onChange={(e) => setForm({ ...form, company: e.target.value })} placeholder="Entreprise" className={inp} data-testid="testimonial-company" />
                <input value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} placeholder="Fonction (ex : Gérant)" className={inp} />
                <input value={form.territory} onChange={(e) => setForm({ ...form, territory: e.target.value })} placeholder="Territoire (ex : Guadeloupe)" className={inp} />
              </div>
              <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="Email (non publié)" className={inp} />
              <div className="flex items-center gap-2">
                <span className="text-sm text-white/60">Votre note :</span>
                {[1, 2, 3, 4, 5].map((n) => (
                  <button key={n} type="button" onClick={() => setForm({ ...form, rating: n })} data-testid={`testimonial-star-${n}`}
                    className={n <= form.rating ? 'text-[#E9CF8E]' : 'text-white/25'}>
                    <Star size={22} fill={n <= form.rating ? 'currentColor' : 'none'} />
                  </button>
                ))}
              </div>
              <textarea value={form.text} onChange={(e) => setForm({ ...form, text: e.target.value })} rows={5}
                placeholder="Racontez votre expérience sur la plateforme (15 caractères minimum) *" data-testid="testimonial-text"
                className="w-full p-3 rounded-lg bg-white/[0.06] border border-white/15 text-sm text-white placeholder:text-white/35 focus:outline-none focus:border-[#D9B35A]/60" required />
              <button type="submit" disabled={sending} data-testid="testimonial-submit-btn"
                className="h-11 px-6 rounded-lg text-sm font-semibold text-[#1A092D] inline-flex items-center gap-2 disabled:opacity-50"
                style={{ background: 'linear-gradient(135deg, #D9B35A, #F2D07A)' }}>
                {sending && <Loader2 size={15} className="animate-spin" />} Envoyer mon témoignage
              </button>
            </form>
          </>
        )}
      </main>
      <Footer />
    </div>
  );
}
