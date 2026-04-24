<template>
  <div>
    <h2>Pending Scripts</h2>
    <el-table v-loading="loading" :data="scripts" border stripe>
      <el-table-column prop="title" label="Title" min-width="200" />
      <el-table-column prop="script_type" label="Type" width="100" />
      <el-table-column prop="status" label="Status" width="120">
        <template #default="{ row }">
          <el-tag type="warning">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="Actions" width="220">
        <template #default="{ row }">
          <el-button size="small" type="success" @click="openReview(row, 'approve')">Approve</el-button>
          <el-button size="small" type="danger"  @click="openReview(row, 'reject')">Reject</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="`${reviewAction === 'approve' ? 'Approve' : 'Reject'} Script`">
      <p><strong>{{ selected?.title }}</strong></p>
      <el-input v-model="comment" type="textarea" :rows="3" placeholder="Review comment (optional)" />
      <template #footer>
        <el-button @click="dialogVisible = false">Cancel</el-button>
        <el-button :type="reviewAction === 'approve' ? 'success' : 'danger'" :loading="submitting" @click="submitReview">
          Confirm
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/api/index.js'
import { ElMessage } from 'element-plus'

const scripts       = ref([])
const loading       = ref(false)
const dialogVisible = ref(false)
const selected      = ref(null)
const reviewAction  = ref('approve')
const comment       = ref('')
const submitting    = ref(false)

async function fetchScripts() {
  loading.value = true
  try {
    const { data } = await api.get('/admin/scripts/pending')
    scripts.value = data
  } finally {
    loading.value = false
  }
}

function openReview(script, action) {
  selected.value = script; reviewAction.value = action; comment.value = ''; dialogVisible.value = true
}

async function submitReview() {
  submitting.value = true
  try {
    await api.post(`/scripts/${selected.value.id}/review`, { action: reviewAction.value, comment: comment.value })
    ElMessage.success('Review submitted')
    dialogVisible.value = false
    fetchScripts()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || 'Failed')
  } finally {
    submitting.value = false
  }
}

onMounted(fetchScripts)
</script>
