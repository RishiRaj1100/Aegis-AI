import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import "./index.css";
import { installDevRouteTimingHooks } from "@/utils/routeTiming";

installDevRouteTimingHooks();

createRoot(document.getElementById("root")!).render(<App />);
