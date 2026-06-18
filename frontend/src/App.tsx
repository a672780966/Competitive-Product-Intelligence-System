import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import AdminLayout from "./components/Layout";
import LoginPage from "./features/auth/LoginPage";
import TaskListPage from "./features/tasks/TaskList";
import TaskDetailPage from "./features/tasks/TaskDetail";
import ProductListPage from "./features/products/ProductList";
import ProductDetailPage from "./features/products/ProductDetail";
import ReviewListPage from "./features/reviews/ReviewList";
import ReviewDetailPage from "./features/reviews/ReviewDetail";
import SyncRecordsPage from "./features/sync/SyncRecords";
import ReportPage from "./features/reports/ReportPage";
import { isAuthenticated } from "./api/auth";

/** Redirects unauthenticated users to /login, preserving intended location. */
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  if (!isAuthenticated()) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  return <>{children}</>;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<ProtectedRoute><AdminLayout /></ProtectedRoute>}>
          <Route index element={<Navigate to="/tasks" replace />} />
          <Route path="tasks" element={<TaskListPage />} />
          <Route path="tasks/:id" element={<TaskDetailPage />} />
          <Route path="products" element={<ProductListPage />} />
          <Route path="products/:id" element={<ProductDetailPage />} />
          <Route path="reviews" element={<ReviewListPage />} />
          <Route path="reviews/:versionId" element={<ReviewDetailPage />} />
          <Route path="sync" element={<SyncRecordsPage />} />
          <Route path="reports" element={<ReportPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
