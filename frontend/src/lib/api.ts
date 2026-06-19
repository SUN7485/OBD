import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add auth token to requests
api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
  }
  return config
})

// Handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      if (typeof window !== 'undefined') {
        localStorage.removeItem('token')
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

// Auth API
export const authAPI = {
  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }),
  register: (email: string, password: string, organization_name: string, full_name: string = "Admin") =>
    api.post('/auth/register', { email, password, organization_name, full_name }),
  me: () => api.get('/auth/me'),
}

// Cars API
export const carsAPI = {
  list: () => api.get('/telemetry/cars'),
  get: (id: string) => api.get(`/telemetry/latest/${id}`),
  create: (data: any) => api.post('/cars', data),
  update: (id: string, data: any) => api.put(`/cars/${id}`, data),
  delete: (id: string) => api.delete(`/cars/${id}`),
}

// Telemetry API
export const telemetryAPI = {
  ingest: (car_id: string, data: any) =>
    api.post('/telemetry/ingest', { car_id, ...data }),
  history: (car_id: string, start: string, end: string, metrics?: string[]) =>
    api.get('/telemetry/history', { params: { car_id, start, end, metrics } }),
  live: (car_id: string) => api.get(`/telemetry/live/${car_id}`),
}

// Analytics API
export const analyticsAPI = {
  fleetSummary: () => api.get('/analytics/fleet/summary'),
  carSummary: (car_id: string) => api.get(`/analytics/car/${car_id}/summary`),
}

// Alerts API
export const alertsAPI = {
  list: (params?: any) => api.get('/alerts', { params }),
  markRead: (id: string) => api.post(`/alerts/${id}/read`),
  resolve: (id: string) => api.post(`/alerts/${id}/resolve`),
}

// Messages API
export const messagesAPI = {
  list: (params?: any) => api.get('/messages', { params }),
  create: (data: any) => api.post('/messages', data),
}

// AI API
export const aiAPI = {
  chat: (message: string, car_id?: string) =>
    api.post('/ai/chat', { message, car_id }),
  explainDTC: (car_id: string, dtc_codes: string[]) =>
    api.post('/ai/dtc/explain', { car_id, dtc_codes }),
}

// Fleet API
export const fleetAPI = {
  // Geofences
  listGeofences: () => api.get('/fleet/geofences'),
  createGeofence: (data: any) => api.post('/fleet/geofences', data),
  updateGeofence: (id: string, data: any) => api.put(`/fleet/geofences/${id}`, data),
  deleteGeofence: (id: string) => api.delete(`/fleet/geofences/${id}`),
  checkGeofence: (car_id: string) => api.post('/fleet/geofences/check', { car_id }),

  // Driver Scores
  driverLeaderboard: (limit?: number) => api.get('/fleet/drivers/leaderboard', { params: { limit } }),
  driverScore: (car_id: string) => api.get(`/fleet/drivers/${car_id}/score`),

  // Maintenance
  listMaintenance: (params?: any) => api.get('/fleet/maintenance', { params }),
  createMaintenance: (data: any) => api.post('/fleet/maintenance', data),
  predictMaintenance: (car_id: string) => api.post(`/fleet/maintenance/${car_id}/predict`),

  // Fuel
  analyzeFuel: (car_id: string, data: any) => api.post('/fleet/fuel/analyze', { car_id, ...data }),
  fuelAnomalies: (params?: any) => api.get('/fleet/fuel/anomalies', { params }),

  // Trips
  trips: (car_id: string, params?: any) => api.get(`/fleet/trips/${car_id}`, { params }),
  tripSummary: (car_id: string) => api.get(`/fleet/trips/${car_id}/summary`),
}

export default api
