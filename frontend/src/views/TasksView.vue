<template>
  <div>
    <h2>My Tasks</h2>
    <el-table v-loading="loading" :data="tasks" border stripe>
      <el-table-column prop="id" label="Task ID" width="300">
        <template #default="{ row }">
          <router-link :to="`/tasks/${row.id}`">{{ row.id }}</router-link>
        </template>
      </el-table-column>
      <el-table-column prop="script_id" label="Script ID" width="300" />
      <el-table-column prop="status" label="Status" width="120">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="Created" width="180">
        <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
      </el-table-column>
    </el-table>
    <div style="margin-top:16px;display:flex;justify-content:flex-end">
      <el-pagination v-model:current-page="page" :page-size="perPage" :total="total"
        layout="prev, pager, next" @current-change="fetchTasks" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/api/index.js'

const tasks   = ref([])
const loading = ref(false)
const page    = ref(1)
const perPage = 20
const total   = ref(0)

async function fetchTasks(p = 1) {
  loading.value = true
  try {
    const { data } = await api.get('/tasks/', { params: { page: p, per_page: perPage } })
    tasks.value = data
    total.value = data.length === perPage ? p * perPage + perPage : (p - 1) * perPage + data.length
  } finally {
    loading.value = false
  }
}

function statusType(s) {
  return { success: 'success', failed: 'danger', running: 'warning', queued: 'info', timeout: 'danger' }[s] || ''
}
function formatDate(d) { return d ? new Date(d).toLocaleString() : '—' }

onMounted(() => fetchTasks())
</script>
