import i18n from '@/i18n';

const LABELS = {
  fr: ['Très faible', 'Faible', 'Moyen', 'Bon', 'Excellent'],
  en: ['Very weak', 'Weak', 'Medium', 'Good', 'Excellent'],
  es: ['Muy débil', 'Débil', 'Media', 'Buena', 'Excelente'],
  gcf: ['Two fèb', 'Fèb', 'Mwayen', 'Bon', 'Ekselan'],
};
const COLORS = ['#FF5A4A', '#FF7A00', '#E9CF8E', '#8CC63E', '#10B981'];

export const passwordScore = (pwd) => {
  if (!pwd) return 0;
  let s = 0;
  if (pwd.length >= 8) s += 1;
  if (pwd.length >= 12) s += 1;
  if (/[a-z]/.test(pwd) && /[A-Z]/.test(pwd)) s += 1;
  if (/\d/.test(pwd)) s += 1;
  if (/[^A-Za-z0-9]/.test(pwd)) s += 1;
  return Math.min(4, s);
};

export const PasswordStrength = ({ password }) => {
  if (!password) return null;
  const lang = i18n.language?.startsWith('gcf') ? 'gcf' : (i18n.language || 'fr').slice(0, 2);
  const labels = LABELS[lang] || LABELS.fr;
  const score = passwordScore(password);
  return (
    <div className="mt-2" data-testid="password-strength">
      <div className="flex gap-1">
        {[0, 1, 2, 3].map((i) => (
          <span key={i} className="h-1.5 flex-1 rounded-full transition-colors duration-300"
            style={{ background: i < score ? COLORS[score] : 'rgba(255,255,255,0.12)' }} />
        ))}
      </div>
      <p className="text-[11px] mt-1 font-medium" style={{ color: COLORS[score] }}
        data-testid="password-strength-label">{labels[score]}</p>
    </div>
  );
};
