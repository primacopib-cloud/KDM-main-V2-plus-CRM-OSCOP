// Countries data with flags (SVG) and phone codes
// Focus on France + DOM-TOM + African francophone countries

export const countries = [
  // France métropolitaine et DOM-TOM
  {
    code: 'FR',
    name: 'France',
    phoneCode: '+33',
    flag: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 600"><rect width="900" height="600" fill="#ED2939"/><rect width="600" height="600" fill="#fff"/><rect width="300" height="600" fill="#002395"/></svg>`
  },
  {
    code: 'GP',
    name: 'Guadeloupe',
    phoneCode: '+590',
    flag: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 600"><rect width="900" height="600" fill="#ED2939"/><rect width="600" height="600" fill="#fff"/><rect width="300" height="600" fill="#002395"/></svg>`
  },
  {
    code: 'MQ',
    name: 'Martinique',
    phoneCode: '+596',
    flag: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 600"><rect width="900" height="600" fill="#ED2939"/><rect width="600" height="600" fill="#fff"/><rect width="300" height="600" fill="#002395"/></svg>`
  },
  {
    code: 'GF',
    name: 'Guyane française',
    phoneCode: '+594',
    flag: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 600"><rect width="900" height="600" fill="#ED2939"/><rect width="600" height="600" fill="#fff"/><rect width="300" height="600" fill="#002395"/></svg>`
  },
  {
    code: 'RE',
    name: 'La Réunion',
    phoneCode: '+262',
    flag: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 600"><rect width="900" height="600" fill="#ED2939"/><rect width="600" height="600" fill="#fff"/><rect width="300" height="600" fill="#002395"/></svg>`
  },
  {
    code: 'YT',
    name: 'Mayotte',
    phoneCode: '+262',
    flag: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 600"><rect width="900" height="600" fill="#ED2939"/><rect width="600" height="600" fill="#fff"/><rect width="300" height="600" fill="#002395"/></svg>`
  },
  {
    code: 'NC',
    name: 'Nouvelle-Calédonie',
    phoneCode: '+687',
    flag: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 600"><rect width="900" height="600" fill="#ED2939"/><rect width="600" height="600" fill="#fff"/><rect width="300" height="600" fill="#002395"/></svg>`
  },
  {
    code: 'PF',
    name: 'Polynésie française',
    phoneCode: '+689',
    flag: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 600"><rect width="900" height="600" fill="#ED2939"/><rect width="600" height="600" fill="#fff"/><rect width="300" height="600" fill="#002395"/></svg>`
  },
  {
    code: 'WF',
    name: 'Wallis-et-Futuna',
    phoneCode: '+681',
    flag: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 600"><rect width="900" height="600" fill="#ED2939"/><rect width="600" height="600" fill="#fff"/><rect width="300" height="600" fill="#002395"/></svg>`
  },
  {
    code: 'PM',
    name: 'Saint-Pierre-et-Miquelon',
    phoneCode: '+508',
    flag: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 600"><rect width="900" height="600" fill="#ED2939"/><rect width="600" height="600" fill="#fff"/><rect width="300" height="600" fill="#002395"/></svg>`
  },
  {
    code: 'BL',
    name: 'Saint-Barthélemy',
    phoneCode: '+590',
    flag: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 600"><rect width="900" height="600" fill="#ED2939"/><rect width="600" height="600" fill="#fff"/><rect width="300" height="600" fill="#002395"/></svg>`
  },
  {
    code: 'MF',
    name: 'Saint-Martin',
    phoneCode: '+590',
    flag: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 600"><rect width="900" height="600" fill="#ED2939"/><rect width="600" height="600" fill="#fff"/><rect width="300" height="600" fill="#002395"/></svg>`
  },
  
  // Europe
  {
    code: 'BE',
    name: 'Belgique',
    phoneCode: '+32',
    flag: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 600"><rect width="300" height="600" fill="#000"/><rect x="300" width="300" height="600" fill="#FFD90C"/><rect x="600" width="300" height="600" fill="#F31830"/></svg>`
  },
  {
    code: 'CH',
    name: 'Suisse',
    phoneCode: '+41',
    flag: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect fill="#f00" width="32" height="32"/><rect fill="#fff" x="13" y="6" width="6" height="20"/><rect fill="#fff" x="6" y="13" width="20" height="6"/></svg>`
  },
  {
    code: 'LU',
    name: 'Luxembourg',
    phoneCode: '+352',
    flag: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 600"><rect width="900" height="200" fill="#ED2939"/><rect y="200" width="900" height="200" fill="#fff"/><rect y="400" width="900" height="200" fill="#00A1DE"/></svg>`
  },
  {
    code: 'MC',
    name: 'Monaco',
    phoneCode: '+377',
    flag: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 600"><rect width="900" height="300" fill="#CE1126"/><rect y="300" width="900" height="300" fill="#fff"/></svg>`
  },
  
  // Afrique francophone
  {
    code: 'SN',
    name: 'Sénégal',
    phoneCode: '+221',
    flag: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 600"><rect width="300" height="600" fill="#00853F"/><rect x="300" width="300" height="600" fill="#FDEF42"/><rect x="600" width="300" height="600" fill="#E31B23"/><path d="M450 225l15 45h48l-39 28 15 46-39-28-39 28 15-46-39-28h48z" fill="#00853F"/></svg>`
  },
  {
    code: 'CI',
    name: 'Côte d\'Ivoire',
    phoneCode: '+225',
    flag: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 600"><rect width="300" height="600" fill="#F77F00"/><rect x="300" width="300" height="600" fill="#fff"/><rect x="600" width="300" height="600" fill="#009E60"/></svg>`
  },
  {
    code: 'ML',
    name: 'Mali',
    phoneCode: '+223',
    flag: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 600"><rect width="300" height="600" fill="#14B53A"/><rect x="300" width="300" height="600" fill="#FCD116"/><rect x="600" width="300" height="600" fill="#CE1126"/></svg>`
  },
  {
    code: 'BF',
    name: 'Burkina Faso',
    phoneCode: '+226',
    flag: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 600"><rect width="900" height="300" fill="#EF2B2D"/><rect y="300" width="900" height="300" fill="#009E49"/><path d="M450 200l30 90h95l-77 56 30 90-78-56-78 56 30-90-77-56h95z" fill="#FCD116"/></svg>`
  },
  {
    code: 'NE',
    name: 'Niger',
    phoneCode: '+227',
    flag: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 600"><rect width="900" height="200" fill="#E05206"/><rect y="200" width="900" height="200" fill="#fff"/><rect y="400" width="900" height="200" fill="#0DB02B"/><circle cx="450" cy="300" r="60" fill="#E05206"/></svg>`
  },
  {
    code: 'TG',
    name: 'Togo',
    phoneCode: '+228',
    flag: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 600"><rect width="900" height="120" fill="#006A4E"/><rect y="120" width="900" height="120" fill="#FFCE00"/><rect y="240" width="900" height="120" fill="#006A4E"/><rect y="360" width="900" height="120" fill="#FFCE00"/><rect y="480" width="900" height="120" fill="#006A4E"/><rect width="360" height="360" fill="#D21034"/><path d="M180 90l20 60h63l-51 37 20 60-52-38-52 38 20-60-51-37h63z" fill="#fff"/></svg>`
  },
  {
    code: 'BJ',
    name: 'Bénin',
    phoneCode: '+229',
    flag: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 600"><rect width="360" height="600" fill="#008751"/><rect x="360" width="540" height="300" fill="#FCD116"/><rect x="360" y="300" width="540" height="300" fill="#E8112D"/></svg>`
  },
  {
    code: 'CM',
    name: 'Cameroun',
    phoneCode: '+237',
    flag: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 600"><rect width="300" height="600" fill="#007A5E"/><rect x="300" width="300" height="600" fill="#CE1126"/><rect x="600" width="300" height="600" fill="#FCD116"/><path d="M450 200l25 75h80l-65 47 25 78-65-48-65 48 25-78-65-47h80z" fill="#FCD116"/></svg>`
  },
  {
    code: 'GA',
    name: 'Gabon',
    phoneCode: '+241',
    flag: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 600"><rect width="900" height="200" fill="#009E60"/><rect y="200" width="900" height="200" fill="#FCD116"/><rect y="400" width="900" height="200" fill="#3A75C4"/></svg>`
  },
  {
    code: 'CG',
    name: 'Congo',
    phoneCode: '+242',
    flag: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 600"><defs><clipPath id="a"><path d="M0 0h900v600H0z"/></clipPath></defs><g clip-path="url(#a)"><path fill="#009543" d="M0 0h900v600H0z"/><path fill="#FBDE4A" d="M0 600L900 0v600z"/><path fill="#DC241F" d="M0 600L900 0H0z"/></g></svg>`
  },
  {
    code: 'CD',
    name: 'RD Congo',
    phoneCode: '+243',
    flag: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 600"><rect width="900" height="600" fill="#007FFF"/><path d="M0 0l180 90-180 90" fill="#F7D618"/><path d="M0 0h900v120H120z" fill="#CE1021"/><path d="M0 480h780l120 60v60H0z" fill="#CE1021"/></svg>`
  },
  {
    code: 'MG',
    name: 'Madagascar',
    phoneCode: '+261',
    flag: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 600"><rect x="200" width="700" height="300" fill="#FC3D32"/><rect x="200" y="300" width="700" height="300" fill="#007E3A"/><rect width="200" height="600" fill="#fff"/></svg>`
  },
  {
    code: 'MU',
    name: 'Maurice',
    phoneCode: '+230',
    flag: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 600"><rect width="900" height="150" fill="#EA2839"/><rect y="150" width="900" height="150" fill="#1A206D"/><rect y="300" width="900" height="150" fill="#FFD500"/><rect y="450" width="900" height="150" fill="#00A551"/></svg>`
  },
  {
    code: 'DZ',
    name: 'Algérie',
    phoneCode: '+213',
    flag: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 600"><rect width="450" height="600" fill="#006233"/><rect x="450" width="450" height="600" fill="#fff"/><circle cx="450" cy="300" r="120" fill="#D21034"/><circle cx="480" cy="300" r="95" fill="#fff"/><path d="M455 210l15 45 47-2-37 29 15 45-40-28-40 28 15-45-37-29 47 2z" fill="#D21034"/></svg>`
  },
  {
    code: 'MA',
    name: 'Maroc',
    phoneCode: '+212',
    flag: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 600"><rect width="900" height="600" fill="#C1272D"/><path d="M450 180l35 105 110 0-90 65 35 105-90-65-90 65 35-105-90-65 110 0z" fill="none" stroke="#006233" stroke-width="12"/></svg>`
  },
  {
    code: 'TN',
    name: 'Tunisie',
    phoneCode: '+216',
    flag: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 600"><rect width="900" height="600" fill="#E70013"/><circle cx="450" cy="300" r="150" fill="#fff"/><circle cx="480" cy="300" r="120" fill="#E70013"/><path d="M420 300l45-30 0 55-45-25z" fill="#E70013"/></svg>`
  },
  
  // Autres
  {
    code: 'HT',
    name: 'Haïti',
    phoneCode: '+509',
    flag: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 600"><rect width="900" height="300" fill="#00209F"/><rect y="300" width="900" height="300" fill="#D21034"/><rect x="300" y="150" width="300" height="300" fill="#fff"/></svg>`
  },
  {
    code: 'CA',
    name: 'Canada',
    phoneCode: '+1',
    flag: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 600"><rect width="225" height="600" fill="#D52B1E"/><rect x="225" width="450" height="600" fill="#fff"/><rect x="675" width="225" height="600" fill="#D52B1E"/><path d="M450 100l20 60-50-25v90l-30-45-30 60 10-60-40 30 30-60h-50l50-50-20-30 50 20 30-50 30 50 50-20-20 30 50 50h-50l30 60-40-30 10 60-30-60-30 45v-90l-50 25z" fill="#D52B1E"/></svg>`
  },
];

// Get flag as data URL for use in img src
export const getFlagDataUrl = (svgString) => {
  return `data:image/svg+xml,${encodeURIComponent(svgString)}`;
};

// Find country by code
export const getCountryByCode = (code) => {
  return countries.find(c => c.code === code);
};

// Find country by phone code
export const getCountryByPhoneCode = (phoneCode) => {
  return countries.find(c => c.phoneCode === phoneCode);
};

// Default country (France)
export const defaultCountry = countries[0];

// Get phone placeholder based on country
export const getPhonePlaceholder = (countryCode) => {
  const placeholders = {
    'FR': '06 12 34 56 78',
    'GP': '0690 12 34 56',
    'MQ': '0696 12 34 56',
    'GF': '0694 12 34 56',
    'RE': '0692 12 34 56',
    'BE': '0470 12 34 56',
    'CH': '076 123 45 67',
    'SN': '77 123 45 67',
    'CI': '07 12 34 56 78',
    'MA': '0612 34 56 78',
  };
  return placeholders[countryCode] || '123 456 789';
};
