import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))

  const isAuthenticated = computed(() => !!user.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const isReviewer = computed(() => ['admin', 'reviewer'].includes(user.value?.role))

  async function login(username, password) {
    const { data } = await axios.post('/api/v1/auth/login', { username, password })
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    // Decode payload to get user info
    const payload = JSON.parse(atob(data.access_token.split('.')[1]))
    user.value = { id: payload.sub, username: payload.username, role: payload.role }
    localStorage.setItem('user', JSON.stringify(user.value))
  }

  async function register(username, email, password) {
    await axios.post('/api/v1/auth/register', { username, email, password })
  }

  async function logout() {
    const token = localStorage.getItem('access_token')
    if (token) {
      await axios.post('/api/v1/auth/logout', {}, {
        headers: { Authorization: `Bearer ${token}` },
      }).catch(() => {})
    }
    user.value = null
    localStorage.clear()
  }

  return { user, isAuthenticated, isAdmin, isReviewer, login, register, logout }
})
