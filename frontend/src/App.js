import { useEffect } from "react";
import "./App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "./components/ui/sonner";

// Pages
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
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
import LegalPage from "./pages/LegalPage";
import OrderPreviewPage from "./pages/OrderPreviewPage";
import SignatureDemoPage from "./pages/SignatureDemoPage";
import SuperAdminPage from "./pages/SuperAdminPage";
import DynamicOrderPage from "./pages/DynamicOrderPage";
import VendorSpacePage from "./pages/VendorSpacePage";
import AdminProductsPage from "./pages/AdminProductsPage";
import BuyerSpacePage from "./pages/BuyerSpacePage";
import CheckoutPage from "./pages/CheckoutPage";
import ProductCardDemoPage from "./pages/ProductCardDemoPage";
import NotificationsHistoryPage from "./pages/NotificationsHistoryPage";
import FavoritesPage from "./pages/FavoritesPage";
import ShoppingListsPage from "./pages/ShoppingListsPage";
import ShoppingListDetailPage from "./pages/ShoppingListDetailPage";
import AdminPlansPage from "./pages/AdminPlansPage";
import { FavoritesProvider } from "./components/FavoriteButton";

// LOLODRIVE by O'SCOP - 7 nouvelles pages
import LolodriveAdminDashboardPage from "./pages/LolodriveAdminDashboardPage";
import PassSpacePage from "./pages/PassSpacePage";
import PosLolodrivePage from "./pages/PosLolodrivePage";
import LoloPointsAdminPage from "./pages/LoloPointsAdminPage";
import LoloHourAdminPage from "./pages/LoloHourAdminPage";
import CrmPartnersPage from "./pages/CrmPartnersPage";
import EssReportingPage from "./pages/EssReportingPage";
import LolodriveCatalogPage from "./pages/LolodriveCatalogPage";

function App() {
  return (
    <FavoritesProvider>
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/offres" element={<OffersPage />} />
          <Route path="/connexion" element={<LoginPage />} />
          <Route path="/inscription" element={<RegisterPage />} />
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
          {/* Dynamic Order Form with Zone Preparation Options */}
          <Route path="/bon-de-commande-dynamique" element={<DynamicOrderPage />} />
          <Route path="/dynamic-order" element={<DynamicOrderPage />} />
          {/* Vendor Space - Espace Vendeur */}
          <Route path="/espace-vendeur" element={<VendorSpacePage />} />
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
          <Route path="/historique-notifications" element={<NotificationsHistoryPage />} />
          {/* Favorites */}
          <Route path="/favoris" element={<FavoritesPage />} />
          <Route path="/favorites" element={<FavoritesPage />} />
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
          <Route path="/admin/lolo-hour" element={<LoloHourAdminPage />} />
          <Route path="/crm" element={<CrmPartnersPage />} />
          <Route path="/crm-partenaires" element={<CrmPartnersPage />} />
          <Route path="/reporting-impact" element={<EssReportingPage />} />
          <Route path="/reporting-ess" element={<EssReportingPage />} />
          <Route path="/catalogue-lolodrive" element={<LolodriveCatalogPage />} />
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" richColors />
    </div>
    </FavoritesProvider>
  );
}

export default App;
