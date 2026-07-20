import { useEffect } from "react";
import "./App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "./components/ui/sonner";

// Pages
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
const RedirectInscription = () => <Navigate to={{ pathname: '/adhesion-vendeur', search: window.location.search }} replace />;
import DashboardPage from "./pages/DashboardPage";
import OffersPage from "./pages/OffersPage";
import ForgotPasswordPage from "./pages/ForgotPasswordPage";
import ResetPasswordPage from "./pages/ResetPasswordPage";
import StatsPage from "./pages/StatsPage";
import AdminPage from "./pages/AdminPage";
import OnboardingPage from "./pages/OnboardingPage";
import CatalogPage from "./pages/CatalogPage";
import OrdersPage from "./pages/OrdersPage";
import AdminV2Page from "./pages/AdminV2Page";
import DocumentsPage from "./pages/DocumentsPage";
import WalletPage from "./pages/WalletPage";
import CrediscopStatementPage from "./pages/CrediscopStatementPage";
import LegalPage from "./pages/LegalPage";
import OrderPreviewPage from "./pages/OrderPreviewPage";
import SignatureDemoPage from "./pages/SignatureDemoPage";
import SuperAdminPage from "./pages/SuperAdminPage";
import TenantPage from "./pages/TenantPage";
import ApiDocsPage from "./pages/ApiDocsPage";
import PartnerDevPage from "./pages/PartnerDevPage";
import DynamicOrderPage from "./pages/DynamicOrderPage";
import VendorSpacePage from "./pages/VendorSpacePage";
import CooperSpacePage from "./pages/CooperSpacePage";
import ExpertSpacePage from "./pages/ExpertSpacePage";
import KdmarchePage from "./pages/KdmarchePage";
import SupportContactPage from "./pages/SupportContactPage";
import PartnershipPage from "./pages/PartnershipPage";
import ChangePasswordPage from "./pages/ChangePasswordPage";
import AdminProductsPage from "./pages/AdminProductsPage";
import BuyerSpacePage from "./pages/BuyerSpacePage";
import CheckoutPage from "./pages/CheckoutPage";
import ProductCardDemoPage from "./pages/ProductCardDemoPage";
import NotificationsHistoryPage from "./pages/NotificationsHistoryPage";
import AiChatPage from "./pages/AiChatPage";
import VendorOnboardingPage from "./pages/VendorOnboardingPage";
import VendorActivationPage from "./pages/VendorActivationPage";
import FavoritesPage from "./pages/FavoritesPage";
import ShoppingListsPage from "./pages/ShoppingListsPage";
import ShoppingListDetailPage from "./pages/ShoppingListDetailPage";
import AdminPlansPage from "./pages/AdminPlansPage";
import AdminLoginPage from "./pages/AdminLoginPage";
import PricingPage from "./pages/PricingPage";
import MessagesPage from "./pages/MessagesPage";
import PartnerSignPage from "./pages/PartnerSignPage";
import { FavoritesProvider } from "./components/FavoriteButton";
import BackButton from "./components/BackButton";

// LOLODRIVE by O'SCOP - 7 nouvelles pages
import LolodriveAdminDashboardPage from "./pages/LolodriveAdminDashboardPage";
import PassSpacePage from "./pages/PassSpacePage";
import PosLolodrivePage from "./pages/PosLolodrivePage";
import LoloPointsAdminPage from "./pages/LoloPointsAdminPage";
import LoloHourAdminPage from "./pages/LoloHourAdminPage";
import CrmPartnersPage from "./pages/CrmPartnersPage";
import EssReportingPage from "./pages/EssReportingPage";
import LoloPointManagerPage from "./pages/LoloPointManagerPage";
import LolodriveCatalogPage from "./pages/LolodriveCatalogPage";
import PaymentReturnPage from "./pages/PaymentReturnPage";
import AuthCallbackPage from "./pages/AuthCallbackPage";
import GoogleAuthReturnPage from "./pages/GoogleAuthReturnPage";
import StripeReconciliationPage from "./pages/StripeReconciliationPage";
import GedBridgeAdminPage from "./pages/GedBridgeAdminPage";
import FinanceBridgeAdminPage from "./pages/FinanceBridgeAdminPage";
import ConnectorsAdminPage from "./pages/ConnectorsAdminPage";
import FavoriteAlertsPage from "./pages/FavoriteAlertsPage";
import LogiscopPage from "./pages/LogiscopPage";
import LogicoopSpacePage from "./pages/LogicoopSpacePage";
import OscopPage from "./pages/OscopPage";

const PLATFORM_HOST_SUFFIXES = ['localhost', '127.0.0.1', 'emergent.host', 'emergentagent.com', 'objectifscopoutremer.com'];
const isCustomDomain = !PLATFORM_HOST_SUFFIXES.some(
  (h) => window.location.hostname === h || window.location.hostname.endsWith(`.${h}`) || window.location.hostname.endsWith(h)
);

function App() {
  return (
    <FavoritesProvider>
    <div className="App">
      <BrowserRouter>
        <BackButton />
        <Routes>
          <Route path="/" element={isCustomDomain ? <TenantPage domainMode /> : <LandingPage />} />
          <Route path="/offres" element={<OffersPage />} />
          <Route path="/connexion" element={<LoginPage />} />
          <Route path="/admin/connexion" element={<AdminLoginPage />} />
          <Route path="/inscription" element={<RedirectInscription />} />
          <Route path="/tarifs" element={<PricingPage />} />
          <Route path="/messages" element={<MessagesPage />} />
          <Route path="/signature-partenariat" element={<PartnerSignPage />} />
          <Route path="/pricing" element={<PricingPage />} />
          <Route path="/auth/callback" element={<AuthCallbackPage />} />
          <Route path="/auth/google/return" element={<GoogleAuthReturnPage />} />
          <Route path="/admin/stripe-reconciliation" element={<StripeReconciliationPage />} />
          <Route path="/admin/ged-bridge" element={<GedBridgeAdminPage />} />
          <Route path="/admin/finance-bridge" element={<FinanceBridgeAdminPage />} />
          <Route path="/admin/connecteurs" element={<ConnectorsAdminPage />} />
          <Route path="/logiscop" element={<LogiscopPage />} />
          <Route path="/logicoop" element={<LogicoopSpacePage />} />
          <Route path="/oscop" element={<OscopPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/mot-de-passe-oublie" element={<ForgotPasswordPage />} />
          <Route path="/reinitialiser-mot-de-passe" element={<ResetPasswordPage />} />
          <Route path="/statistiques" element={<StatsPage />} />
          <Route path="/admin" element={<AdminPage />} />
          <Route path="/admin-v2" element={<AdminV2Page />} />
          <Route path="/onboarding" element={<OnboardingPage />} />
          <Route path="/adhesion" element={<OnboardingPage />} />
          <Route path="/catalogue" element={<CatalogPage />} />
          <Route path="/commandes" element={<OrdersPage />} />
          <Route path="/documents" element={<DocumentsPage />} />
          <Route path="/documents-legaux" element={<DocumentsPage />} />
          <Route path="/wallet" element={<WalletPage />} />
          <Route path="/mon-crediscop" element={<CrediscopStatementPage />} />
          <Route path="/zones" element={<WalletPage />} />
          {/* Legal Documents Routes */}
          <Route path="/legal" element={<LegalPage />} />
          <Route path="/legal/:docId" element={<LegalPage />} />
          {/* Order Preview with Stamp */}
          <Route path="/bon-de-commande" element={<OrderPreviewPage />} />
          <Route path="/order-preview" element={<OrderPreviewPage />} />
          {/* SMS Signature Demo */}
          <Route path="/signature" element={<SignatureDemoPage />} />
          <Route path="/signature-sms" element={<SignatureDemoPage />} />
          {/* Super Admin Dashboard */}
          <Route path="/super-admin" element={<SuperAdminPage />} />
          <Route path="/superadmin" element={<SuperAdminPage />} />
          <Route path="/t/:slug" element={<TenantPage />} />
          <Route path="/docs-api" element={<ApiDocsPage />} />
          <Route path="/espace-developpeur" element={<PartnerDevPage />} />
          {/* Dynamic Order Form with Zone Preparation Options */}
          <Route path="/bon-de-commande-dynamique" element={<DynamicOrderPage />} />
          <Route path="/dynamic-order" element={<DynamicOrderPage />} />
          {/* Vendor Space - Espace Vendeur */}
          <Route path="/espace-vendeur" element={<VendorSpacePage />} />
          <Route path="/espace-cooper" element={<CooperSpacePage />} />
          <Route path="/espace-expert" element={<ExpertSpacePage />} />
          <Route path="/changer-mot-de-passe" element={<ChangePasswordPage />} />
          <Route path="/kdmarche" element={<KdmarchePage />} />
          <Route path="/contact" element={<SupportContactPage />} />
          <Route path="/support" element={<SupportContactPage />} />
          <Route path="/partenariat" element={<PartnershipPage />} />
          <Route path="/vendor" element={<VendorSpacePage />} />
          {/* Admin Products Validation */}
          <Route path="/admin/produits" element={<AdminProductsPage />} />
          <Route path="/admin/products" element={<AdminProductsPage />} />
          {/* Buyer Space - Espace Acheteur Pro */}
          <Route path="/espace-acheteur" element={<BuyerSpacePage />} />
          <Route path="/buyer" element={<BuyerSpacePage />} />
          <Route path="/mon-espace" element={<BuyerSpacePage />} />
          {/* Checkout with Dynamic Order & Signature */}
          <Route path="/checkout" element={<CheckoutPage />} />
          <Route path="/paiement" element={<CheckoutPage />} />
          {/* Product Card Demo */}
          <Route path="/fiche-produit" element={<ProductCardDemoPage />} />
          <Route path="/product-card" element={<ProductCardDemoPage />} />
          {/* Notifications History */}
          <Route path="/notifications" element={<NotificationsHistoryPage />} />
          <Route path="/assistant-ia" element={<AiChatPage />} />
          <Route path="/adhesion-vendeur" element={<VendorOnboardingPage />} />
          <Route path="/activation-vendeur" element={<VendorActivationPage />} />
          <Route path="/historique-notifications" element={<NotificationsHistoryPage />} />
          {/* Favorites */}
          <Route path="/favoris" element={<FavoritesPage />} />
          <Route path="/favorites" element={<FavoritesPage />} />
          <Route path="/alertes-favoris" element={<FavoriteAlertsPage />} />
          {/* Shopping Lists */}
          <Route path="/listes-achats" element={<ShoppingListsPage />} />
          <Route path="/shopping-lists" element={<ShoppingListsPage />} />
          <Route path="/listes-achats/:listId" element={<ShoppingListDetailPage />} />
          <Route path="/shopping-lists/:listId" element={<ShoppingListDetailPage />} />
          {/* Super Admin - Plans & Credits Management */}
          <Route path="/admin/plans" element={<AdminPlansPage />} />
          <Route path="/admin/plans-credits" element={<AdminPlansPage />} />
          {/* ====================================================== */}
          {/* LOLODRIVE by O'SCOP — 7 modules                           */}
          {/* ====================================================== */}
          <Route path="/lolodrive" element={<LolodriveAdminDashboardPage />} />
          <Route path="/lolodrive/dashboard" element={<LolodriveAdminDashboardPage />} />
          <Route path="/pass" element={<PassSpacePage />} />
          <Route path="/espace-pass" element={<PassSpacePage />} />
          <Route path="/pos" element={<PosLolodrivePage />} />
          <Route path="/pos-lolodrive" element={<PosLolodrivePage />} />
          <Route path="/admin/lolo-points" element={<LoloPointsAdminPage />} />
          <Route path="/lolo-point/dashboard" element={<LoloPointManagerPage />} />
          <Route path="/gerant" element={<LoloPointManagerPage />} />
          <Route path="/admin/lolo-hour" element={<LoloHourAdminPage />} />
          <Route path="/crm" element={<CrmPartnersPage />} />
          <Route path="/crm-partenaires" element={<CrmPartnersPage />} />
          <Route path="/reporting-impact" element={<EssReportingPage />} />
          <Route path="/reporting-ess" element={<EssReportingPage />} />
          <Route path="/catalogue-lolodrive" element={<LolodriveCatalogPage />} />
          <Route path="/paiement/retour" element={<PaymentReturnPage />} />
          <Route path="/paiement/annule" element={<PaymentReturnPage />} />
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" richColors />
    </div>
    </FavoritesProvider>
  );
}

export default App;
