<template>
  <div v-if="task">
    <el-page-header @back="$router.push('/tasks')" :content="`Task ${task.id}`" />
    <el-descriptions :column="2" border style="margin-top:16px">
      <el-descriptions-item label="Status">
        <el-tag :type="statusType(task.status)">{{ task.status }}</el-tag>
      </el-descriptions-item>
      <el-descriptions-item label="Exit Code">{{ task.exit_code ?? '—' }}</el-descriptions-item>
      <el-descriptions-item label="Started">{{ formatDate(task.started_at) }}</el-descriptions-item>
      <el-descriptions-item label="Finished">{{ formatDate(task.finished_at) }}</el-descriptions-item>
    </el-descriptions>

    <el-card style="margin-top:16px">
      <template #header>stdout</template>
      <pre class="log-block">{{ task.stdout || '(empty)' }}</pre>
    </el-card>

    <el-card style="margin-top:16px" v-if="task.stderr">
      <template #header>stderr</template>
      <pre class="log-block error">{{ task.stderr }}</pre>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/api/index.js'

const route = useRoute()
const task  = ref(null)
let timer = null

async function fetchTask() {
  const { data } = await api.get(`/tasks/${route.params.id}`)
  task.value = data
  // Stop polling once task is in terminal state
  if (['success', 'failed', 'timeout'].includes(data.status) && timer) {
    clearInterval(timer)
    timer = null
  }
}

onMounted(() => {
  fetchTask()
  timer = setInterval(fetchTask, 3000)
})
onUnmounted(() => { if (timer) clearInterval(timer) })

function statusType(s) {
  return { success: 'success', failed: 'danger', running: 'warning', queued: 'info', timeout: 'danger' }[s] || ''
}
function formatDate(d) { return d ? new Date(d).toLocaleString() : '—' }
</script>

<style scoped>
.log-block       { background:#1e293b; color:#e2e8f0; padding:16px; border-radius:6px; overflow-x:auto; font-size:0.8rem; white-space:pre-wrap; }
.log-block.error { color:#fca5a5; }
</style>
