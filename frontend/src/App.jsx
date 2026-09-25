import { useEffect, useState } from 'react';
import { NavLink, Route, Routes } from 'react-router-dom';
import api from './services/api';
import FileUpload from './components/FileUpload';
import DashboardPage from './pages/DashboardPage';
import ResumePage from './pages/ResumePage';
import JobsPage from './pages/JobsPage';
import SkillsPage from './pages/SkillsPage';
import ProfilePage from './pages/ProfilePage';
import './App.css';

const navItems = [
  { label: 'Dashboard', path: '/' },
  { label: 'Resume', path: '/resume' },
  { label: 'Jobs', path: '/jobs' },
  { label: 'Skills', path: '/skills' },
  { label: 'Profile', path: '/profile' },
];

function App() {
  const [backendStatus, setBackendStatus] = useState({ loading: true, online: false, message: 'Checking backend...' });

  useEffect(() => {
    const checkBackend = async () => {
      try {
        const response = await api.get('/');
        setBackendStatus({
          loading: false,
          online: true,
          message: response?.data?.message || 'Backend connected successfully',
        });
      } catch (error) {
        setBackendStatus({
          loading: false,
          online: false,
          message: 'Backend unavailable. Start the FastAPI server on port 8000.',
        });
      }
    };

    checkBackend();
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 text-slate-700">
      <div className="mx-auto flex min-h-screen max-w-7xl flex-col lg:flex-row">
        <aside className="w-full bg-slate-900 p-6 text-slate-200 lg:w-72">
          <div className="mb-8 flex items-center gap-3 border-b border-slate-700 pb-5">
            <div className="grid h-11 w-11 place-items-center rounded-xl bg-gradient-to-br from-blue-500 to-violet-500 font-bold text-white">
              DS
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Project</p>
              <h2 className="mt-1 text-xl font-semibold text-white">Resume AI</h2>
            </div>
          </div>

          <nav className="space-y-2" aria-label="Main navigation">
            {navItems.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                end={item.path === '/'}
                className={({ isActive }) =>
                  `block rounded-xl px-4 py-3 text-left text-sm font-medium transition ${
                    isActive
                      ? 'bg-blue-500/15 text-white shadow-inner shadow-blue-500/20'
                      : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </aside>

        <main className="flex-1 p-5 sm:p-8 lg:p-10">
          <header className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-[10px] uppercase tracking-[0.2em] text-slate-500">Welcome back</p>
              <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
                Data Science Project Dashboard
              </h1>
            </div>

            <div
              className={`inline-flex items-center rounded-full border px-3 py-2 text-xs font-semibold ${
                backendStatus.online
                  ? 'border-green-200 bg-green-100 text-green-700'
                  : 'border-red-200 bg-red-100 text-red-700'
              }`}
            >
              {backendStatus.loading ? 'Checking backend...' : backendStatus.online ? 'Backend online' : 'Backend offline'}
            </div>
          </header>

          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/resume" element={<ResumePage />} />
            <Route path="/jobs" element={<JobsPage />} />
            <Route path="/skills" element={<SkillsPage />} />
            <Route path="/profile" element={<ProfilePage />} />
          </Routes>

          <section className="mt-8 grid gap-5 xl:grid-cols-[2fr_1fr]">
            <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm shadow-slate-200/60">
              <h3 className="mb-3 text-lg font-semibold text-slate-900">AI Resume Workflow</h3>
              <p className="mb-5 text-sm text-slate-600">
                Upload the resume, analyze the profile, match it with jobs, and review recommendation insights in one place.
              </p>
              <FileUpload />
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm shadow-slate-200/60">
              <h3 className="mb-3 text-lg font-semibold text-slate-900">Quick Actions</h3>
              <ul className="space-y-2 text-sm text-slate-600">
                <li>• Upload resume PDF</li>
                <li>• Analyze profile</li>
                <li>• View job matches</li>
                <li>• Track skill gaps</li>
              </ul>
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}

export default App;
