import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { wsService } from '@/services/websocket'

// Global State
const username = ref<string | null>(localStorage.getItem('auth_username'))
const isLoggedIn = ref(localStorage.getItem('auth_logged_in') === 'true')

const TOKEN_KEY = 'auth_token'
const EXPIRED_EVENT = 'auth:expired'

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function getTokenTTLSeconds(): number {
  try {
    const raw = localStorage.getItem('auth_token_payload')
    if (!raw) return 0
    const payload = JSON.parse(raw) as { exp?: number }
    if (!payload.exp) return 0
    return Math.max(0, payload.exp - Math.floor(Date.now() / 1000))
  } catch {
    return 0
  }
}

// 清除本地认证状态并停止 WebSocket（供登出与认证失效事件共用）
function clearAuthState() {
  username.value = null
  isLoggedIn.value = false
  localStorage.removeItem('auth_username')
  localStorage.removeItem('auth_logged_in')
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem('auth_token_payload')
  wsService.stop()
}

// 监听 WebSocket 认证失效事件，清除状态并回到登录页
if (typeof window !== 'undefined') {
  window.addEventListener(EXPIRED_EVENT, () => {
    if (isLoggedIn.value) {
      clearAuthState()
      window.location.href = '/login'
    }
  })
}

export function useAuth() {
  const router = useRouter()

  const isAuthenticated = computed(() => isLoggedIn.value)

  function setAuthenticated(user: string, token?: string, expiresIn?: number) {
    username.value = user
    isLoggedIn.value = true

    localStorage.setItem('auth_username', user)
    localStorage.setItem('auth_logged_in', 'true')

    if (token) {
      localStorage.setItem(TOKEN_KEY, token)
      if (expiresIn) {
        localStorage.setItem(
          'auth_token_payload',
          JSON.stringify({ exp: Math.floor(Date.now() / 1000) + expiresIn })
        )
      }
    } else {
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem('auth_token_payload')
    }

    // 启动 WebSocket 连接
    wsService.start()
  }

  function logout() {
    clearAuthState()

    // Redirect to login if using router
    if (router) {
      router.push('/login')
    } else {
      window.location.href = '/login'
    }
  }

  async function login(user: string, pass: string): Promise<boolean> {
    try {
      const response = await fetch('/auth/status', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username: user, password: pass }),
      })

      if (response.status === 429) {
        console.warn('登录尝试过于频繁，请稍后再试')
        return false
      }

      if (response.ok) {
        const data = await response.json().catch(() => ({}))
        setAuthenticated(data.username || user, data.token, data.expires_in)
        return true
      } else {
        return false
      }
    } catch (e) {
      console.error('Login error', e)
      return false
    }
  }

  return {
    username,
    isAuthenticated,
    login,
    logout
  }
}

export { EXPIRED_EVENT }
