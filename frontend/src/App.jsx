import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
import Layout from "./components/Layout";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import DashboardPage from "./pages/DashboardPage";
import ResumesPage from "./pages/ResumesPage";
import ResumeDetailPage from "./pages/ResumeDetailPage";
import JobMatchingPage from "./pages/Jobmatchingpage";
import ResumeScorePage from "./pages/ResumeScorePage";
import SkillGapPage from "./pages/SkillGapPage";
import ProfilePage from "./pages/ProfilePage";
import AdminAccessPage from "./pages/AdminAccessPage";
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
        path="/profile"
        element={
          <ProtectedRoute>
            <Layout><ProfilePage /></Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/analytics"
        element={
          <ProtectedRoute requiredRole="admin">
            <Layout><AdminAccessPage /></Layout>
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
<Route
  path="/skill-gap"
  element={
    <ProtectedRoute>
      <Layout><SkillGapPage /></Layout>
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