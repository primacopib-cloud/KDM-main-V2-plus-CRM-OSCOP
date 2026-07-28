import { useNavigate } from 'react-router-dom';

// Bouton retour universel : page précédente si historique, sinon destination de secours
export const BackLink = ({ fallback = '/', className, children, ...rest }) => {
  const navigate = useNavigate();
  const goBack = () => (window.history.length > 1 ? navigate(-1) : navigate(fallback));
  return (
    <button type="button" onClick={goBack} className={className} {...rest}>
      {children}
    </button>
  );
};
