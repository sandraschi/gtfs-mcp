import {
  Navigate,
  Route,
  BrowserRouter as Router,
  Routes,
} from "react-router-dom";
import { AppLayout } from "@/components/layout/app-layout";
import { Chat } from "@/pages/chat";
import { Dashboard } from "@/pages/dashboard";
import { Feeds } from "@/pages/feeds";
import { Help } from "@/pages/help";
import Logging from "@/pages/Logging";
import { Settings } from "@/pages/settings";
import { Skills } from "@/pages/skills";
import { Stops } from "@/pages/stops";
import { Tools } from "@/pages/tools";

function App() {
  return (
    <Router>
      <AppLayout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/feeds" element={<Feeds />} />
          <Route path="/stops" element={<Stops />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/tools" element={<Tools />} />
          <Route path="/skills" element={<Skills />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/logging" element={<Logging />} />
          <Route path="/help" element={<Help />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AppLayout>
    </Router>
  );
}

export default App;
