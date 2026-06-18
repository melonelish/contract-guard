import { App as AntApp } from "antd";
import { Navigate, Route, Routes } from "react-router-dom";

import { AppLayout } from "./components/Layout/AppLayout";
import { LoginPage } from "./pages/Login";
import { ContractDetailPage } from "./pages/ContractDetailPage";
import { ContractListPage } from "./pages/ContractListPage";
import { useAuthStore } from "./stores/auth";

function ProtectedRoute({ children }: { children: JSX.Element }) {
  const token = useAuthStore((state) => state.token);
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

export default function App() {
  return (
    <AntApp>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <AppLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<ContractListPage />} />
          <Route path="contracts/:id" element={<ContractDetailPage />} />
        </Route>
      </Routes>
    </AntApp>
  );
}
