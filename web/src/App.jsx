import { useEffect, useState } from "react";
import { api, auth } from "./api.js";
import AuthScreen from "./AuthScreen.jsx";
import Board from "./Board.jsx";

export default function App() {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);

  // Restore session on load if a token is present.
  useEffect(() => {
    if (!auth.token) {
      setReady(true);
      return;
    }
    api
      .me()
      .then(setUser)
      .catch(() => auth.clear())
      .finally(() => setReady(true));
  }, []);

  function handleLogout() {
    auth.clear();
    setUser(null);
  }

  if (!ready) {
    return (
      <div className="splash">
        <span className="logo-mark">📋</span>
      </div>
    );
  }

  return user ? (
    <Board user={user} onLogout={handleLogout} onUserUpdate={setUser} />
  ) : (
    <AuthScreen onAuthenticated={setUser} />
  );
}
