import { useNavigate, useLocation } from 'react-router-dom';
import { popPrevious } from '../utils/backStack';

// Bouton retour universel : page interne précédente (pile interne), sinon destination de secours
export const BackLink = ({ fallback = '/', className, children, ...rest }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const goBack = () => {
    const prev = popPrevious(location.pathname + location.search);
    navigate(prev || fallback);
  };
  return (
    <button type="button" onClick={goBack} className={className} {...rest}>
      {children}
    </button>
  );
};
