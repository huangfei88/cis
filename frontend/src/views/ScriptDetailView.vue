<template>
  <div v-if="script">
    <el-page-header @back="$router.push('/scripts')" :content="script.title" />
    <el-descriptions :column="2" border style="margin-top:16px">
      <el-descriptions-item label="Type">{{ script.script_type }}</el-descriptions-item>
      <el-descriptions-item label="Status">
        <el-tag :type="statusType(script.status)">{{ script.status }}</el-tag>
      </el-descriptions-item>
      <el-descriptions-item label="Created">{{ formatDate(script.created_at) }}</el-descriptions-item>
      <el-descriptions-item label="Description">{{ script.description || '—' }}</el-descriptions-item>
    </el-descriptions>

    <el-card style="margin-top:16px">
      <template #header>Script Content</template>
      <pre class="code-block">{{ script.content }}</pre>
    </el-card>

    <div v-if="script.status === 'approved'" style="margin-top:16px">
      <el-button type="primary" :loading="running" @click="runScript">Run Script</el-button>
    </div>
  </div>
  <el-empty v-else-if="!loading" description="Script not found" />
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api/index.js'
import { ElMessage } from 'element-plus'

const route  = useRoute()
const router = useRouter()
const script  = ref(null)
const loading = ref(false)
const running = ref(false)

onMounted(async () => {
  loading.value = true
  try {
    const { data } = await api.get(`/scripts/${route.params.id}`)
    script.value = data
  } finally {
    loading.value = false
  }
})

async function runScript() {
  running.value = true
  try {
    const { data } = await api.post('/tasks/', { script_id: script.value.id })
    ElMessage.success('Task queued!')
    router.push(`/tasks/${data.id}`)
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || 'Failed to run script')
  } finally {
    running.value = false
  }
}

function statusType(s) {
  return { approved: 'success', rejected: 'danger', pending: 'warning', under_review: 'info' }[s] || ''
}
function formatDate(d) { return d ? new Date(d).toLocaleString() : '—' }
</script>

<style scoped>
.code-block { background:#1e293b; color:#e2e8f0; padding:16px; border-radius:6px; overflow-x:auto; font-size:0.85rem; }
</style>
