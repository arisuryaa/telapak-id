import { BrowserRouter, Link, Navigate, NavLink, Route, Routes } from "react-router";
import Scan from "./pages/Scan.jsx";
import Result from "./pages/Result.jsx";
import PersonDetail from "./pages/PersonDetail.jsx";
import Register from "./pages/Register.jsx";
import RegisteredData from "./pages/RegisteredData.jsx";
import { IkonTangan, tombol } from "./components/ui.jsx";

const linkClass = ({ isActive }) =>
  `rounded-full px-4 py-2 text-sm font-semibold transition-colors ${
    isActive ? "bg-brand-soft text-brand" : "text-muted hover:text-ink"
  }`;

export default function App() {
  return (
    <BrowserRouter>
      <div className="latar-grid pointer-events-none fixed inset-x-0 top-0 -z-10 h-[520px]" aria-hidden="true" />
      <header className="mx-auto max-w-6xl px-4 pt-4">
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-full border border-white bg-white/90 py-2 pr-2 pl-5 shadow-card backdrop-blur">
          <Link to="/" className="flex items-center gap-2 text-lg font-extrabold tracking-tight text-ink">
            <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-brand text-white">
              <IkonTangan className="h-5 w-5" />
            </span>
            Telapak ID
          </Link>
          <nav className="order-3 flex w-full justify-center gap-1 sm:order-none sm:w-auto">
            <NavLink to="/" end className={linkClass}>Scan</NavLink>
            <NavLink to="/data" className={linkClass}>Data terdaftar</NavLink>
          </nav>
          <NavLink to="/daftar" className={tombol.utama}>Daftarkan telapak</NavLink>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 pt-10 pb-16">
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
