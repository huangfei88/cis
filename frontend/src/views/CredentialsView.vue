<template>
  <div>
    <div class="page-header">
      <h2>Credentials</h2>
      <el-button type="primary" @click="openAddDialog">Add Credential</el-button>
    </div>

    <el-table :data="credentials" v-loading="loading" stripe>
      <el-table-column prop="name" label="Name" />
      <el-table-column prop="cred_type" label="Type" width="120" />
      <el-table-column prop="username" label="Username" />
      <el-table-column label="Created" width="180">
        <template #default="{ row }">{{ new Date(row.created_at).toLocaleString() }}</template>
      </el-table-column>
      <el-table-column label="Actions" width="100">
        <template #default="{ row }">
          <el-button size="small" type="danger" @click="deleteCredential(row.id)">Delete</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Add Dialog -->
    <el-dialog v-model="dialogVisible" title="Add Credential" width="480px">
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="Name" prop="name">
          <el-input v-model="form.name" placeholder="My SSH key" />
        </el-form-item>
        <el-form-item label="Type" prop="cred_type">
          <el-select v-model="form.cred_type" style="width:100%">
            <el-option label="Password" value="password" />
            <el-option label="Private Key" value="private_key" />
          </el-select>
        </el-form-item>
        <el-form-item label="Username" prop="username">
          <el-input v-model="form.username" placeholder="root" />
        </el-form-item>
        <el-form-item label="Secret" prop="secret">
          <el-input
            v-model="form.secret"
            :type="form.cred_type === 'private_key' ? 'textarea' : 'password'"
            :rows="6"
            show-password
            placeholder="Password or PEM private key"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">Cancel</el-button>
        <el-button type="primary" :loading="saving" @click="saveCredential">Save</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'

const credentials = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const saving = ref(false)
const formRef = ref(null)

const form = reactive({ name: '', cred_type: 'password', username: '', secret: '' })

const rules = {
  name: [{ required: true, message: 'Required', trigger: 'blur' }],
  cred_type: [{ required: true, message: 'Required', trigger: 'change' }],
  username: [{ required: true, message: 'Required', trigger: 'blur' }],
  secret: [{ required: true, message: 'Required', trigger: 'blur' }],
}

function authHeaders() {
  return { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
}

async function fetchCredentials() {
  loading.value = true
  try {
    const { data } = await axios.get('/api/v1/credentials/', { headers: authHeaders() })
    credentials.value = data
  } catch {
    ElMessage.error('Failed to load credentials')
  } finally {
    loading.value = false
  }
}

function openAddDialog() {
  Object.assign(form, { name: '', cred_type: 'password', username: '', secret: '' })
  dialogVisible.value = true
}

async function saveCredential() {
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    try {
      await axios.post('/api/v1/credentials/', { ...form }, { headers: authHeaders() })
      ElMessage.success('Credential saved')
      dialogVisible.value = false
      form.secret = ''
      await fetchCredentials()
    } catch (err) {
      ElMessage.error(err.response?.data?.detail || 'Save failed')
    } finally {
      saving.value = false
    }
  })
}

async function deleteCredential(id) {
  await ElMessageBox.confirm('Delete this credential?', 'Confirm', { type: 'warning' })
  try {
    await axios.delete(`/api/v1/credentials/${id}`, { headers: authHeaders() })
    ElMessage.success('Credential deleted')
    await fetchCredentials()
  } catch {
    ElMessage.error('Delete failed')
  }
}

onMounted(fetchCredentials)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
</style>
