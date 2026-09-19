import { Route, Routes } from "react-router-dom";
import { AppLayout } from "./components/ui/AppLayout";
import { OverviewPage } from "./pages/OverviewPage";
import { AppsKeysPage } from "./pages/AppsKeysPage";
import { CustomersListPage } from "./pages/CustomersListPage";
import { CustomerDetailPage } from "./pages/CustomerDetailPage";
import { CustomerSignupPage } from "./pages/CustomerSignupPage";
import { ContractTemplatesPage } from "./pages/ContractTemplatesPage";
import { PaymentDetailPage } from "./pages/PaymentDetailPage";
import { PaymentResultPage } from "./pages/PaymentResultPage";
import { LoginPage } from "./pages/LoginPage";
import { ContractSignPage } from "./pages/ContractSignPage";
import { RequireAuth } from "./auth/RequireAuth";
import "./styles/dashboard.css";

function App() {
  return (
    <Routes>
      {/* Public: Pagopar redirects the payer here after checkout. */}
      <Route path="/payments/result/:hash" element={<PaymentResultPage />} />
      {/* Public: click-to-sign ceremony, addressed by capability token. */}
      <Route path="/contracts/sign/:token" element={<ContractSignPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="*"
        element={
          <RequireAuth>
            <AppLayout>
              <Routes>
                <Route path="/" element={<OverviewPage />} />
                <Route path="/apps" element={<AppsKeysPage />} />
                <Route path="/customers" element={<CustomersListPage />} />
                <Route path="/customers/new" element={<CustomerSignupPage />} />
                <Route path="/customers/:customerId" element={<CustomerDetailPage />} />
                <Route path="/contract-templates" element={<ContractTemplatesPage />} />
                <Route path="/payments/:paymentId" element={<PaymentDetailPage />} />
              </Routes>
            </AppLayout>
          </RequireAuth>
        }
      />
    </Routes>
  );
}

export default App;
