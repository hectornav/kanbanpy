import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import "./styles.css";

// Apply the saved theme before first paint to avoid a flash.
document.documentElement.dataset.appTheme = localStorage.getItem("kanban.theme") || "nocturne";

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
