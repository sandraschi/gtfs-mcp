import {
  Navigate,
  Route,
  BrowserRouter as Router,
  Routes,
  useLocation,
} from "react-router-dom";
import { ErrorBoundary } from "@/components/error-boundary";
import { AppLayout } from "@/components/layout/app-layout";
import { Chat } from "@/pages/chat";
import { Dashboard } from "@/pages/dashboard";
import { Feeds } from "@/pages/feeds";
import { Help } from "@/pages/help";
import Logging from "@/pages/Logging";
import { Lines } from "@/pages/lines";
import { Settings } from "@/pages/settings";
import { Skills } from "@/pages/skills";
import { Sources } from "@/pages/sources";
import { Stops } from "@/pages/stops";
import { Tools } from "@/pages/tools";

function AppRoutes() {
  // Keyed by path: navigating away resets a tripped boundary so one bad
  // page can never trap the whole app in the error fallback.
  const { pathname } = useLocation();
  return (
    <ErrorBoundary key={pathname}>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/sources" element={<Sources />} />
        <Route path="/feeds" element={<Feeds />} />
        <Route path="/stops" element={<Stops />} />
        <Route path="/lines" element={<Lines />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/tools" element={<Tools />} />
        <Route path="/skills" element={<Skills />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/logging" element={<Logging />} />
        <Route path="/help" element={<Help />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </ErrorBoundary>
  );
}

function App() {
  return (
    <Router>
      <AppLayout>
        <AppRoutes />
      </AppLayout>
    </Router>
  );
}

export default App;
