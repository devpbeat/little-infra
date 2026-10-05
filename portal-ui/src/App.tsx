import { Route, Routes } from "react-router-dom";
import { RequireAuth, RequireStaff } from "./components/auth/RouteGuards";
import { AdminProductsPage } from "./pages/AdminProductsPage";
import { CheckoutPage } from "./pages/CheckoutPage";
import { DashboardPage } from "./pages/DashboardPage";
import { LandingPage } from "./pages/LandingPage";
import { LoginPage } from "./pages/LoginPage";
import { ProductDetailPage } from "./pages/ProductDetailPage";
import { SignupPage } from "./pages/SignupPage";
import "./styles/portal.css";

function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      {/* Clerk path-based routing needs a catch-all so its internal
          sub-steps (verification, SSO callback, etc.) stay on this route. */}
      <Route path="/login/*" element={<LoginPage />} />
      <Route path="/signup/*" element={<SignupPage />} />
      <Route path="/products/:slug" element={<ProductDetailPage />} />
      <Route
        path="/dashboard"
        element={
          <RequireAuth>
            <DashboardPage />
          </RequireAuth>
        }
      />
      <Route
        path="/admin/products"
        element={
          <RequireAuth>
            <RequireStaff>
              <AdminProductsPage />
            </RequireStaff>
          </RequireAuth>
        }
      />
      <Route
        path="/checkout"
        element={
          <RequireAuth>
            <CheckoutPage />
          </RequireAuth>
        }
      />
    </Routes>
  );
}

export default App;
