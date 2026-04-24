<template>
  <div>
    <h2>Audit Logs</h2>
    <el-table v-loading="loading" :data="logs" border stripe size="small">
      <el-table-column prop="created_at" label="Time" width="180">
        <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
      </el-table-column>
      <el-table-column prop="action" label="Action" width="180" />
      <el-table-column prop="user_id" label="User ID" min-width="260" />
      <el-table-column prop="resource_type" label="Resource" width="100" />
      <el-table-column prop="ip_address" label="IP" width="130" />
      <el-table-column prop="status_code" label="Status" width="80" />
      <el-table-column prop="request_method" label="Method" width="80" />
      <el-table-column prop="request_path" label="Path" min-width="200" />
    </el-table>
    <div style="margin-top:16px;display:flex;justify-content:flex-end">
      <el-pagination v-model:current-page="page" :page-size="perPage" :total="total"
        layout="prev, pager, next" @current-change="fetchLogs" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/api/index.js'

const logs    = ref([])
const loading = ref(false)
const page    = ref(1)
const perPage = 50
const total   = ref(0)

async function fetchLogs(p = 1) {
  loading.value = true
  try {
    const { data } = await api.get('/admin/audit-logs', { params: { page: p, per_page: perPage } })
    logs.value = data
    total.value = data.length === perPage ? p * perPage + perPage : (p - 1) * perPage + data.length
  } finally {
    loading.value = false
  }
}

function formatDate(d) { return d ? new Date(d).toLocaleString() : '—' }
onMounted(() => fetchLogs())
</script>
