import { createContext, useContext, useState, useCallback, ReactNode } from 'react'

interface UserContextType {
  userId: number
  setUserId: (id: number) => void
  isAuthenticated: boolean
}

const UserContext = createContext<UserContextType | undefined>(undefined)

interface UserProviderProps {
  children: ReactNode
}

export function UserProvider({ children }: UserProviderProps) {
  // For MVP, we use a hardcoded user ID of 1
  // This can be replaced with actual authentication in v2+
  const [userId, setUserIdState] = useState<number>(() => {
    const stored = localStorage.getItem('userId')
    return stored ? parseInt(stored, 10) : 1
  })

  const setUserId = useCallback((id: number) => {
    setUserIdState(id)
    localStorage.setItem('userId', id.toString())
  }, [])

  const value: UserContextType = {
    userId,
    setUserId,
    isAuthenticated: userId > 0,
  }

  return <UserContext.Provider value={value}>{children}</UserContext.Provider>
}

export function useUser(): UserContextType {
  const context = useContext(UserContext)
  if (context === undefined) {
    throw new Error('useUser must be used within a UserProvider')
  }
  return context
}

export function useUserId(): number {
  const { userId } = useUser()
  return userId
}
