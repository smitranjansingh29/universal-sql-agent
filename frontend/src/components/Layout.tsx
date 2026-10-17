import { Link, useLocation } from "react-router-dom";
import { useConnection } from "../context/useConnection";
export function Layout({ children }: { children: React.ReactNode }) {
  const { active } = useConnection();
  const loc = useLocation();

  const link = (to: string, label: string) => {
    const isActive = loc.pathname === to;
    return (
      <Link
        to={to}
        className={`px-3 py-1.5 rounded text-sm font-medium ${
          isActive ? "bg-blue-600 text-white" : "text-gray-700 hover:bg-gray-200"
        }`}
      >
        {label}
      </Link>
    );
  };

  return (
    <div className="min-h-screen">
      <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center gap-4">
        <div className="font-semibold text-lg">Universal SQL Agent</div>
        <nav className="flex gap-1">
          {link("/connect", "Connect")}
          {link("/schema", "Schema")}
          {link("/ask", "Ask")}
        </nav>
        <div className="ml-auto text-sm text-gray-600">
          {active ? (
            <>
              Active: <span className="font-medium">{active.name}</span>{" "}
              <span className="text-gray-400">({active.dialect})</span>
            </>
          ) : (
            <span className="text-amber-600">No connection</span>
          )}
        </div>
      </header>
      <main className="max-w-6xl mx-auto p-6">{children}</main>
    </div>
  );
}