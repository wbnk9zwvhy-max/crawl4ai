import { createContext, useContext, useState } from "react";

const DEFAULT_EMAIL = "rgimeno32@gmail.com";
const STORAGE_KEY = "preciofacil.user_email";

function readStoredEmail() {
  try {
    return localStorage.getItem(STORAGE_KEY) || DEFAULT_EMAIL;
  } catch {
    return DEFAULT_EMAIL;
  }
}

const UserContext = createContext({ userEmail: DEFAULT_EMAIL, setUserEmail: () => {} });

export function UserProvider({ children }) {
  const [userEmail, setUserEmailState] = useState(readStoredEmail);

  const setUserEmail = (email) => {
    setUserEmailState(email);
    try {
      localStorage.setItem(STORAGE_KEY, email);
    } catch {
      /* almacenamiento no disponible, seguimos solo en memoria */
    }
  };

  return (
    <UserContext.Provider value={{ userEmail, setUserEmail }}>{children}</UserContext.Provider>
  );
}

export function useUser() {
  return useContext(UserContext);
}
