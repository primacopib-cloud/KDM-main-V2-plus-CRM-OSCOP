import React from 'react';
import { render, screen } from '@testing-library/react';
import { PaymentStep } from './CheckoutPayment';

// Bandeau urgence promo flash à l'étape paiement
test('affiche le bandeau urgence quand promoUrgency est fourni à l étape 4', () => {
  render(
    <PaymentStep
      currentStep={4}
      totals={{ totalTTC: 10000, installmentTotal: 12000 }}
      useInstallment={false}
      setUseInstallment={() => {}}
      paymentMethod="card"
      setPaymentMethod={() => {}}
      orderNotes=""
      setOrderNotes={() => {}}
      signatureComplete={true}
      processingPayment={false}
      handlePayment={() => {}}
      promoUrgency={{ name: 'Flash de lancement', value_percent: 10, leftMs: 20 * 3600000 }}
    />
  );
  const banner = screen.getByTestId('checkout-promo-urgency');
  expect(banner.textContent).toContain('Promo flash −10%');
  expect(banner.textContent).toContain('fin dans 20 h 00 min');
  expect(banner.textContent).toContain('Flash de lancement');
});

test('pas de bandeau sans promoUrgency', () => {
  render(
    <PaymentStep
      currentStep={4}
      totals={{ totalTTC: 10000, installmentTotal: 12000 }}
      useInstallment={false}
      setUseInstallment={() => {}}
      paymentMethod="card"
      setPaymentMethod={() => {}}
      orderNotes=""
      setOrderNotes={() => {}}
      signatureComplete={true}
      processingPayment={false}
      handlePayment={() => {}}
    />
  );
  expect(screen.queryByTestId('checkout-promo-urgency')).toBeNull();
});
