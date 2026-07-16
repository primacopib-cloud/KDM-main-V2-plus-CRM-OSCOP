// Country flags SVG component
export const CountryFlag = ({ countryCode, size = 24 }) => {
  const flags = {
    FR: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="300" height="600" fill="#002395"/>
        <rect x="300" width="300" height="600" fill="#ffffff"/>
        <rect x="600" width="300" height="600" fill="#ED2939"/>
      </svg>
    ),
    ES: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="900" height="600" fill="#c60b1e"/>
        <rect y="150" width="900" height="300" fill="#ffc400"/>
      </svg>
    ),
    IT: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="300" height="600" fill="#009246"/>
        <rect x="300" width="300" height="600" fill="#ffffff"/>
        <rect x="600" width="300" height="600" fill="#ce2b37"/>
      </svg>
    ),
    DE: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="900" height="200" fill="#000000"/>
        <rect y="200" width="900" height="200" fill="#DD0000"/>
        <rect y="400" width="900" height="200" fill="#FFCC00"/>
      </svg>
    ),
    BE: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="300" height="600" fill="#000000"/>
        <rect x="300" width="300" height="600" fill="#FAE042"/>
        <rect x="600" width="300" height="600" fill="#ED2939"/>
      </svg>
    ),
    NL: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="900" height="200" fill="#AE1C28"/>
        <rect y="200" width="900" height="200" fill="#FFFFFF"/>
        <rect y="400" width="900" height="200" fill="#21468B"/>
      </svg>
    ),
    PT: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="360" height="600" fill="#006600"/>
        <rect x="360" width="540" height="600" fill="#FF0000"/>
        <circle cx="360" cy="300" r="100" fill="#FFCC00"/>
      </svg>
    ),
    MA: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="900" height="600" fill="#C1272D"/>
        <path d="M450,170 L485,295 L615,295 L510,370 L545,495 L450,420 L355,495 L390,370 L285,295 L415,295 Z" fill="none" stroke="#006233" strokeWidth="15"/>
      </svg>
    ),
    TN: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="900" height="600" fill="#E70013"/>
        <circle cx="450" cy="300" r="150" fill="#FFFFFF"/>
        <circle cx="480" cy="300" r="120" fill="#E70013"/>
        <path d="M400,300 L450,260 L450,340 Z" fill="#E70013"/>
      </svg>
    ),
    CN: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="900" height="600" fill="#DE2910"/>
        <polygon points="150,100 170,160 230,160 180,200 200,260 150,220 100,260 120,200 70,160 130,160" fill="#FFDE00"/>
      </svg>
    ),
    TH: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="900" height="100" fill="#A51931"/>
        <rect y="100" width="900" height="100" fill="#F4F5F8"/>
        <rect y="200" width="900" height="200" fill="#2D2A4A"/>
        <rect y="400" width="900" height="100" fill="#F4F5F8"/>
        <rect y="500" width="900" height="100" fill="#A51931"/>
      </svg>
    ),
    VN: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="900" height="600" fill="#DA251D"/>
        <polygon points="450,120 510,300 690,300 540,400 600,580 450,480 300,580 360,400 210,300 390,300" fill="#FFFF00"/>
      </svg>
    ),
    IN: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="900" height="200" fill="#FF9933"/>
        <rect y="200" width="900" height="200" fill="#FFFFFF"/>
        <rect y="400" width="900" height="200" fill="#138808"/>
        <circle cx="450" cy="300" r="60" fill="#000080"/>
      </svg>
    ),
    BR: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="900" height="600" fill="#009B3A"/>
        <polygon points="450,50 850,300 450,550 50,300" fill="#FEDF00"/>
        <circle cx="450" cy="300" r="100" fill="#002776"/>
      </svg>
    ),
    US: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="900" height="600" fill="#BF0A30"/>
        <rect y="46" width="900" height="46" fill="#FFFFFF"/>
        <rect y="138" width="900" height="46" fill="#FFFFFF"/>
        <rect y="230" width="900" height="46" fill="#FFFFFF"/>
        <rect y="322" width="900" height="46" fill="#FFFFFF"/>
        <rect y="414" width="900" height="46" fill="#FFFFFF"/>
        <rect y="506" width="900" height="46" fill="#FFFFFF"/>
        <rect width="360" height="322" fill="#002868"/>
      </svg>
    ),
  };
  
  return flags[countryCode] || (
    <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
      <rect width="900" height="600" fill="#cccccc"/>
      <text x="450" y="320" textAnchor="middle" fontSize="200" fill="#666666">{countryCode}</text>
    </svg>
  );
};
