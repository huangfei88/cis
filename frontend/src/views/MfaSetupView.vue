<template>
  <div class="mfa-wrapper">
    <el-card style="max-width:560px;margin:0 auto">
      <template #header><h2 style="margin:0">Multi-Factor Authentication</h2></template>

      <el-descriptions :column="1" border>
        <el-descriptions-item label="Status">
          <el-tag :type="mfaEnabled ? 'success' : 'info'">
            {{ mfaEnabled ? 'Enabled' : 'Disabled' }}
          </el-tag>
        </el-descriptions-item>
      </el-descriptions>

      <!-- Setup step 1 – not yet set up or re-setup -->
      <template v-if="!mfaEnabled">
        <el-divider />
        <p>Scan the QR code below with an authenticator app (Google Authenticator, Authy, etc.), then enter the 6-digit code to enable MFA.</p>

        <el-button type="primary" :loading="setupLoading" @click="setupMfa" style="margin-bottom:16px">
          Generate MFA Secret
        </el-button>

        <template v-if="otpUri">
          <p style="word-break:break-all;font-size:0.85em;color:#475569">
            <strong>OTP URI:</strong> {{ otpUri }}
          </p>
          <p>
            <a :href="qrUrl" target="_blank">
              <img :src="qrUrl" alt="QR Code" style="border:1px solid #e2e8f0;border-radius:4px" />
            </a>
          </p>
          <el-form @submit.prevent="enableMfa" style="margin-top:12px">
            <el-form-item label="Verification Code">
              <el-input v-model="verifyCode" placeholder="123456" maxlength="6" style="width:200px" />
            </el-form-item>
            <el-button type="success" native-type="submit" :loading="enableLoading">Enable MFA</el-button>
          </el-form>
        </template>
      </template>

      <!-- Disable MFA -->
      <template v-else>
        <el-divider />
        <p>Enter your current authenticator code to disable MFA.</p>
        <el-form @submit.prevent="disableMfa">
          <el-form-item label="Current MFA Code">
            <el-input v-model="disableCode" placeholder="123456" maxlength="6" style="width:200px" />
          </el-form-item>
          <el-button type="danger" native-type="submit" :loading="disableLoading">Disable MFA</el-button>
        </el-form>
      </template>

      <el-alert v-if="errorMsg" :title="errorMsg" type="error" show-icon :closable="false" style="margin-top:16px" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import { useAuthStore } from '@/stores/auth.js'
import { ElMessage } from 'element-plus'

const auth = useAuthStore()
const mfaEnabled = ref(false)
const otpUri = ref('')
const verifyCode = ref('')
const disableCode = ref('')
const setupLoading = ref(false)
const enableLoading = ref(false)
const disableLoading = ref(false)
const errorMsg = ref('')

const qrUrl = computed(() => {
  if (!otpUri.value) return ''
  return `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(otpUri.value)}`
})

function authHeaders() {
  return { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
}

onMounted(() => {
  // Derive MFA status from JWT payload stored in auth store
  const token = localStorage.getItem('access_token')
  if (token) {
    try {
      const payload = JSON.parse(atob(token.split('.')[1]))
      mfaEnabled.value = !!payload.mfa_enabled
    } catch {
      // ignore
    }
  }
})

async function setupMfa() {
  setupLoading.value = true
  errorMsg.value = ''
  try {
    const { data } = await axios.post('/api/v1/auth/mfa/setup', {}, { headers: authHeaders() })
    otpUri.value = data.uri
  } catch (err) {
    errorMsg.value = err.response?.data?.detail || 'Setup failed'
  } finally {
    setupLoading.value = false
  }
}

async function enableMfa() {
  enableLoading.value = true
  errorMsg.value = ''
  try {
    await axios.post('/api/v1/auth/mfa/enable', { code: verifyCode.value }, { headers: authHeaders() })
    ElMessage.success('MFA enabled successfully')
    mfaEnabled.value = true
    otpUri.value = ''
    verifyCode.value = ''
  } catch (err) {
    errorMsg.value = err.response?.data?.detail || 'Enable failed'
  } finally {
    enableLoading.value = false
  }
}

async function disableMfa() {
  disableLoading.value = true
  errorMsg.value = ''
  try {
    await axios.post('/api/v1/auth/mfa/disable', { code: disableCode.value }, { headers: authHeaders() })
    ElMessage.success('MFA disabled')
    mfaEnabled.value = false
    disableCode.value = ''
  } catch (err) {
    errorMsg.value = err.response?.data?.detail || 'Disable failed'
  } finally {
    disableLoading.value = false
  }
}
</script>

<style scoped>
.mfa-wrapper { padding: 24px; }
</style>
