import { NavLink } from "react-router-dom";
import { Headphones, User, Mic2, TrendingUp, BarChart3, LogOut } from "lucide-react";
import { useAuth } from "../context/AuthContext";

const linkBase =
  "flex items-center gap-2 rounded-full px-3 py-2 text-sm font-medium transition";
const linkIdle = "text-brink-mute hover:text-brink-text";
const linkActive = "bg-brink-panel text-brink-text";

export default function NavBar() {
  const { profile, logout } = useAuth();
  const avatar = profile?.images?.[0]?.url;

  return (
    <header className="sticky top-0 z-10 border-b border-brink-line bg-brink-ink/80 backdrop-blur">
      <div className="mx-auto flex max-w-3xl items-center justify-between gap-2 px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="text-xl font-bold tracking-tight text-brink-accent">
            brink
          </span>
        </div>
        <nav className="flex items-center gap-1">
          <NavLink
            to="/feed"
            className={({ isActive }) => `${linkBase} ${isActive ? linkActive : linkIdle}`}
          >
            <Headphones size={16} /> Feed
          </NavLink>
          <NavLink
            to="/profile/me"
            className={({ isActive }) => `${linkBase} ${isActive ? linkActive : linkIdle}`}
          >
            <User size={16} /> Profile
          </NavLink>
          <NavLink
            to="/artist"
            className={({ isActive }) => `${linkBase} ${isActive ? linkActive : linkIdle}`}
          >
            <Mic2 size={16} /> Artist
          </NavLink>
          <NavLink
            to="/predict"
            className={({ isActive }) => `${linkBase} ${isActive ? linkActive : linkIdle}`}
          >
            <TrendingUp size={16} /> Predict
          </NavLink>
          <NavLink
            to="/analytics"
            className={({ isActive }) => `${linkBase} ${isActive ? linkActive : linkIdle}`}
          >
            <BarChart3 size={16} /> Analytics
          </NavLink>
        </nav>
        <div className="flex items-center gap-2">
          {avatar ? (
            <img
              src={avatar}
              alt={profile?.display_name ?? "profile"}
              className="h-8 w-8 rounded-full border border-brink-line object-cover"
            />
          ) : (
            <div className="h-8 w-8 rounded-full bg-gradient-to-br from-brink-accent to-brink-hot" />
          )}
          <button
            onClick={logout}
            title="Log out"
            className="rounded-full p-2 text-brink-mute hover:bg-brink-panel hover:text-brink-text"
          >
            <LogOut size={16} />
          </button>
        </div>
      </div>
    </header>
  );
}
