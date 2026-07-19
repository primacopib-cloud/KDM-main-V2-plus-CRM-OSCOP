export const COUNTRIES = [
  { code: 'GP', name: 'Guadeloupe', flag: '🇬🇵', dial: '+590' },
  { code: 'MQ', name: 'Martinique', flag: '🇲🇶', dial: '+596' },
  { code: 'GF', name: 'Guyane', flag: '🇬🇫', dial: '+594' },
  { code: 'RE', name: 'La Réunion', flag: '🇷🇪', dial: '+262' },
  { code: 'YT', name: 'Mayotte', flag: '🇾🇹', dial: '+262' },
  { code: 'MF', name: 'Saint-Martin', flag: '🇲🇫', dial: '+590' },
  { code: 'FR', name: 'France métropolitaine', flag: '🇫🇷', dial: '+33' },
  { code: 'BE', name: 'Belgique', flag: '🇧🇪', dial: '+32' },
  { code: 'LU', name: 'Luxembourg', flag: '🇱🇺', dial: '+352' },
  { code: 'CH', name: 'Suisse', flag: '🇨🇭', dial: '+41' },
  { code: 'ES', name: 'Espagne', flag: '🇪🇸', dial: '+34' },
  { code: 'PT', name: 'Portugal', flag: '🇵🇹', dial: '+351' },
  { code: 'IT', name: 'Italie', flag: '🇮🇹', dial: '+39' },
  { code: 'DE', name: 'Allemagne', flag: '🇩🇪', dial: '+49' },
  { code: 'NL', name: 'Pays-Bas', flag: '🇳🇱', dial: '+31' },
  { code: 'IE', name: 'Irlande', flag: '🇮🇪', dial: '+353' },
  { code: 'GB', name: 'Royaume-Uni', flag: '🇬🇧', dial: '+44' },
  { code: 'US', name: 'États-Unis', flag: '🇺🇸', dial: '+1' },
  { code: 'CA', name: 'Canada', flag: '🇨🇦', dial: '+1' },
  { code: 'BR', name: 'Brésil', flag: '🇧🇷', dial: '+55' },
  { code: 'DO', name: 'Rép. Dominicaine', flag: '🇩🇴', dial: '+1809' },
  { code: 'HT', name: 'Haïti', flag: '🇭🇹', dial: '+509' },
  { code: 'MU', name: 'Maurice', flag: '🇲🇺', dial: '+230' },
  { code: 'MG', name: 'Madagascar', flag: '🇲🇬', dial: '+261' },
  { code: 'MA', name: 'Maroc', flag: '🇲🇦', dial: '+212' },
  { code: 'SN', name: 'Sénégal', flag: '🇸🇳', dial: '+221' },
  { code: 'CI', name: "Côte d'Ivoire", flag: '🇨🇮', dial: '+225' },
  { code: 'CM', name: 'Cameroun', flag: '🇨🇲', dial: '+237' },
];

const DOM_85 = ['GP', 'MQ', 'RE'];
const DOM_0 = ['GF', 'YT'];

export const vatRateFor = (code) => {
  if (DOM_85.includes(code)) return 8.5;
  if (DOM_0.includes(code)) return 0;
  if (code === 'FR') return 20;
  return 0;
};
