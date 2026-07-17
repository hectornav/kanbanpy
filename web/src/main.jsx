import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import { LangProvider } from "./i18n.jsx";
import "./styles.css";

// Apply the saved theme + language before first paint to avoid a flash.
document.documentElement.dataset.appTheme = localStorage.getItem("kanban.theme") || "nocturne";
document.documentElement.lang = localStorage.getItem("kanban.lang") || "es";

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <LangProvider>
      <App />
    </LangProvider>
  </React.StrictMode>
);
