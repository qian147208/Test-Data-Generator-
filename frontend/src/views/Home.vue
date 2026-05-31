<template>
  <div class="home-container">
    <!-- 顶部导航栏 -->
    <header class="app-header">
      <div class="header-content">
        <div class="logo-section">
          <el-icon class="logo-icon"><DataAnalysis /></el-icon>
          <h1 class="app-title">测试数据生成工具</h1>
        </div>
        <div class="header-actions">
          <el-tooltip content="关于工具" placement="bottom">
            <el-button circle :icon="InfoFilled" class="header-btn" />
          </el-tooltip>
          <el-tooltip content="设置" placement="bottom">
            <el-button circle :icon="Setting" class="header-btn" @click="showSettings = true" />
          </el-tooltip>
        </div>
      </div>
    </header>

    <!-- 主内容区域 -->
    <main class="app-main">
      <!-- 未连接状态 -->
      <div class="disconnected-view" v-if="!connected">
        <div class="disconnected-content">
          <!-- 连接配置区域 -->
          <div class="connection-card">
            <div class="card-header">
              <el-icon class="card-icon"><Connection /></el-icon>
              <h2 class="card-title">数据库连接</h2>
            </div>
            <ConnectionForm />
          </div>

          <!-- 信息区域 -->
          <div class="info-card">
            <div class="card-header">
              <el-icon class="card-icon"><InfoFilled /></el-icon>
              <h2 class="card-title">使用指南</h2>
            </div>
            <div class="info-content">
              <div class="steps-container">
                <div class="step-item" v-for="(step, index) in steps" :key="index">
                  <div class="step-number">{{ index + 1 }}</div>
                  <div class="step-content">
                    <h3 class="step-title">{{ step.title }}</h3>
                    <p class="step-description">{{ step.description }}</p>
                  </div>
                </div>
              </div>
              
              <div class="database-support">
                <h3 class="support-title">支持的数据库</h3>
                <div class="database-tags">
                  <el-tag size="large" effect="dark" class="database-tag">MySQL</el-tag>
                  <el-tag size="large" effect="dark" class="database-tag">PostgreSQL</el-tag>
                  <el-tag size="large" effect="dark" class="database-tag">SQLite</el-tag>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 已连接状态 -->
      <div class="connected-view" v-else>
        <!-- 顶部连接状态栏 -->
        <div class="connection-status-bar">
          <ConnectionStatus />
        </div>

        <!-- 主工作区 -->
        <div class="workspace">
          <!-- 左侧表列表 -->
          <aside class="table-sidebar">
            <div class="sidebar-header">
              <el-icon class="sidebar-icon"><Grid /></el-icon>
              <h3 class="sidebar-title">数据表</h3>
            </div>
            <TableList />
          </aside>

          <!-- 右侧工作区 -->
          <section class="main-content-area">
            <!-- 标签页导航 -->
            <div class="tab-navigation">
              <el-tabs v-model="activeTab" class="modern-tabs" stretch>
                <el-tab-pane label="表结构" name="structure">
                  <div class="tab-content">
                    <TableDetails />
                  </div>
                </el-tab-pane>
                <el-tab-pane label="生成配置" name="generate">
                  <div class="tab-content">
                    <GenerateConfig
                      :table-name="currentTableName"
                      @generated="handleGenerated"
                    />
                  </div>
                </el-tab-pane>
                <el-tab-pane label="SQL 导出" name="export">
                  <div class="tab-content">
                    <SqlPreview
                      :sql-statements="sqlStatements"
                      :data="generatedData"
                      :table-name="currentTableName"
                    />
                  </div>
                </el-tab-pane>
                <el-tab-pane label="批量生成" name="batch">
                  <div class="tab-content">
                    <BatchGenerate />
                  </div>
                </el-tab-pane>
                <el-tab-pane label="依赖关系" name="dependencies">
                  <div class="tab-content">
                    <TableDependencies
                      :table-name="currentTableName"
                      @table-click="handleTableClick"
                    />
                  </div>
                </el-tab-pane>
              </el-tabs>
            </div>
          </section>
        </div>
      </div>
    </main>

    <!-- 设置对话框 -->
    <el-dialog
      title="设置"
      v-model="showSettings"
      width="400px"
      :close-on-click-modal="false"
    >
      <div class="settings-content">
        <div class="settings-section">
          <h3 class="section-title">数据生成设置</h3>
          <div class="setting-item">
            <span class="setting-label">默认生成数量</span>
            <el-input-number
              v-model="generateStore.defaultCount"
              :min="1"
              :max="10000"
              class="setting-input"
            />
          </div>
          <div class="setting-item">
            <span class="setting-label">批量生成数量上限</span>
            <el-input-number
              v-model="generateStore.batchLimit"
              :min="10"
              :max="100000"
              class="setting-input"
            />
          </div>
        </div>
        <div class="settings-section">
          <h3 class="section-title">SQL 设置</h3>
          <div class="setting-item">
            <span class="setting-label">SQL 语句分隔符</span>
            <el-input
              v-model="generateStore.sqlDelimiter"
              class="setting-input"
            />
          </div>
          <div class="setting-item">
            <span class="setting-label">包含自增主键</span>
            <el-switch
              v-model="generateStore.includeAutoIncrement"
            />
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="showSettings = false">取消</el-button>
        <el-button type="primary" @click="saveSettings">保存设置</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useConnectionStore } from '@/stores/connection'
import { useTablesStore } from '@/stores/tables'
import { useGenerateStore } from '@/stores/generate'
import ConnectionForm from '@/components/ConnectionForm.vue'
import ConnectionStatus from '@/components/ConnectionStatus.vue'
import TableList from '@/components/TableList.vue'
import TableDetails from '@/components/TableDetails.vue'
import GenerateConfig from '@/components/GenerateConfig.vue'
import SqlPreview from '@/components/SqlPreview.vue'
import BatchGenerate from '@/components/BatchGenerate.vue'
import TableDependencies from '@/components/TableDependencies.vue'
import { DataAnalysis, InfoFilled, Setting, Connection, Grid } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const connectionStore = useConnectionStore()
const tablesStore = useTablesStore()
const generateStore = useGenerateStore()

const activeTab = ref('structure')
const showSettings = ref(false)

// 使用指南步骤数据
const steps = [
  {
    title: '连接数据库',
    description: '选择数据库类型并填写连接信息，建立数据库连接'
  },
  {
    title: '选择目标表',
    description: '从表列表中选择需要生成测试数据的表'
  },
  {
    title: '配置生成规则',
    description: '设置生成策略、数量，可选配置字段级别规则'
  },
  {
    title: '生成并导出',
    description: '生成测试数据，预览并导出 SQL INSERT 语句'
  }
]

const connected = computed(() => connectionStore.connected)
const currentTableName = computed(() => {
  const table = tablesStore.currentTable
  return table ? (table.name || table.table_name) : ''
})
const generatedData = computed(() => generateStore.generatedData)
const sqlStatements = computed(() => generateStore.sqlStatements)

watch(connected, async (newVal) => {
  if (newVal) {
    await tablesStore.fetchTables()
  } else {
    tablesStore.reset()
    generateStore.reset()
  }
})

watch(currentTableName, (newVal) => {
  if (newVal) {
    generateStore.setTableName(newVal)
    activeTab.value = 'structure'
  }
})

onMounted(async () => {
  await connectionStore.getStatus()
  if (connectionStore.connected) {
    await tablesStore.fetchTables()
  }
})

async function handleGenerated(data) {
  activeTab.value = 'export'
  try {
    await generateStore.exportSql()
  } catch (error) {
    console.error('导出 SQL 失败:', error)
  }
}

async function handleTableClick(table) {
  await tablesStore.selectTable(table)
  activeTab.value = 'structure'
}

function saveSettings() {
  showSettings.value = false
  ElMessage.success('设置已保存')
}
</script>

<style scoped>
/* 全局样式 */
.home-container {
  width: 100%;
  min-height: 100vh;
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
  color: #f8fafc;
  display: flex;
  flex-direction: column;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

/* 顶部导航栏 */
.app-header {
  background: rgba(15, 23, 42, 0.8);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(96, 165, 250, 0.1);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  min-height: 70px;
  z-index: 100;
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 24px;
  height: 70px;
}

.logo-section {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-icon {
  font-size: 32px;
  color: #60a5fa;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.05);
    color: #3b82f6;
  }
  100% {
    transform: scale(1);
  }
}

.app-title {
  font-size: 24px;
  font-weight: 700;
  margin: 0;
  background: linear-gradient(90deg, #60a5fa, #3b82f6);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.header-btn {
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05);
  color: #f8fafc;
  transition: all 0.3s ease;
}

.header-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(96, 165, 250, 0.5);
  transform: translateY(-2px);
}

/* 主内容区域 */
.app-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 24px;
}

/* 未连接状态 */
.disconnected-view {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.disconnected-content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 32px;
  max-width: 1200px;
  width: 100%;
}

.connection-card,
.info-card {
  background: rgba(30, 41, 59, 0.8);
  border: 1px solid rgba(96, 165, 250, 0.1);
  border-radius: 16px;
  backdrop-filter: blur(10px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  overflow: hidden;
  transition: all 0.3s ease;
}

.connection-card:hover,
.info-card:hover {
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
  transform: translateY(-4px);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 24px;
  border-bottom: 1px solid rgba(96, 165, 250, 0.1);
  background: rgba(15, 23, 42, 0.6);
}

.card-icon {
  font-size: 24px;
  color: #3b82f6;
}

.card-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
  color: #f8fafc;
}

.info-content {
  padding: 24px;
}

/* 步骤容器 */
.steps-container {
  display: flex;
  flex-direction: column;
  gap: 24px;
  margin-bottom: 32px;
}

.step-item {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}

.step-number {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, #3b82f6, #60a5fa);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 14px;
  color: #0f172a;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
}

.step-content {
  flex: 1;
}

.step-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 8px 0;
  color: #f8fafc;
}

.step-description {
  font-size: 14px;
  color: #cbd5e1;
  margin: 0;
  line-height: 1.6;
}

/* 数据库支持 */
.database-support {
  border-top: 1px solid rgba(96, 165, 250, 0.1);
  padding-top: 24px;
}

.support-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 16px 0;
  color: #f8fafc;
}

.database-tags {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.database-tag {
  background: rgba(96, 165, 250, 0.1);
  border: 1px solid rgba(96, 165, 250, 0.3);
  color: #60a5fa;
  font-weight: 500;
  transition: all 0.3s ease;
}

.database-tag:hover {
  background: rgba(96, 165, 250, 0.2);
  transform: translateY(-2px);
}

/* 已连接状态 */
.connected-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.connection-status-bar {
  background: rgba(30, 41, 59, 0.8);
  border: 1px solid rgba(96, 165, 250, 0.1);
  border-radius: 12px;
  padding: 16px 24px;
  backdrop-filter: blur(10px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

/* 工作区 */
.workspace {
  flex: 1;
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 24px;
  min-height: 0;
}

/* 左侧表列表 */
.table-sidebar {
  background: rgba(30, 41, 59, 0.8);
  border: 1px solid rgba(96, 165, 250, 0.1);
  border-radius: 16px;
  backdrop-filter: blur(10px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 24px;
  border-bottom: 1px solid rgba(96, 165, 250, 0.1);
  background: rgba(15, 23, 42, 0.6);
}

.sidebar-icon {
  font-size: 20px;
  color: #3b82f6;
}

.sidebar-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0;
  color: #f8fafc;
}

/* 右侧工作区 */
.main-content-area {
  background: rgba(30, 41, 59, 0.8);
  border: 1px solid rgba(96, 165, 250, 0.1);
  border-radius: 16px;
  backdrop-filter: blur(10px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* 标签页导航 */
.tab-navigation {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.modern-tabs {
  height: 100%;
  display: flex;
  flex-direction: column;
}

:deep(.el-tabs__header) {
  background: rgba(15, 23, 42, 0.6);
  border-bottom: 1px solid rgba(96, 165, 255, 0.1);
  padding: 0 24px;
}

:deep(.el-tabs__nav) {
  height: 60px;
}

:deep(.el-tabs__item) {
  height: 60px;
  line-height: 60px;
  font-size: 14px;
  font-weight: 500;
  color: #94a3b8;
  transition: all 0.3s ease;
  margin-right: 32px;
}

:deep(.el-tabs__item:hover) {
  color: #f8fafc;
}

:deep(.el-tabs__item.is-active) {
  color: #3b82f6;
  font-weight: 600;
}

:deep(.el-tabs__active-bar) {
  background: linear-gradient(90deg, #3b82f6, #60a5fa);
  height: 3px;
  border-radius: 3px;
}

:deep(.el-tabs__content) {
  flex: 1;
  overflow: auto;
  padding: 24px;
}

.tab-content {
  height: 100%;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .disconnected-content {
    grid-template-columns: 1fr;
  }
  
  .workspace {
    grid-template-columns: 280px 1fr;
  }
}

@media (max-width: 768px) {
  .app-main {
    padding: 16px;
  }
  
  .header-content {
    padding: 0 16px;
  }
  
  .app-title {
    font-size: 20px;
  }
  
  .workspace {
    grid-template-columns: 1fr;
    grid-template-rows: 250px 1fr;
  }
  
  .table-sidebar {
    border-radius: 12px;
  }
  
  .main-content-area {
    border-radius: 12px;
  }
  
  :deep(.el-tabs__content) {
    padding: 16px;
  }
  
  .card-header {
    padding: 16px 20px;
  }
  
  .info-content {
    padding: 20px;
  }
}

/* 滚动条样式 */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: rgba(15, 23, 42, 0.5);
  border-radius: 4px;
}

::-webkit-scrollbar-thumb {
  background: rgba(59, 130, 246, 0.5);
  border-radius: 4px;
  transition: all 0.3s ease;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(59, 130, 246, 0.7);
}

/* 加载动画 */
.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  width: 100%;
}

/* 动画效果 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-enter-active,
.slide-leave-active {
  transition: all 0.3s ease;
}

.slide-enter-from {
  transform: translateX(-20px);
  opacity: 0;
}

.slide-leave-to {
  transform: translateX(20px);
  opacity: 0;
}
</style>
