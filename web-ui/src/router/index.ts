import { watch } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '@/layouts/MainLayout.vue'
import LoginView from '@/views/LoginView.vue'
import DashboardView from '@/views/DashboardView.vue'
import TasksView from '@/views/TasksView.vue'
import AccountsView from '@/views/AccountsView.vue'
import ResultsView from '@/views/ResultsView.vue'
import LogsView from '@/views/LogsView.vue'
import SettingsView from '@/views/SettingsView.vue'
import { useAuth } from '@/composables/useAuth'
import { i18n, t } from '@/i18n'

// 视图直接打包进主包（体积小），换取点击导航零加载延迟
const routes = [
  {
    path: '/login',
    name: 'Login',
    component: LoginView,
    meta: { titleKey: 'routes.login' },
  },
  {
    path: '/',
    component: MainLayout,
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: DashboardView,
        meta: { titleKey: 'routes.dashboard', requiresAuth: true },
      },
      {
        path: 'tasks',
        name: 'Tasks',
        component: TasksView,
        meta: { titleKey: 'routes.tasks', requiresAuth: true },
      },
      {
        path: 'accounts',
        name: 'Accounts',
        component: AccountsView,
        meta: { titleKey: 'routes.accounts', requiresAuth: true },
      },
      {
        path: 'results',
        name: 'Results',
        component: ResultsView,
        meta: { titleKey: 'routes.results', requiresAuth: true },
      },
      {
        path: 'logs',
        name: 'Logs',
        component: LogsView,
        meta: { titleKey: 'routes.logs', requiresAuth: true },
      },
      {
        path: 'settings',
        name: 'Settings',
        component: SettingsView,
        meta: { titleKey: 'routes.settings', requiresAuth: true },
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    redirect: '/',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  // 路由切换立即回顶（覆盖 CSS 的 smooth 滚动，避免"缓动回顶"的卡顿感）
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return { ...savedPosition, behavior: 'instant' }
    }
    if (to.path !== from.path) {
      return { top: 0, left: 0, behavior: 'instant' }
    }
    return false
  },
})

function updateDocumentTitle() {
  const currentRoute = router.currentRoute.value
  const titleKey = typeof currentRoute.meta.titleKey === 'string'
    ? currentRoute.meta.titleKey
    : null
  const appName = t('app.name')
  document.title = titleKey ? `${t(titleKey)} - ${appName}` : appName
}

router.beforeEach((to, _from, next) => {
  const { isAuthenticated } = useAuth()

  if (to.meta.requiresAuth && !isAuthenticated.value) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else if (to.name === 'Login' && isAuthenticated.value) {
    next({ name: 'Dashboard' })
  } else {
    next()
  }
})

router.afterEach(() => {
  updateDocumentTitle()
})

watch(
  () => i18n.global.locale.value,
  () => {
    updateDocumentTitle()
  },
)

export default router
