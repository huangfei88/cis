<template>
  <div>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
      <h2>Scripts</h2>
      <el-button type="primary" @click="$router.push('/scripts/submit')">Submit New Script</el-button>
    </div>
    <el-table v-loading="loading" :data="scripts" border stripe>
      <el-table-column prop="title" label="Title" min-width="200">
        <template #default="{ row }">
          <router-link :to="`/scripts/${row.id}`">{{ row.title }}</router-link>
        </template>
      </el-table-column>
      <el-table-column prop="script_type" label="Type" width="100" />
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
      <el-pagination
        v-model:current-page="page"
        :page-size="perPage"
        :total="total"
        layout="prev, pager, next"
        @current-change="fetchScripts"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/api/index.js'

const scripts = ref([])
const loading = ref(false)
const page    = ref(1)
const perPage = 20
const total   = ref(0)

async function fetchScripts(p = 1) {
  loading.value = true
  try {
    const { data } = await api.get('/scripts/', { params: { page: p, per_page: perPage } })
    scripts.value = data
    // Show correct total: if full page returned we indicate there may be more
    total.value = data.length === perPage ? p * perPage + perPage : (p - 1) * perPage + data.length
  } finally {
    loading.value = false
  }
}

function statusType(s) {
  return { approved: 'success', rejected: 'danger', pending: 'warning', under_review: 'info' }[s] || ''
}
function formatDate(d) { return d ? new Date(d).toLocaleString() : '—' }

onMounted(() => fetchScripts())
</script>
