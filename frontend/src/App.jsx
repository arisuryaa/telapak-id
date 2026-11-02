import { BrowserRouter, Navigate, NavLink, Route, Routes } from "react-router";
import Scan from "./pages/Scan.jsx";
import Result from "./pages/Result.jsx";
import PersonDetail from "./pages/PersonDetail.jsx";
import Register from "./pages/Register.jsx";
import RegisteredData from "./pages/RegisteredData.jsx";

const linkClass = ({ isActive }) =>
  `rounded-md px-3 py-2 text-sm font-medium ${
    isActive ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-200"
  }`;

export default function App() {
  return (
    <BrowserRouter>
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
          <span className="font-semibold">Telapak ID</span>
          <nav className="flex gap-2">
            <NavLink to="/" end className={linkClass}>Scan</NavLink>
            <NavLink to="/daftar" className={linkClass}>Daftar</NavLink>
            <NavLink to="/data" className={linkClass}>Data terdaftar</NavLink>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-6">
        <Routes>
          <Route path="/" element={<Scan />} />
          <Route path="/hasil" element={<Result />} />
          <Route path="/orang/:id" element={<PersonDetail />} />
          <Route path="/daftar" element={<Register />} />
          <Route path="/data" element={<RegisteredData />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </BrowserRouter>
  );
}
