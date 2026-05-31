<template>
  <el-card class="connection-status-card">
    <template #header>
      <div class="card-header">
        <el-icon class="header-icon"><DataAnalysis /></el-icon>
        <span>连接状态</span>
      </div>
    </template>

    <div class="status-content">
      <!-- 连接状态指示器 -->
      <div class="status-indicator">
        <div class="status-badge" :class="statusClass">
          <el-icon class="status-icon">
            <component :is="statusIcon" />
          </el-icon>
          <span class="status-text">{{ statusText }}</span>
        </div>
      </div>

      <!-- 连接信息 -->
      <div v-if="connected && connectionInfo" class="connection-info">
        <el-divider />

        <div class="info-section">
          <h3 class="info-title">连接详情</h3>

          <div class="info-list">
            <div class="info-item">
              <span class="info-label">数据库类型:</span>
              <el-tag size="small" type="info">{{ connectionInfo.type || config?.type }}</el-tag>
            </div>

            <div v-if="connectionInfo.host" class="info-item">
              <span class="info-label">主机地址:</span>
              <span class="info-value">{{ connectionInfo.host }}</span>
            </div>

            <div v-if="connectionInfo.port" class="info-item">
              <span class="info-label">端口号:</span>
              <span class="info-value">{{ connectionInfo.port }}</span>
            </div>

            <div v-if="connectionInfo.database" class="info-item">
              <span class="info-label">数据库:</span>
              <span class="info-value">{{ connectionInfo.database }}</span>
            </div>

            <div v-if="connectionInfo.username" class="info-item">
              <span class="info-label">用户名:</span>
              <span class="info-value">{{ connectionInfo.username }}</span>
            </div>

            <div v-if="connectionInfo.version" class="info-item">
              <span class="info-label">版本:</span>
              <span class="info-value">{{ connectionInfo.version }}</span>
            </div>

            <div v-if="connectionInfo.charset" class="info-item">
              <span class="info-label">字符集:</span>
              <span class="info-value">{{ connectionInfo.charset }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 错误信息 -->
      <div v-if="error" class="error-section">
        <el-divider />
        <el-alert
          :title="error"
          type="error"
          :closable="false"
          show-icon
        />
      </div>

      <!-- 操作按钮 -->
      <div class="action-buttons">
        <el-button
          v-if="connected"
          type="danger"
          :loading="connecting"
          @click="handleDisconnect"
        >
          <el-icon><SwitchButton /></el-icon>
          断开连接
        </el-button>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useConnectionStore } from '@/stores/connection'

const connectionStore = useConnectionStore()

// 状态
const connected = computed(() => connectionStore.connected)
const connecting = computed(() => connectionStore.connecting)
const config = computed(() => connectionStore.config)
const error = computed(() => connectionStore.error)
const connectionInfo = computed(() => connectionStore.connectionInfo)

// 状态样式
const statusClass = computed(() => {
  if (connecting.value) return 'status-connecting'
  if (connected.value) return 'status-connected'
  return 'status-disconnected'
})

// 状态文本
const statusText = computed(() => {
  if (connecting.value) return '连接中...'
  if (connected.value) return '已连接'
  return '未连接'
})

// 状态图标
const statusIcon = computed(() => {
  if (connecting.value) return 'Loading'
  if (connected.value) return 'CircleCheckFilled'
  return 'CircleCloseFilled'
})

// 断开连接
const handleDisconnect = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要断开数据库连接吗？',
      '确认断开',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const result = await connectionStore.disconnect()

    if (result.success) {
      ElMessage.success('已断开连接')
    } else {
      ElMessage.error(result.message || '断开连接失败')
    }
  } catch (error) {
    // 用户取消操作
    if (error !== 'cancel') {
      ElMessage.error('操作失败')
    }
  }
}
</script>

<style scoped>
.connection-status-card {
  width: 100%;
  max-width: 600px;
}

.card-header {
  display: flex;
  align-items: center;
  font-size: 16px;
  font-weight: 500;
}

.header-icon {
  margin-right: 8px;
  font-size: 20px;
  color: #409eff;
}

.status-content {
  padding: 10px 0;
}

/* 状态指示器 */
.status-indicator {
  display: flex;
  justify-content: center;
  margin-bottom: 20px;
}

.status-badge {
  display: flex;
  align-items: center;
  padding: 12px 24px;
  border-radius: 20px;
  font-size: 16px;
  font-weight: 500;
  transition: all 0.3s ease;
}

.status-icon {
  margin-right: 8px;
  font-size: 20px;
}

.status-connected {
  background-color: #f0f9ff;
  color: #67c23a;
  border: 2px solid #67c23a;
}

.status-disconnected {
  background-color: #fef0f0;
  color: #f56c6c;
  border: 2px solid #f56c6c;
}

.status-connecting {
  background-color: #fdf6ec;
  color: #e6a23c;
  border: 2px solid #e6a23c;
}

.status-connecting .status-icon {
  animation: rotate 1s linear infinite;
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* 连接信息 */
.connection-info {
  margin-top: 20px;
}

.info-section {
  padding: 0 10px;
}

.info-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 16px;
}

.info-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-item {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.info-label {
  min-width: 80px;
  font-size: 13px;
  color: #606266;
  font-weight: 500;
}

.info-value {
  font-size: 13px;
  color: #303133;
  margin-left: 12px;
}

/* 错误信息 */
.error-section {
  margin-top: 20px;
}

/* 操作按钮 */
.action-buttons {
  margin-top: 24px;
  display: flex;
  justify-content: center;
}

.el-divider {
  margin: 16px 0;
}
</style>
