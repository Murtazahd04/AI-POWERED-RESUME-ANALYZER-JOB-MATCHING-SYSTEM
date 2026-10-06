import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
import Layout from "./components/Layout";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import DashboardPage from "./pages/DashboardPage";
import ResumesPage from "./pages/ResumesPage";
import ResumeDetailPage from "./pages/ResumeDetailPage";
import JobMatchingPage from "./pages/JobMatchingPage";
import ResumeScorePage from "./pages/ResumeScorePage";
function RootRedirect() {
  const { user, loading } = useAuth();
  if (loading) return null;
  return <Navigate to={user ? "/dashboard" : "/login"} replace />;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<RootRedirect />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Layout><DashboardPage /></Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/resumes"
        element={
          <ProtectedRoute>
            <Layout><ResumesPage /></Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/resumes/:id"
        element={
          <ProtectedRoute>
            <Layout><ResumeDetailPage /></Layout>
          </ProtectedRoute>
        }
      />
      <Route
  path="/job-matching"
  element={
    <ProtectedRoute>
      <JobMatchingPage />
    </ProtectedRoute>
  }
/>
<Route
  path="/resume-score"
  element={
    <ProtectedRoute>
      <ResumeScorePage />
    </ProtectedRoute>
  }
/>
    </Routes>
    
  );
  
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  );
}  