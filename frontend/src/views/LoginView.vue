<template>
  <div class="auth-wrapper">
    <el-card class="auth-card" shadow="always">
      <template #header><h2 class="auth-title">Sign in to CIS</h2></template>
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="handleLogin">
        <el-form-item label="Username" prop="username">
          <el-input v-model="form.username" placeholder="Username" autocomplete="username" />
        </el-form-item>
        <el-form-item label="Password" prop="password">
          <el-input v-model="form.password" type="password" show-password placeholder="Password" autocomplete="current-password" />
        </el-form-item>
        <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" style="margin-bottom:12px" />
        <el-button type="primary" native-type="submit" :loading="loading" style="width:100%">Sign In</el-button>
      </el-form>
      <p class="auth-footer">No account? <router-link to="/register">Register</router-link></p>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth.js'

const router = useRouter()
const route  = useRoute()
const auth   = useAuthStore()
const formRef = ref(null)
const loading = ref(false)
const error   = ref('')
const form = reactive({ username: '', password: '' })
const rules = {
  username: [{ required: true, message: 'Required', trigger: 'blur' }],
  password: [{ required: true, message: 'Required', trigger: 'blur' }],
}

async function handleLogin() {
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    loading.value = true; error.value = ''
    try {
      await auth.login(form.username, form.password)
      router.push(route.query.redirect || '/scripts')
    } catch (err) {
      error.value = err.response?.data?.detail || 'Login failed'
    } finally {
      loading.value = false
    }
  })
}
</script>

<style scoped>
.auth-wrapper { display:flex; justify-content:center; align-items:center; min-height:100vh; background:#f0f2f5; }
.auth-card    { width:400px; }
.auth-title   { margin:0; text-align:center; }
.auth-footer  { margin-top:12px; text-align:center; color:#606266; }
</style>
