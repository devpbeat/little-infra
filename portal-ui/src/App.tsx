import { Route, Routes } from "react-router-dom";
import { AdminProductsPage } from "./pages/AdminProductsPage";
import { CheckoutPage } from "./pages/CheckoutPage";
import { DashboardPage } from "./pages/DashboardPage";
import { LandingPage } from "./pages/LandingPage";
import { LoginPage } from "./pages/LoginPage";
import { ProductDetailPage } from "./pages/ProductDetailPage";
import "./styles/portal.css";

function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/products/:slug" element={<ProductDetailPage />} />
      <Route path="/dashboard" element={<DashboardPage />} />
      <Route path="/admin/products" element={<AdminProductsPage />} />
      <Route path="/checkout" element={<CheckoutPage />} />
    </Routes>
  );
}

export default App;
