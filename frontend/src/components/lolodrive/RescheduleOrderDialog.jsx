import { useEffect, useState } from 'react';
import { CalendarClock } from 'lucide-react';
import { toast } from 'sonner';
import { lolodriveAPI } from '../../services/api';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Button } from '../ui/button';
import { PickupCalendar } from './PickupCalendar';

// Le membre déplace la date/créneau de retrait de sa commande vers un créneau libre
export const RescheduleOrderDialog = ({ order, open, onOpenChange, onDone }) => {
  const [point, setPoint] = useState(null);
  const [cfg, setCfg] = useState(null);
  const [avail, setAvail] = useState(null);
  const [pickupDate, setPickupDate] = useState(order?.pickup_date || '');
  const [slotId, setSlotId] = useState(order?.pickup_slot_id || '');
  const [saving, setSaving] = useState(false);

  const kind = order?.fulfillment_type === 'DELIVERY' ? 'delivery' : 'pickup';
  const pid = order?.lolo_point_id || order?.reference_point_id;

  useEffect(() => {
    if (!open) return;
    setPickupDate(order?.pickup_date || '');
    setSlotId(order?.pickup_slot_id || '');
    lolodriveAPI.feesConfig().then(setCfg).catch(() => {});
    lolodriveAPI.listLoloPoints().then((res) => {
      const pts = res.points || [];
      setPoint(pts.find((p) => p.id === pid) || null);
    }).catch(() => {});
  }, [open, order, pid]);

  if (!order) return null;
  const slots = cfg?.[`${kind}_slots`] || [];
  const dayInfo = (avail?.days || []).find((d) => d.date === pickupDate);
  const slotFull = (sid) => Boolean(dayInfo?.slots?.[sid]?.full);
  const slotQuiet = (sid) => Boolean(dayInfo?.slots?.[sid]?.quiet);

  const save = async () => {
    setSaving(true);
    try {
      await lolodriveAPI.rescheduleOrder(order.id, { pickup_date: pickupDate, pickup_slot_id: slotId });
      toast.success(`Commande déplacée au ${new Date(`${pickupDate}T12:00:00`).toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' })}`);
      onOpenChange(false);
      onDone?.();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-[#0a0a0f] border-white/10 text-white sm:max-w-md" data-testid="reschedule-dialog">
        <DialogHeader>
          <DialogTitle className="text-white flex items-center gap-2 text-base">
            <CalendarClock className="w-4 h-4 text-[#D9B35A]" />
            Déplacer la commande {order.order_number}
          </DialogTitle>
        </DialogHeader>
        <p className="text-xs text-white/50 -mt-1">
          Choisissez une nouvelle date et un créneau libre{point ? ` — calendrier ${point.name}` : ''}. Maximum 2 déplacements.
        </p>
        <PickupCalendar relayCode={point?.code} relayDays={kind === 'delivery' ? point?.delivery_days : point?.pickup_days}
          kind={kind} pickupDate={pickupDate} setPickupDate={setPickupDate} slotId={slotId} onAvailability={setAvail} />
        <Select value={slotId} onValueChange={setSlotId}>
          <SelectTrigger className="h-9 bg-white/[0.04] border-white/15 text-white text-xs" data-testid="reschedule-slot-select">
            <SelectValue placeholder="Choisir un créneau" />
          </SelectTrigger>
          <SelectContent>
            {slots.map((s) => (
              <SelectItem key={s.id} value={s.id} disabled={slotFull(s.id)} data-testid={`reschedule-slot-${s.id}`}>
                {s.label}{slotFull(s.id) ? ' — COMPLET' : slotQuiet(s.id) ? ' — créneau calme (+2 UC)' : ''}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button onClick={save} disabled={saving || !pickupDate || !slotId}
          data-testid="reschedule-confirm-btn"
          className="bg-[#D9B35A] text-black hover:bg-[#E9CF8E] font-bold">
          {saving ? 'Déplacement…' : 'Confirmer le déplacement'}
        </Button>
      </DialogContent>
    </Dialog>
  );
};
