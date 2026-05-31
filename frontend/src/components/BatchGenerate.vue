<template>
  <div class="batch-generate">
    <el-card class="select-card">
      <template #header>
        <div class="card-header">
          <el-icon><List /></el-icon>
          <span>选择表</span>
          <el-tag type="info" size="small" style="margin-left: 8px">
            已选择 {{ selectedTables.length }} 个表
          </el-tag>
        </div>
      </template>

      <div class="table-select-container">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索表名..."
          clearable
          style="margin-bottom: 12px"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>

        <el-checkbox-group v-model="selectedTables" class="table-checkbox-group">
          <div
            v-for="table in filteredTables"
            :key="table.name || table.table_name"
            class="table-checkbox-item"
          >
            <el-checkbox
              :label="table.name || table.table_name"
              :value="table.name || table.table_name"
            >
              <div class="table-info">
                <span class="table-name">{{ table.name || table.table_name }}</span>
                <span class="table-comment" v-if="table.comment || table.table_comment">
                  {{ table.comment || table.table_comment }}
                </span>
              </div>
            </el-checkbox>
          </div>
        </el-checkbox-group>

        <div class="select-actions">
          <el-button size="small" @click="selectAll">全选</el-button>
          <el-button size="small" @click="clearSelection">清除选择</el-button>
        </div>
      </div>
    </el-card>

    <el-card class="dependency-card" v-if="selectedTables.length > 0">
      <template #header>
        <div class="card-header">
          <el-icon><Share /></el-icon>
          <span>依赖关系</span>
        </div>
      </template>

      <div class="dependency-info">
        <el-alert
          v-if="hasCircularDependency"
          title="检测到循环依赖"
          type="warning"
          :closable="false"
          show-icon
          style="margin-bottom: 12px"
        >
          存在循环依赖的表，生成顺序可能需要手动调整
        </el-alert>

        <div class="generation-order">
          <div class="order-label">建议生成顺序：</div>
          <div class="order-list">
            <el-tag
              v-for="(table, index) in generationOrder"
              :key="table"
              :type="getOrderTagType(index)"
              effect="plain"
              class="order-tag"
            >
              {{ index + 1 }}. {{ table }}
            </el-tag>
          </div>
        </div>

        <div class="dependency-graph">
          <ForeignKeyDiagram
            v-if="selectedTables.length <= 10"
            :tables="selectedTables"
            :foreign-keys="relevantForeignKeys"
          />
        </div>
      </div>
    </el-card>

    <el-card class="config-card">
      <template #header>
        <div class="card-header">
          <el-icon><Setting /></el-icon>
          <span>批量生成配置</span>
        </div>
      </template>

      <el-form :model="batchConfig" label-width="100px">
        <el-form-item label="生成策略">
          <el-select v-model="batchConfig.strategy" style="width: 100%">
            <el-option label="正常数据" value="normal" />
            <el-option label="边界值" value="boundary" />
            <el-option label="异常数据" value="abnormal" />
            <el-option label="混合模式" value="mixed" />
          </el-select>
        </el-form-item>

        <el-form-item label="每表行数">
          <el-input-number
            v-model="batchConfig.countPerTable"
            :min="1"
            :max="10000"
            :step="10"
            style="width: 100%"
          />
        </el-form-item>

        <el-form-item label="语言区域">
          <el-select v-model="batchConfig.locale" style="width: 100%">
            <el-option label="中文 (中国)" value="zh_CN" />
            <el-option label="英文 (美国)" value="en_US" />
          </el-select>
        </el-form-item>

        <el-form-item label="依赖顺序">
          <el-switch
            v-model="batchConfig.respectDependencies"
            active-text="按依赖顺序生成"
            inactive-text="忽略依赖"
          />
        </el-form-item>
      </el-form>
    </el-card>

    <div class="action-buttons">
      <el-button
        type="primary"
        :loading="generating"
        :disabled="selectedTables.length === 0"
        @click="handleBatchGenerate"
      >
        <el-icon><MagicStick /></el-icon>
        批量生成
      </el-button>

      <el-button
        :disabled="batchResults.length === 0"
        @click="handleBatchExport"
      >
        <el-icon><Download /></el-icon>
        导出全部 SQL
      </el-button>
    </div>

    <el-card class="results-card" v-if="batchResults.length > 0">
      <template #header>
        <div class="card-header">
          <el-icon><SuccessFilled /></el-icon>
          <span>生成结果</span>
        </div>
      </template>

      <el-table :data="batchResults" style="width: 100%" size="small">
        <el-table-column prop="table_name" label="表名" width="180" />
        <el-table-column prop="strategy" label="策略" width="100" />
        <el-table-column prop="total_rows" label="行数" width="100">
          <template #default="{ row }">
            <el-tag type="success" size="small">{{ row.total_rows }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.error ? 'danger' : 'success'" size="small">
              {{ row.error ? '失败' : '成功' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="warnings" label="警告">
          <template #default="{ row }">
            <span v-if="row.warnings && row.warnings.length > 0" class="warning-text">
              {{ row.warnings.join(', ') }}
            </span>
            <span v-else class="no-warning">-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button
              size="small"
              text
              @click="previewTableData(row)"
              :disabled="!row.data || row.data.length === 0"
            >
              预览
            </el-button>
            <el-button
              size="small"
              text
              @click="exportTableSql(row)"
              :disabled="!row.data || row.data.length === 0"
            >
              导出
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog
      v-model="previewVisible"
      :title="`数据预览 - ${previewTableName}`"
      width="80%"
      destroy-on-close
    >
      <el-table :data="previewData" style="width: 100%" max-height="400" size="small">
        <el-table-column
          v-for="col in previewColumns"
          :key="col"
          :prop="col"
          :label="col"
          min-width="120"
          show-overflow-tooltip
        />
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { generateBatchApi, exportBatchSqlApi } from '@/api/generate'
import { useTablesStore } from '@/stores/tables'
import ForeignKeyDiagram from './ForeignKeyDiagram.vue'

const tablesStore = useTablesStore()

const searchKeyword = ref('')
const selectedTables = ref([])
const generating = ref(false)
const batchResults = ref([])
const previewVisible = ref(false)
const previewData = ref([])
const previewTableName = ref('')

const batchConfig = reactive({
  strategy: 'normal',
  countPerTable: 10,
  locale: 'zh_CN',
  respectDependencies: true,
})

const filteredTables = computed(() => {
  const tables = tablesStore.tables || []
  if (!searchKeyword.value) {
    return tables
  }
  const keyword = searchKeyword.value.toLowerCase()
  return tables.filter(table => {
    const name = (table.name || table.table_name || '').toLowerCase()
    const comment = (table.comment || table.table_comment || '').toLowerCase()
    return name.includes(keyword) || comment.includes(keyword)
  })
})

const generationOrder = computed(() => {
  return selectedTables.value
})

const hasCircularDependency = computed(() => {
  return false
})

const relevantForeignKeys = computed(() => {
  const fks = []
  selectedTables.value.forEach(tableName => {
    const details = tablesStore.tableDetails[tableName]
    if (details && details.foreign_keys) {
      details.foreign_keys.forEach(fk => {
        if (selectedTables.value.includes(fk.referred_table)) {
          fks.push({
            ...fk,
            constrained_table: tableName,
          })
        }
      })
    }
  })
  return fks
})

const previewColumns = computed(() => {
  if (previewData.value.length === 0) return []
  return Object.keys(previewData.value[0])
})

function selectAll() {
  selectedTables.value = filteredTables.value.map(t => t.name || t.table_name)
}

function clearSelection() {
  selectedTables.value = []
}

function getOrderTagType(index) {
  const types = ['success', 'primary', 'warning', 'info', 'danger']
  return types[index % types.length]
}

async function handleBatchGenerate() {
  if (selectedTables.value.length === 0) {
    ElMessage.warning('请至少选择一个表')
    return
  }

  generating.value = true
  batchResults.value = []

  try {
    const result = await generateBatchApi({
      tables: selectedTables.value,
      count_per_table: batchConfig.countPerTable,
      strategy: batchConfig.strategy,
      respect_dependencies: batchConfig.respectDependencies,
      locale: batchConfig.locale,
    })

    const results = result.results || {}
    const errors = result.errors || []

    batchResults.value = selectedTables.value.map(tableName => {
      const tableResult = results[tableName]
      return {
        table_name: tableName,
        strategy: batchConfig.strategy,
        total_rows: tableResult?.total_rows || 0,
        data: tableResult?.data || [],
        warnings: tableResult?.warnings || [],
        error: errors.find(e => e.includes(tableName)),
      }
    })

    const successCount = Object.keys(results).length
    ElMessage.success(`批量生成完成: ${successCount}/${selectedTables.value.length} 个表`)
  } catch (error) {
    ElMessage.error('批量生成失败: ' + error.message)
  } finally {
    generating.value = false
  }
}

async function handleBatchExport() {
  const tablesData = {}
  batchResults.value.forEach(result => {
    if (result.data && result.data.length > 0) {
      tablesData[result.table_name] = result.data
    }
  })

  if (Object.keys(tablesData).length === 0) {
    ElMessage.warning('没有可导出的数据')
    return
  }

  try {
    const result = await exportBatchSqlApi({
      tables_data: tablesData,
      batch_size: 100,
    })

    const sqlContent = result.sql_statements.join('\n')
    const blob = new Blob([sqlContent], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
    link.download = `batch_export_${timestamp}.sql`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)

    ElMessage.success('SQL 文件下载成功')
  } catch (error) {
    ElMessage.error('导出失败: ' + error.message)
  }
}

function previewTableData(row) {
  previewTableName.value = row.table_name
  previewData.value = row.data || []
  previewVisible.value = true
}

async function exportTableSql(row) {
  if (!row.data || row.data.length === 0) {
    ElMessage.warning('没有可导出的数据')
    return
  }

  const columns = Object.keys(row.data[0])
  const sqlStatements = row.data.map(dataRow => {
    const values = columns.map(col => {
      const val = dataRow[col]
      if (val === null || val === undefined) return 'NULL'
      if (typeof val === 'string') return `'${val.replace(/'/g, "''")}'`
      if (val instanceof Date) return `'${val.toISOString()}'`
      return val
    })
    return `INSERT INTO \`${row.table_name}\` (\`${columns.join('`, `')}\`) VALUES (${values.join(', ')});`
  })

  const sqlContent = sqlStatements.join('\n')
  const blob = new Blob([sqlContent], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
  link.download = `${row.table_name}_${timestamp}.sql`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)

  ElMessage.success('SQL 文件下载成功')
}
</script>

<style scoped>
.batch-generate {
  padding: 16px;
}

.select-card,
.dependency-card,
.config-card,
.results-card {
  margin-bottom: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  font-size: 15px;
  font-weight: 500;
}

.card-header .el-icon {
  margin-right: 8px;
  color: #409eff;
}

.table-select-container {
  max-height: 300px;
  overflow-y: auto;
}

.table-checkbox-group {
  width: 100%;
}

.table-checkbox-item {
  padding: 8px 12px;
  border-bottom: 1px solid #f0f0f0;
}

.table-checkbox-item:last-child {
  border-bottom: none;
}

.table-info {
  display: flex;
  flex-direction: column;
}

.table-name {
  font-weight: 500;
}

.table-comment {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}

.select-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #e4e7ed;
}

.dependency-info {
  padding: 8px 0;
}

.generation-order {
  margin-bottom: 16px;
}

.order-label {
  font-weight: 500;
  margin-bottom: 8px;
}

.order-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.order-tag {
  margin: 0;
}

.warning-text {
  color: #e6a23c;
  font-size: 12px;
}

.no-warning {
  color: #c0c4cc;
}

.action-buttons {
  display: flex;
  gap: 12px;
  justify-content: center;
  padding: 16px 0;
}
</style>
