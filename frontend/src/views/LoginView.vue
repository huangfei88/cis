<template>
  <div class="auth-wrapper">
    <el-card class="auth-card" shadow="always">
      <template #header><h2 class="auth-title">Sign in to CIS</h2></template>

      <!-- Step 1: Username + Password -->
      <el-form
        v-if="!mfaRequired"
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @submit.prevent="handleLogin"
      >
        <el-form-item label="Username" prop="username">
          <el-input v-model="form.username" placeholder="Username" autocomplete="username" />
        </el-form-item>
        <el-form-item label="Password" prop="password">
          <el-input v-model="form.password" type="password" show-password placeholder="Password" autocomplete="current-password" />
        </el-form-item>
        <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" style="margin-bottom:12px" />
        <el-button type="primary" native-type="submit" :loading="loading" style="width:100%">Sign In</el-button>
      </el-form>

      <!-- Step 2: MFA Code -->
      <el-form
        v-else
        ref="mfaFormRef"
        :model="form"
        :rules="mfaRules"
        label-position="top"
        @submit.prevent="handleMfaLogin"
      >
        <p style="color:#475569;margin-top:0">Enter the 6-digit code from your authenticator app.</p>
        <el-form-item label="MFA Code" prop="mfa_code">
          <el-input v-model="form.mfa_code" placeholder="123456" maxlength="6" autocomplete="one-time-code" />
        </el-form-item>
        <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" style="margin-bottom:12px" />
        <el-button type="primary" native-type="submit" :loading="loading" style="width:100%">Verify</el-button>
        <el-button style="width:100%;margin-top:8px" @click="resetLogin">Back</el-button>
      </el-form>

      <p v-if="!mfaRequired" class="auth-footer">No account? <router-link to="/register">Register</router-link></p>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import axios from 'axios'
import { useAuthStore } from '@/stores/auth.js'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const formRef = ref(null)
const mfaFormRef = ref(null)
const loading = ref(false)
const error = ref('')
const mfaRequired = ref(false)

const form = reactive({ username: '', password: '', mfa_code: '' })

const rules = {
  username: [{ required: true, message: 'Required', trigger: 'blur' }],
  password: [{ required: true, message: 'Required', trigger: 'blur' }],
}
const mfaRules = {
  mfa_code: [{ required: true, message: 'Required', trigger: 'blur' }],
}

function resetLogin() {
  mfaRequired.value = false
  form.mfa_code = ''
  error.value = ''
}

async function handleLogin() {
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    loading.value = true
    error.value = ''
    try {
      const { data } = await axios.post('/api/v1/auth/login', {
        username: form.username,
        password: form.password,
      })
      if (data.mfa_required) {
        mfaRequired.value = true
        return
      }
      _applyTokens(data)
    } catch (err) {
      error.value = err.response?.data?.detail || 'Login failed'
    } finally {
      loading.value = false
    }
  })
}

async function handleMfaLogin() {
  await mfaFormRef.value.validate(async (valid) => {
    if (!valid) return
    loading.value = true
    error.value = ''
    try {
      const { data } = await axios.post('/api/v1/auth/login', {
        username: form.username,
        password: form.password,
        mfa_code: form.mfa_code,
      })
      _applyTokens(data)
    } catch (err) {
      error.value = err.response?.data?.detail || 'Invalid MFA code'
    } finally {
      loading.value = false
    }
  })
}

function _applyTokens(data) {
  localStorage.setItem('access_token', data.access_token)
  localStorage.setItem('refresh_token', data.refresh_token)
  const payload = JSON.parse(atob(data.access_token.split('.')[1]))
  auth.user = { id: payload.sub, username: payload.username, role: payload.role }
  localStorage.setItem('user', JSON.stringify(auth.user))
  router.push(route.query.redirect || '/scripts')
}
</script>

<style scoped>
.auth-wrapper { display:flex; justify-content:center; align-items:center; min-height:100vh; background:#f0f2f5; }
.auth-card    { width:400px; }
.auth-title   { margin:0; text-align:center; }
.auth-footer  { margin-top:12px; text-align:center; color:#606266; }
</style>
