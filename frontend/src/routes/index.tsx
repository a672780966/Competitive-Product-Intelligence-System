// CPIS V1 — Route configuration

import AdminLayout from "../components/Layout";
import TaskListPage from "../features/tasks/TaskList";
import TaskDetailPage from "../features/tasks/TaskDetail";
import ProductListPage from "../features/products/ProductList";
import ReviewListPage from "../features/reviews/ReviewList";
import ReviewDetailPage from "../features/reviews/ReviewDetail";
import SyncRecordsPage from "../features/sync/SyncRecords";
import ReportPage from "../features/reports/ReportPage";

export const routes = [
  {
    path: "/",
    element: <AdminLayout />,
    children: [
      { index: true, element: <TaskListPage /> },
      { path: "tasks", element: <TaskListPage /> },
      { path: "tasks/:id", element: <TaskDetailPage /> },
      { path: "products", element: <ProductListPage /> },
      { path: "products/:id", element: <ReviewDetailPage /> },  // placeholder
      { path: "reviews", element: <ReviewListPage /> },
      { path: "reviews/:versionId", element: <ReviewDetailPage /> },
      { path: "sync", element: <SyncRecordsPage /> },
      { path: "reports", element: <ReportPage /> },
    ],
  },
];
