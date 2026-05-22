import React, { useState } from 'react';
import { CreditCard, ExternalLink, Loader2 } from 'lucide-react';
import { Button } from './ui/button';
import { toast } from 'sonner';

/**
 * Generic Stripe Checkout button.
 * Calls the provided createSession function with `window.location.origin`,
 * receives { url, session_id } and redirects to Stripe-hosted checkout.
 * On return, /paiement/retour polls status and applies business logic server-side.
 */
export default function StripeCheckoutButton({
  createSession,
  label = 'Payer par CB (Stripe)',
  variant = 'default',
  size = 'default',
  disabled = false,
  className = '',
  testId,
  icon = <CreditCard className="w-4 h-4 mr-2" />,
}) {
  const [loading, setLoading] = useState(false);

  const handle = async () => {
    setLoading(true);
    try {
      const origin = window.location.origin;
      const r = await createSession(origin);
      if (!r?.url) throw new Error('URL Stripe manquante');
      // Redirect to Stripe hosted page
      window.location.href = r.url;
    } catch (e) {
      toast.error(e.message || 'Erreur paiement');
      setLoading(false);
    }
  };

  return (
    <Button
      onClick={handle}
      disabled={disabled || loading}
      variant={variant}
      size={size}
      className={className}
      data-testid={testId}
      style={variant === 'default' ? { background: 'linear-gradient(135deg, #D9B35A, #7c3aed)' } : undefined}
    >
      {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : icon}
      {label}
      <ExternalLink className="w-3 h-3 ml-1 opacity-60" />
    </Button>
  );
}
