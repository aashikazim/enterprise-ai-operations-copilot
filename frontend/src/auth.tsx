import {createContext, useContext, useState, type ReactNode} from 'react'
import {ApiClient, type User} from './api'
interface Auth { user: User | null; api: ApiClient; login(email: string, password: string): Promise<void>; logout(): void }
const Context = createContext<Auth | null>(null)
export function AuthProvider({children}: {children: ReactNode}) {
  const [user, setUser] = useState<User | null>(null)
  const [api] = useState(() => new ApiClient())
  api.onUnauthorized = () => setUser(null)
  return <Context.Provider value={{user, api, login: async (email, password) => {setUser(await api.login(email, password))}, logout: () => {api.setToken(null); setUser(null)}}}>{children}</Context.Provider>
}
export function useAuth() { const value = useContext(Context); if (!value) throw new Error('Auth context unavailable'); return value }
