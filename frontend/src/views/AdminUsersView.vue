<template>
  <div>
    <h2>User Management</h2>
    <el-table v-loading="loading" :data="users" border stripe>
      <el-table-column prop="username" label="Username" width="150" />
      <el-table-column prop="email" label="Email" min-width="200" />
      <el-table-column prop="role" label="Role" width="130">
        <template #default="{ row }">
          <el-select v-model="row.role" size="small" @change="(v) => updateRole(row.id, v)">
            <el-option value="user"     label="user" />
            <el-option value="reviewer" label="reviewer" />
            <el-option value="admin"    label="admin" />
          </el-select>
        </template>
      </el-table-column>
      <el-table-column prop="is_active" label="Active" width="80">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'danger'">{{ row.is_active ? 'Yes' : 'No' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="Created" width="180">
        <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/api/index.js'
import { ElMessage } from 'element-plus'

const users   = ref([])
const loading = ref(false)

async function fetchUsers() {
  loading.value = true
  try {
    const { data } = await api.get('/admin/users')
    users.value = data
  } finally {
    loading.value = false
  }
}

async function updateRole(userId, role) {
  try {
    await api.put(`/admin/users/${userId}/role`, { role })
    ElMessage.success('Role updated')
  } catch (err) {
    ElMessage.error('Failed to update role')
    fetchUsers()
  }
}

function formatDate(d) { return d ? new Date(d).toLocaleString() : '—' }
onMounted(fetchUsers)
</script>
