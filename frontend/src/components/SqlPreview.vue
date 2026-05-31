<template>
  <div class="sql-preview">
    <el-card class="preview-card">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <el-icon><Document /></el-icon>
            <span>SQL 导出预览</span>
          </div>
          <div class="header-right">
            <el-tag type="info" size="small">
              {{ sqlStatements.length }} 条语句
            </el-tag>
            <el-tag type="success" size="small" style="margin-left: 8px">
              {{ formatFileSize(fileSize) }}
            </el-tag>
          </div>
        </div>
      </template>

      <div class="toolbar">
        <el-button-group>
          <el-button size="small" @click="handleCopy" :disabled="!hasSql">
            <el-icon><CopyDocument /></el-icon>
            复制全部
          </el-button>
          <el-button size="small" @click="handleDownload" :disabled="!hasSql">
            <el-icon><Download /></el-icon>
            下载文件
          </el-button>
        </el-button-group>

        <div class="view-options">
          <el-switch
            v-model="wrapText"
            active-text="自动换行"
            inactive-text="不换行"
          />
        </div>
      </div>

      <div class="sql-container" v-if="hasSql">
        <div class="sql-content" :class="{ 'wrap-text': wrapText }">
          <pre><code class="language-sql" v-html="highlightedSql"></code></pre>
        </div>
      </div>

      <el-empty v-else description="暂无 SQL 语句，请先生成数据并导出" />
    </el-card>

    <el-card class="data-preview-card" v-if="hasData">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <el-icon><Grid /></el-icon>
            <span>生成数据预览</span>
          </div>
          <div class="header-right">
            <el-tag type="primary" size="small">
              {{ data.length }} 行数据
            </el-tag>
          </div>
        </div>
      </template>

      <el-table
        :data="paginatedData"
        style="width: 100%"
        max-height="300"
        size="small"
        border
      >
        <el-table-column
          v-for="col in columns"
          :key="col"
          :prop="col"
          :label="col"
          min-width="120"
          show-overflow-tooltip
        />
      </el-table>

      <div class="pagination-container" v-if="data.length > pageSize">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="data.length"
          layout="total, prev, pager, next"
          small
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import hljs from 'highlight.js/lib/core'
import sql from 'highlight.js/lib/languages/sql'
import 'highlight.js/styles/atom-one-dark.css'

hljs.registerLanguage('sql', sql)

const props = defineProps({
  sqlStatements: {
    type: Array,
    default: () => [],
  },
  data: {
    type: Array,
    default: () => [],
  },
  tableName: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['export'])

const wrapText = ref(true)
const currentPage = ref(1)
const pageSize = 20

const hasSql = computed(() => props.sqlStatements.length > 0)
const hasData = computed(() => props.data.length > 0)

const columns = computed(() => {
  if (props.data.length === 0) return []
  return Object.keys(props.data[0])
})

const paginatedData = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  const end = start + pageSize
  return props.data.slice(start, end)
})

const fileSize = computed(() => {
  const text = props.sqlStatements.join('\n')
  return new Blob([text]).size
})

const highlightedSql = computed(() => {
  const sqlText = props.sqlStatements.join('\n')
  if (!sqlText) return ''
  try {
    return hljs.highlight(sqlText, { language: 'sql' }).value
  } catch {
    return sqlText
  }
})

function formatFileSize(bytes) {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

async function handleCopy() {
  try {
    const text = props.sqlStatements.join('\n')
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制到剪贴板')
  } catch (error) {
    ElMessage.error('复制失败: ' + error.message)
  }
}

function handleDownload() {
  const sqlText = props.sqlStatements.join('\n')
  const blob = new Blob([sqlText], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
  link.download = `${props.tableName || 'data'}_${timestamp}.sql`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
  ElMessage.success('文件下载成功')
}

watch(() => props.data, () => {
  currentPage.value = 1
})
</script>

<style scoped>
.sql-preview {
  padding: 16px;
}

.preview-card,
.data-preview-card {
  margin-bottom: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-left {
  display: flex;
  align-items: center;
  font-size: 15px;
  font-weight: 500;
}

.header-left .el-icon {
  margin-right: 8px;
  color: #409eff;
}

.header-right {
  display: flex;
  align-items: center;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 4px;
}

.view-options {
  font-size: 13px;
}

.sql-container {
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  overflow: hidden;
}

.sql-content {
  max-height: 400px;
  overflow: auto;
  background: #282c34;
}

.sql-content.wrap-text {
  white-space: pre-wrap;
  word-break: break-all;
}

.sql-content pre {
  margin: 0;
  padding: 16px;
}

.sql-content code {
  font-family: 'Fira Code', 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  line-height: 1.6;
}

.pagination-container {
  display: flex;
  justify-content: center;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #e4e7ed;
}

:deep(.hljs-keyword) {
  color: #c678dd;
}

:deep(.hljs-string) {
  color: #98c379;
}

:deep(.hljs-number) {
  color: #d19a66;
}

:deep(.hljs-comment) {
  color: #5c6370;
}
</style>
