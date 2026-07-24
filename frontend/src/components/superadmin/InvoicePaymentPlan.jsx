import { useState } from 'react';
import { CalendarPlus, Check, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';

const eur = (c) => `${((c || 0) / 100).toFixed(2)} €`;
const INST_STATUS = {
  PENDING: ['À venir', 'text-amber-300'],
  PAID: ['Réglée ✓', 'text-emerald-400'],
  OVERDUE: ['EN RETARD', 'text-red-300'],
};

export const LiftSuspensionForm = ({ invoice, onDone }) => {
  const [rows, setRows] = useState([{ due_date: '', amount_eur: '' }]);
  const [busy, setBusy] = useState(false);

  const submit = async (withPlan) => {
    setBusy(true);
    try {
      const installments = withPlan
        ? rows.filter((r) => r.due_date && Number(r.amount_eur) > 0)
            .map((r) => ({ due_date: r.due_date, amount_eur: Number(r.amount_eur) }))
        : [];
      if (withPlan && !installments.length) throw new Error('Ajoutez au moins une échéance valide (date + montant)');
      const r = await fetch(`${API}/logiscop-transport/admin/invoices/${invoice.id}/lift-suspension`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ installments }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Action impossible');
      toast.success(`Suspension levée — ${d.ref}${d.installments ? ` (échéancier : ${d.installments} échéance(s))` : ''}`);
      onDone?.();
    } catch (e) { toast.error(e.message); }
    setBusy(false);
  };

  const inp = 'h-7 px-2 rounded bg-white/[0.06] border border-white/15 text-[10px] text-white';
  return (
    <div className="rounded-lg p-2.5 mt-1.5 bg-amber-500/[0.06] border border-amber-500/25 space-y-1.5"
      data-testid={`lift-form-${invoice.ref}`}>
      <p className="text-[10px] font-bold text-amber-300">
        Levée de suspension — échéancier de paiement (optionnel, {eur(invoice.total_ttc_cents)} TTC dûs)
      </p>
      {rows.map((r, i) => (
        <div key={i} className="flex items-center gap-1.5">
          <input type="date" value={r.due_date} data-testid={`plan-date-${i}`}
            onChange={(e) => setRows(rows.map((x, j) => (j === i ? { ...x, due_date: e.target.value } : x)))}
            className={inp} />
          <input type="number" placeholder="Montant €" value={r.amount_eur} data-testid={`plan-amount-${i}`}
            onChange={(e) => setRows(rows.map((x, j) => (j === i ? { ...x, amount_eur: e.target.value } : x)))}
            className={`${inp} w-24`} />
          {rows.length > 1 && (
            <button type="button" onClick={() => setRows(rows.filter((_, j) => j !== i))}
              className="text-white/40 hover:text-red-300"><Trash2 size={12} /></button>
          )}
        </div>
      ))}
      <div className="flex flex-wrap items-center gap-1.5">
        <button type="button" onClick={() => setRows([...rows, { due_date: '', amount_eur: '' }])}
          className="px-2 py-1 rounded-lg text-[10px] text-white/60 hover:text-white border border-white/15 inline-flex items-center gap-1">
          <CalendarPlus size={10} /> Échéance
        </button>
        <button type="button" disabled={busy} onClick={() => submit(true)} data-testid={`lift-with-plan-${invoice.ref}`}
          className="px-2 py-1 rounded-lg text-[10px] font-bold bg-amber-500/20 text-amber-300 hover:bg-amber-500/30 disabled:opacity-50">
          Lever avec échéancier
        </button>
        <button type="button" disabled={busy} onClick={() => submit(false)} data-testid={`lift-no-plan-${invoice.ref}`}
          className="px-2 py-1 rounded-lg text-[10px] text-white/50 hover:text-white border border-white/15 disabled:opacity-50">
          Lever sans échéancier
        </button>
      </div>
    </div>
  );
};

export const InvoicePaymentPlan = ({ invoice, onChanged }) => {
  const plan = invoice.payment_plan;
  if (!plan?.installments?.length) return null;

  const markPaid = async (idx) => {
    try {
      const r = await fetch(`${API}/logiscop-transport/admin/invoices/${invoice.id}/plan/${idx}/mark-paid`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Action impossible');
      toast.success(d.invoice_paid ? `Échéancier soldé — facture ${d.ref} PAYÉE` : `Échéance n°${idx + 1} pointée`);
      onChanged?.();
    } catch (e) { toast.error(e.message); }
  };

  return (
    <div className="mt-1 space-y-0.5" data-testid={`payment-plan-${invoice.ref}`}>
      {plan.installments.map((inst, i) => {
        const [label, cls] = INST_STATUS[inst.status] || [inst.status, 'text-white/50'];
        return (
          <p key={i} className="text-[10px] text-white/50 flex items-center gap-1.5">
            Échéance {i + 1} : {inst.due_date} — {eur(inst.amount_cents)}
            <span className={`font-bold ${cls}`}>{label}</span>
            {inst.status !== 'PAID' && invoice.status !== 'PAID' && (
              <button type="button" data-testid={`plan-pay-${invoice.ref}-${i}`} onClick={() => markPaid(i)}
                className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-emerald-500/20 text-emerald-300 hover:bg-emerald-500/30 inline-flex items-center gap-0.5">
                <Check size={9} /> Pointer
              </button>
            )}
          </p>
        );
      })}
    </div>
  );
};
