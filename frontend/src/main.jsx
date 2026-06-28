import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// Remove the static HTML splash screen once React has taken over
const splash = document.getElementById("root-splash");
if (splash) splash.remove();
