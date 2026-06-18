import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface User {
  id: string
  email: string
  organization_id: string
  organization_name: string
  role: string
}

interface AuthState {
  token: string | null
  user: User | null
  isAuthenticated: boolean
  setAuth: (token: string, user: User) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      isAuthenticated: false,
      setAuth: (token, user) => set({ token, user, isAuthenticated: true }),
      logout: () => set({ token: null, user: null, isAuthenticated: false }),
    }),
    {
      name: 'auth-storage',
    }
  )
)

interface Car {
  id: string
  name: string
  license_plate: string
  make: string
  model: string
  year: number
  status: 'online' | 'offline'
  last_seen?: string
}

interface FleetState {
  cars: Car[]
  selectedCar: Car | null
  setCars: (cars: Car[]) => void
  selectCar: (car: Car | null) => void
}

export const useFleetStore = create<FleetState>()((set) => ({
  cars: [],
  selectedCar: null,
  setCars: (cars) => set({ cars }),
  selectCar: (car) => set({ selectedCar: car }),
}))

interface TelemetryData {
  speed: number
  rpm: number
  coolant_temp: number
  engine_load: number
  fuel_level: number
  latitude?: number
  longitude?: number
  timestamp: string
}

interface TelemetryState {
  liveData: Record<string, TelemetryData>
  updateTelemetry: (carId: string, data: TelemetryData) => void
}

export const useTelemetryStore = create<TelemetryState>()((set) => ({
  liveData: {},
  updateTelemetry: (carId, data) =>
    set((state) => ({
      liveData: { ...state.liveData, [carId]: data },
    })),
}))

interface Alert {
  id: string
  car_id: string
  car_name?: string
  severity: 'info' | 'warning' | 'critical'
  message: string
  is_read: boolean
  is_resolved: boolean
  created_at: string
}

interface AlertState {
  alerts: Alert[]
  unreadCount: number
  setAlerts: (alerts: Alert[]) => void
  addAlert: (alert: Alert) => void
  markRead: (id: string) => void
}

export const useAlertStore = create<AlertState>()((set) => ({
  alerts: [],
  unreadCount: 0,
  setAlerts: (alerts) => set({ 
    alerts, 
    unreadCount: alerts.filter(a => !a.is_read).length 
  }),
  addAlert: (alert) =>
    set((state) => ({
      alerts: [alert, ...state.alerts],
      unreadCount: state.unreadCount + 1,
    })),
  markRead: (id) =>
    set((state) => ({
      alerts: state.alerts.map((a) =>
        a.id === id ? { ...a, is_read: true } : a
      ),
      unreadCount: Math.max(0, state.unreadCount - 1),
    })),
}))
