<template>
  <div>
    <div class="page-header">
      <h2>Servers</h2>
      <el-button type="primary" @click="openAddDialog">Add Server</el-button>
    </div>

    <el-table :data="servers" v-loading="loading" stripe>
      <el-table-column prop="name" label="Name" />
      <el-table-column prop="host" label="Host" />
      <el-table-column prop="port" label="Port" width="80" />
      <el-table-column prop="conn_type" label="Type" width="90" />
      <el-table-column label="Fingerprint" width="180">
        <template #default="{ row }">
          <span v-if="row.fingerprint" class="mono">{{ row.fingerprint.slice(0, 16) }}…</span>
          <el-tag v-else type="warning" size="small">Not verified</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="Tags">
        <template #default="{ row }">{{ (row.tags || []).join(', ') }}</template>
      </el-table-column>
      <el-table-column label="Active" width="80">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
            {{ row.is_active ? 'Yes' : 'No' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="Actions" width="140">
        <template #default="{ row }">
          <el-button size="small" @click="openEditDialog(row)">Edit</el-button>
          <el-button size="small" type="danger" @click="deleteServer(row.id)">Delete</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Add / Edit Dialog -->
    <el-dialog v-model="dialogVisible" :title="editingId ? 'Edit Server' : 'Add Server'" width="480px">
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="Name" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="Host" prop="host">
          <el-input v-model="form.host" placeholder="192.168.1.100 or hostname" />
        </el-form-item>
        <el-form-item label="Port" prop="port">
          <el-input-number v-model="form.port" :min="1" :max="65535" style="width:100%" />
        </el-form-item>
        <el-form-item label="Connection Type" prop="conn_type">
          <el-select v-model="form.conn_type" style="width:100%">
            <el-option label="SSH" value="ssh" />
            <el-option label="Agent" value="agent" />
          </el-select>
        </el-form-item>
        <el-form-item label="Tags (comma-separated)">
          <el-input v-model="tagsInput" placeholder="prod, web, us-east" />
        </el-form-item>
        <el-form-item v-if="editingId" label="Active">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">Cancel</el-button>
        <el-button type="primary" :loading="saving" @click="saveServer">Save</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'

const servers = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const saving = ref(false)
const editingId = ref(null)
const formRef = ref(null)
const tagsInput = ref('')

const form = reactive({ name: '', host: '', port: 22, conn_type: 'ssh', is_active: true })

const rules = {
  name: [{ required: true, message: 'Required', trigger: 'blur' }],
  host: [{ required: true, message: 'Required', trigger: 'blur' }],
  conn_type: [{ required: true, message: 'Required', trigger: 'change' }],
}

function authHeaders() {
  return { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
}

async function fetchServers() {
  loading.value = true
  try {
    const { data } = await axios.get('/api/v1/servers/', { headers: authHeaders() })
    servers.value = data
  } catch {
    ElMessage.error('Failed to load servers')
  } finally {
    loading.value = false
  }
}

function openAddDialog() {
  editingId.value = null
  Object.assign(form, { name: '', host: '', port: 22, conn_type: 'ssh', is_active: true })
  tagsInput.value = ''
  dialogVisible.value = true
}

function openEditDialog(row) {
  editingId.value = row.id
  Object.assign(form, {
    name: row.name, host: row.host, port: row.port,
    conn_type: row.conn_type, is_active: row.is_active,
  })
  tagsInput.value = (row.tags || []).join(', ')
  dialogVisible.value = true
}

async function saveServer() {
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    const payload = {
      ...form,
      tags: tagsInput.value.split(',').map(t => t.trim()).filter(Boolean),
    }
    try {
      if (editingId.value) {
        await axios.put(`/api/v1/servers/${editingId.value}`, payload, { headers: authHeaders() })
        ElMessage.success('Server updated')
      } else {
        await axios.post('/api/v1/servers/', payload, { headers: authHeaders() })
        ElMessage.success('Server added')
      }
      dialogVisible.value = false
      await fetchServers()
    } catch (err) {
      ElMessage.error(err.response?.data?.detail || 'Save failed')
    } finally {
      saving.value = false
    }
  })
}

async function deleteServer(id) {
  await ElMessageBox.confirm('Delete this server?', 'Confirm', { type: 'warning' })
  try {
    await axios.delete(`/api/v1/servers/${id}`, { headers: authHeaders() })
    ElMessage.success('Server deleted')
    await fetchServers()
  } catch {
    ElMessage.error('Delete failed')
  }
}

onMounted(fetchServers)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.mono { font-family: monospace; font-size: 0.85em; }
</style>
