import { App as AntApp } from "antd";
import { Navigate, Route, Routes } from "react-router-dom";

import { AppLayout } from "./components/Layout/AppLayout";
import { HomePage } from "./pages/HomePage";
import { LoginPage } from "./pages/Login";
import { ContractDetailPage } from "./pages/ContractDetailPage";
import { ContractListPage } from "./pages/ContractListPage";
import { ReviewReportPage } from "./pages/ReviewReportPage";
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
        <Route path="/" element={<HomePage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/workspace"
          element={
            <ProtectedRoute>
              <AppLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<ContractListPage />} />
        </Route>
        <Route
          path="/contracts/:id"
          element={
            <ProtectedRoute>
              <AppLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<ContractDetailPage />} />
        </Route>
        <Route
          path="/reviews/:id"
          element={
            <ProtectedRoute>
              <AppLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<ReviewReportPage />} />
        </Route>
      </Routes>
    </AntApp>
  );
}
