<template>
  <div>
    <el-page-header @back="$router.push('/scripts')" content="Submit Script" />
    <el-card style="margin-top:16px">
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="handleSubmit">
        <el-form-item label="Title" prop="title">
          <el-input v-model="form.title" placeholder="My deployment playbook" />
        </el-form-item>
        <el-form-item label="Description">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="Script Type" prop="script_type">
          <el-radio-group v-model="form.script_type">
            <el-radio-button value="ansible">Ansible</el-radio-button>
            <el-radio-button value="shell">Shell</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="Content" prop="content">
          <el-input v-model="form.content" type="textarea" :rows="15" placeholder="Paste your script here..." />
        </el-form-item>
        <el-alert v-if="error" :title="typeof error === 'string' ? error : JSON.stringify(error)" type="error" show-icon :closable="false" style="margin-bottom:12px" />
        <el-button type="primary" native-type="submit" :loading="loading">Submit for Review</el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api/index.js'
import { ElMessage } from 'element-plus'

const router  = useRouter()
const formRef = ref(null)
const loading = ref(false)
const error   = ref('')
const form = reactive({ title: '', description: '', script_type: 'ansible', content: '' })
const rules = {
  title:       [{ required: true, message: 'Required', trigger: 'blur' }],
  script_type: [{ required: true }],
  content:     [{ required: true, message: 'Content is required', trigger: 'blur' }],
}

async function handleSubmit() {
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    loading.value = true; error.value = ''
    try {
      await api.post('/scripts/', form)
      ElMessage.success('Script submitted for review!')
      router.push('/scripts')
    } catch (err) {
      error.value = err.response?.data?.detail || 'Submission failed'
    } finally {
      loading.value = false
    }
  })
}
</script>
