import {
  Calendar, CalendarDays, CalendarRange, CalendarCheck, Settings,
} from 'lucide-react';

export const frequencyIcons = {
  weekly: Calendar,
  biweekly: Calendar,
  monthly: CalendarDays,
  quarterly: CalendarRange,
  one_time: CalendarCheck,
  custom: Settings,
};

export const frequencyLabels = {
  weekly: 'Hebdomadaire',
  biweekly: 'Bi-mensuel',
  monthly: 'Mensuel',
  quarterly: 'Trimestriel',
  one_time: 'Ponctuel',
  custom: 'Personnalisé',
};

export const frequencyColors = {
  weekly: '#D4AF37',
  biweekly: '#3B82F6',
  monthly: '#8B5CF6',
  quarterly: '#F59E0B',
  one_time: '#6B7280',
  custom: '#D9B35A',
};

export const COLOR_OPTIONS = [
    { value: '#D9B35A', label: 'Or' },
    { value: '#D4AF37', label: 'Vert' },
    { value: '#3B82F6', label: 'Bleu' },
    { value: '#8B5CF6', label: 'Violet' },
    { value: '#EC4899', label: 'Rose' },
    { value: '#F59E0B', label: 'Orange' },
  ];
