import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth.js'

const routes = [
  { path: '/login',    name: 'Login',    component: () => import('@/views/LoginView.vue'),    meta: { public: true } },
  { path: '/register', name: 'Register', component: () => import('@/views/RegisterView.vue'), meta: { public: true } },
  {
    path: '/',
    component: () => import('@/components/AppLayout.vue'),
    children: [
      { path: '',        redirect: '/scripts' },
      { path: 'scripts', name: 'Scripts',       component: () => import('@/views/ScriptsView.vue') },
      { path: 'scripts/submit', name: 'SubmitScript', component: () => import('@/views/ScriptSubmitView.vue') },
      { path: 'scripts/:id',    name: 'ScriptDetail', component: () => import('@/views/ScriptDetailView.vue') },
      { path: 'tasks',          name: 'Tasks',        component: () => import('@/views/TasksView.vue') },
      { path: 'tasks/:id',      name: 'TaskDetail',   component: () => import('@/views/TaskDetailView.vue') },
      { path: 'servers',        name: 'Servers',      component: () => import('@/views/ServersView.vue') },
      { path: 'credentials',    name: 'Credentials',  component: () => import('@/views/CredentialsView.vue') },
      { path: 'profile/mfa',    name: 'MfaSetup',     component: () => import('@/views/MfaSetupView.vue') },
      { path: 'admin/scripts',  name: 'AdminScripts', component: () => import('@/views/AdminScriptsView.vue'), meta: { roles: ['admin', 'reviewer'] } },
      { path: 'admin/users',    name: 'AdminUsers',   component: () => import('@/views/AdminUsersView.vue'),   meta: { roles: ['admin'] } },
      { path: 'admin/audit',    name: 'AdminAudit',   component: () => import('@/views/AdminAuditView.vue'),   meta: { roles: ['admin'] } },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.isAuthenticated) {
    return { name: 'Login', query: { redirect: to.fullPath } }
  }
  if (to.meta.roles && !to.meta.roles.includes(auth.user?.role)) {
    return { name: 'Scripts' }
  }
})

export default router
