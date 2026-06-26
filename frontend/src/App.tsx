import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import AdminLayout from "./components/Layout";
import TaskListPage from "./features/tasks/TaskList";
import TaskDetailPage from "./features/tasks/TaskDetail";
import ProductListPage from "./features/products/ProductList";
import ProductDetailPage from "./features/products/ProductDetail";
import ReviewListPage from "./features/reviews/ReviewList";
import ReviewDetailPage from "./features/reviews/ReviewDetail";
import SyncRecordsPage from "./features/sync/SyncRecords";
import ReportPage from "./features/reports/ReportPage";
import DiscoveryPage from "./features/discovery/DiscoveryPage";
import TemplatesPage from "./features/collection-templates/TemplatesPage";
import TemplateDetailPage from "./features/collection-templates/TemplateDetail";
import UsagePage from "./features/usage/UsagePage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AdminLayout />}>
          <Route index element={<Navigate to="/tasks" replace />} />
          <Route path="tasks" element={<TaskListPage />} />
          <Route path="tasks/:id" element={<TaskDetailPage />} />
          <Route path="products" element={<ProductListPage />} />
          <Route path="products/:id" element={<ProductDetailPage />} />
          <Route path="reviews" element={<ReviewListPage />} />
          <Route path="reviews/:versionId" element={<ReviewDetailPage />} />
          <Route path="sync" element={<SyncRecordsPage />} />
          <Route path="reports" element={<ReportPage />} />
          <Route path="discovery" element={<DiscoveryPage />} />
          <Route path="collection-templates" element={<TemplatesPage />} />
          <Route path="collection-templates/:id" element={<TemplateDetailPage />} />
          <Route path="usage" element={<UsagePage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
