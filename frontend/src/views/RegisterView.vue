<template>
  <div class="auth-wrapper">
    <el-card class="auth-card" shadow="always">
      <template #header><h2 class="auth-title">Create Account</h2></template>
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="handleRegister">
        <el-form-item label="Username" prop="username">
          <el-input v-model="form.username" placeholder="username" />
        </el-form-item>
        <el-form-item label="Email" prop="email">
          <el-input v-model="form.email" type="email" placeholder="you@example.com" />
        </el-form-item>
        <el-form-item label="Password" prop="password">
          <el-input v-model="form.password" type="password" show-password placeholder="Min 8 chars" />
        </el-form-item>
        <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" style="margin-bottom:12px" />
        <el-button type="primary" native-type="submit" :loading="loading" style="width:100%">Register</el-button>
      </el-form>
      <p class="auth-footer">Already have an account? <router-link to="/login">Sign in</router-link></p>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth.js'
import { ElMessage } from 'element-plus'

const router  = useRouter()
const auth    = useAuthStore()
const formRef = ref(null)
const loading = ref(false)
const error   = ref('')
const form = reactive({ username: '', email: '', password: '' })
const rules = {
  username: [{ required: true, message: 'Required', trigger: 'blur' }],
  email:    [{ required: true, type: 'email', message: 'Valid email required', trigger: 'blur' }],
  password: [{ required: true, min: 8, message: 'Min 8 chars', trigger: 'blur' }],
}

async function handleRegister() {
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    loading.value = true; error.value = ''
    try {
      await auth.register(form.username, form.email, form.password)
      ElMessage.success('Registration successful! Please sign in.')
      router.push('/login')
    } catch (err) {
      error.value = err.response?.data?.detail || 'Registration failed'
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
