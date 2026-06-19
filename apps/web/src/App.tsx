import { Outlet } from "react-router-dom";
import NavBar from "./components/NavBar";
import LoginPage from "./pages/LoginPage";
import { useAuth } from "./context/AuthContext";

export default function App() {
  const { status } = useAuth();

  if (status === "loading") {
    return (
      <div className="grid min-h-full place-items-center bg-brink-ink text-sm text-brink-mute">
        Loading…
      </div>
    );
  }

  if (status !== "authenticated") {
    return <LoginPage />;
  }

  return (
    <div className="min-h-full bg-brink-ink text-brink-text">
      <NavBar />
      <main className="mx-auto max-w-3xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}
