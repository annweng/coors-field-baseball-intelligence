import { Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import CoorsLabPage from "./pages/CoorsLabPage";
import DataPage from "./pages/DataPage";
import ForecastsPage from "./pages/ForecastsPage";
import ModelLabPage from "./pages/ModelLabPage";
import OverviewPage from "./pages/OverviewPage";
import RunsPage from "./pages/RunsPage";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<OverviewPage />} />
        <Route path="/forecasts" element={<ForecastsPage />} />
        <Route path="/coors" element={<CoorsLabPage />} />
        <Route path="/runs" element={<RunsPage />} />
        <Route path="/models" element={<ModelLabPage />} />
        <Route path="/data" element={<DataPage />} />
      </Route>
    </Routes>
  );
}
