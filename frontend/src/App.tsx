import { Routes, Route } from "react-router-dom";
import { Layout } from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Mapping from "./pages/Mapping";
import Arbs from "./pages/Arbs";
import ArbDetail from "./pages/ArbDetail";
import Events from "./pages/Events";
import EventDetail from "./pages/EventDetail";

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/mapping" element={<Mapping />} />
        <Route path="/arbs" element={<Arbs />} />
        <Route path="/arbs/:id" element={<ArbDetail />} />
        <Route path="/events" element={<Events />} />
        <Route path="/events/:id" element={<EventDetail />} />
      </Routes>
    </Layout>
  );
}

export default App;

