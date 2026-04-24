<template>
  <el-container class="layout">
    <el-aside width="220px" class="sidebar">
      <div class="logo">CIS Platform</div>
      <el-menu :default-active="$route.path" router>
        <el-menu-item index="/scripts">
          <el-icon><Document /></el-icon> Scripts
        </el-menu-item>
        <el-menu-item index="/scripts/submit">
          <el-icon><Plus /></el-icon> Submit Script
        </el-menu-item>
        <el-menu-item index="/tasks">
          <el-icon><List /></el-icon> My Tasks
        </el-menu-item>
        <template v-if="auth.isReviewer">
          <el-divider />
          <el-menu-item index="/admin/scripts">
            <el-icon><Checked /></el-icon> Review Scripts
          </el-menu-item>
        </template>
        <template v-if="auth.isAdmin">
          <el-menu-item index="/admin/users">
            <el-icon><User /></el-icon> Users
          </el-menu-item>
          <el-menu-item index="/admin/audit">
            <el-icon><Clock /></el-icon> Audit Logs
          </el-menu-item>
        </template>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <span class="user-info">
          <el-icon><UserFilled /></el-icon>
          {{ auth.user?.username }} ({{ auth.user?.role }})
        </span>
        <el-button type="danger" link @click="handleLogout">Logout</el-button>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth.js'

const auth = useAuthStore()
const router = useRouter()

async function handleLogout() {
  await auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.layout  { height: 100vh; }
.sidebar { background: #1e293b; }
.logo    { color: #fff; padding: 20px; font-size: 1.1rem; font-weight: bold; border-bottom: 1px solid #334155; }
.header  { display: flex; align-items: center; justify-content: flex-end; gap: 16px; border-bottom: 1px solid #e2e8f0; }
.user-info { display: flex; align-items: center; gap: 6px; color: #475569; }
</style>
