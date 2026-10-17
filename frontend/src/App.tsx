import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { ConnectionProvider } from "./context/ConnectionContext";
import { Layout } from "./components/Layout";
import { Connect } from "./pages/Connect";
import { Schema } from "./pages/Schema";
import { Ask } from "./pages/Ask";

const qc = new QueryClient();

export default function App() {
  return (
    <QueryClientProvider client={qc}>
      <ConnectionProvider>
        <BrowserRouter>
          <Layout>
            <Routes>
              <Route path="/" element={<Navigate to="/connect" replace />} />
              <Route path="/connect" element={<Connect />} />
              <Route path="/schema" element={<Schema />} />
              <Route path="/ask" element={<Ask />} />
            </Routes>
          </Layout>
        </BrowserRouter>
      </ConnectionProvider>
    </QueryClientProvider>
  );
}