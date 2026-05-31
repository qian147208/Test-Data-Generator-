<template>
  <div class="history-panel">
    <el-card class="history-card">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <el-icon><Clock /></el-icon>
            <span>历史记录</span>
          </div>
          <el-button
            size="small"
            text
            type="danger"
            @click="clearHistory"
            :disabled="history.length === 0"
          >
            清空
          </el-button>
        </div>
      </template>

      <el-empty v-if="history.length === 0" description="暂无历史记录" :image-size="80" />

      <el-timeline v-else>
        <el-timeline-item
          v-for="(record, index) in history"
          :key="index"
          :timestamp="formatTime(record.timestamp)"
          placement="top"
          :type="getRecordType(record.type)"
        >
          <el-card class="history-item" shadow="hover">
            <div class="record-header">
              <el-tag :type="getRecordType(record.type)" size="small">
                {{ record.type === 'generate' ? '生成' : '导出' }}
              </el-tag>
              <span class="table-name">{{ record.tableName }}</span>
            </div>

            <div class="record-details">
              <template v-if="record.type === 'generate'">
                <span class="detail-item">
                  <el-icon><DataLine /></el-icon>
                  {{ record.rowCount }} 行
                </span>
                <span class="detail-item">
                  <el-icon><Operation /></el-icon>
                  {{ getStrategyLabel(record.strategy) }}
                </span>
              </template>
              <template v-else>
                <span class="detail-item">
                  <el-icon><DataLine /></el-icon>
                  {{ record.rowCount }} 行
                </span>
                <span class="detail-item">
                  <el-icon><Document /></el-icon>
                  {{ record.sqlCount }} 条 SQL
                </span>
              </template>
            </div>

            <div class="record-actions">
              <el-button
                size="small"
                text
                @click="handleRerun(record)"
                v-if="record.type === 'generate'"
              >
                <el-icon><RefreshRight /></el-icon>
                重新生成
              </el-button>
            </div>
          </el-card>
        </el-timeline-item>
      </el-timeline>
    </el-card>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useGenerateStore } from '@/stores/generate'

const emit = defineEmits(['rerun'])

const generateStore = useGenerateStore()

const history = computed(() => generateStore.history)

function formatTime(timestamp) {
  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function getRecordType(type) {
  return type === 'generate' ? 'primary' : 'success'
}

function getStrategyLabel(strategy) {
  const labels = {
    normal: '正常',
    boundary: '边界值',
    abnormal: '异常',
    mixed: '混合',
  }
  return labels[strategy] || strategy
}

async function handleRerun(record) {
  try {
    await ElMessageBox.confirm(
      `确定要重新生成表 "${record.tableName}" 的数据吗？`,
      '重新生成',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'info',
      }
    )

    emit('rerun', record)
  } catch {
    // 用户取消
  }
}

function clearHistory() {
  ElMessageBox.confirm(
    '确定要清空所有历史记录吗？',
    '清空历史',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    }
  ).then(() => {
    generateStore.history = []
    ElMessage.success('历史记录已清空')
  }).catch(() => {})
}
</script>

<style scoped>
.history-panel {
  padding: 16px;
}

.history-card {
  height: 100%;
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

.history-item {
  margin-bottom: 0;
}

.record-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.table-name {
  font-weight: 500;
  color: #303133;
}

.record-details {
  display: flex;
  gap: 16px;
  margin-bottom: 8px;
}

.detail-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: #606266;
}

.detail-item .el-icon {
  font-size: 14px;
  color: #909399;
}

.record-actions {
  display: flex;
  justify-content: flex-end;
}

:deep(.el-timeline-item__timestamp) {
  font-size: 12px;
}
</style>
