<template>
  <div class="table-details" v-loading="loading">
    <!-- 表基本信息 -->
    <div class="table-header" v-if="tableDetails">
      <div class="header-left">
        <el-icon class="table-icon"><Grid /></el-icon>
        <div class="table-meta">
          <h2 class="table-name">{{ tableName }}</h2>
          <p class="table-comment" v-if="tableDetails.comment || tableDetails.table_comment">
            {{ tableDetails.comment || tableDetails.table_comment }}
          </p>
        </div>
      </div>
      <div class="header-right">
        <el-tag type="primary" size="large">
          {{ columns.length }} 个字段
        </el-tag>
      </div>
    </div>

    <!-- 字段列表 -->
    <el-card class="section-card" shadow="never">
      <template #header>
        <div class="section-header">
          <el-icon><List /></el-icon>
          <span>字段列表</span>
        </div>
      </template>
      <el-table :data="columns" border stripe max-height="400">
        <el-table-column prop="name" label="字段名" min-width="150">
          <template #default="{ row }">
            <div class="field-name">
              <span>{{ row.name || row.column_name }}</span>
              <el-icon v-if="row.is_primary || row.is_primary_key" class="primary-icon"><Key /></el-icon>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="type" label="类型" min-width="120">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ row.type || row.data_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="nullable" label="可空" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="(row.nullable || row.is_nullable) ? 'warning' : 'danger'" size="small">
              {{ (row.nullable || row.is_nullable) ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="default" label="默认值" min-width="100">
          <template #default="{ row }">
            <span class="default-value">{{ row.default || row.default_value || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="is_primary" label="主键" width="80" align="center">
          <template #default="{ row }">
            <el-icon v-if="row.is_primary || row.is_primary_key" class="check-icon"><Check /></el-icon>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="is_unique" label="唯一" width="80" align="center">
          <template #default="{ row }">
            <el-icon v-if="row.is_unique" class="check-icon"><Check /></el-icon>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="comment" label="注释" min-width="150">
          <template #default="{ row }">
            <span class="comment-text">{{ row.comment || row.column_comment || '-' }}</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 主键信息 -->
    <el-card class="section-card" shadow="never" v-if="primaryKeys.length > 0">
      <template #header>
        <div class="section-header">
          <el-icon><Key /></el-icon>
          <span>主键信息</span>
        </div>
      </template>
      <div class="primary-keys">
        <el-tag
          v-for="pk in primaryKeys"
          :key="pk.name || pk"
          type="success"
          size="large"
          class="pk-tag"
        >
          <el-icon><Key /></el-icon>
          {{ pk.name || pk }}
        </el-tag>
      </div>
    </el-card>

    <!-- 外键关系 -->
    <el-card class="section-card" shadow="never" v-if="foreignKeys.length > 0">
      <template #header>
        <div class="section-header">
          <el-icon><Connection /></el-icon>
          <span>外键关系</span>
        </div>
      </template>
      <el-table :data="foreignKeys" border stripe>
        <el-table-column prop="name" label="外键名" min-width="150">
          <template #default="{ row }">
            {{ row.name || row.constraint_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="column" label="本地字段" min-width="120">
          <template #default="{ row }">
            <el-tag type="primary" size="small">{{ row.column || row.column_name }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="referenced_table" label="关联表" min-width="120">
          <template #default="{ row }">
            <el-tag type="success" size="small">{{ row.referenced_table || row.ref_table_name }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="referenced_column" label="关联字段" min-width="120">
          <template #default="{ row }">
            <el-tag type="warning" size="small">{{ row.referenced_column || row.ref_column_name }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 索引信息 -->
    <el-card class="section-card" shadow="never" v-if="indexes.length > 0">
      <template #header>
        <div class="section-header">
          <el-icon><Collection /></el-icon>
          <span>索引信息</span>
        </div>
      </template>
      <el-table :data="indexes" border stripe>
        <el-table-column prop="name" label="索引名" min-width="150">
          <template #default="{ row }">
            {{ row.name || row.index_name }}
          </template>
        </el-table-column>
        <el-table-column prop="columns" label="字段" min-width="150">
          <template #default="{ row }">
            <div class="index-columns">
              <el-tag
                v-for="(col, idx) in getIndexColumns(row)"
                :key="idx"
                size="small"
                class="index-col-tag"
              >
                {{ col }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="is_unique" label="唯一索引" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_unique || row.unique ? 'success' : 'info'" size="small">
              {{ row.is_unique || row.unique ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="type" label="索引类型" min-width="100">
          <template #default="{ row }">
            {{ row.type || row.index_type || '-' }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 外键关系图 -->
    <el-card class="section-card" shadow="never" v-if="foreignKeys.length > 0">
      <template #header>
        <div class="section-header">
          <el-icon><Share /></el-icon>
          <span>关系图</span>
        </div>
      </template>
      <ForeignKeyDiagram
        :table-name="tableName"
        :foreign-keys="foreignKeys"
      />
    </el-card>

    <!-- 空状态 -->
    <el-empty v-if="!loading && !tableDetails" description="请选择一个表查看详情" />
  </div>
</template>

<script setup>
import { computed, watch } from 'vue'
import { useTablesStore } from '@/stores/tables'
import { storeToRefs } from 'pinia'
import ForeignKeyDiagram from './ForeignKeyDiagram.vue'

const tablesStore = useTablesStore()
const { currentTable, currentTableDetails, loading } = storeToRefs(tablesStore)

// 表名
const tableName = computed(() => {
  if (!currentTable.value) return ''
  return currentTable.value.table_name
})

// 表详情
const tableDetails = computed(() => currentTableDetails.value)

// 字段列表
const columns = computed(() => {
  if (!tableDetails.value) return []
  return tableDetails.value.columns || tableDetails.value.fields || []
})

// 主键列表
const primaryKeys = computed(() => {
  if (!tableDetails.value) return []
  const pks = tableDetails.value.primary_keys || tableDetails.value.primaryKeys || []
  // 也可以从 columns 中筛选主键
  const pkFromColumns = columns.value.filter(col => col.is_primary || col.is_primary_key)
  if (pks.length > 0) return pks
  return pkFromColumns.map(col => ({ name: col.name || col.column_name }))
})

// 外键列表
const foreignKeys = computed(() => {
  if (!tableDetails.value) return []
  return tableDetails.value.foreign_keys || tableDetails.value.foreignKeys || []
})

// 索引列表
const indexes = computed(() => {
  if (!tableDetails.value) return []
  return tableDetails.value.indexes || []
})

// 获取索引字段列表
const getIndexColumns = (index) => {
  if (index.columns) {
    return Array.isArray(index.columns) ? index.columns : index.columns.split(',')
  }
  if (index.column_name) {
    return [index.column_name]
  }
  return []
}

// 监听当前表变化，加载详情
watch(currentTable, async (newTable) => {
  if (newTable) {
    const name = newTable.name || newTable.table_name
    if (!tablesStore.tableDetails[name]) {
      await tablesStore.fetchTableDetails(name)
    }
  }
}, { immediate: true })
</script>

<style scoped>
.table-details {
  height: 100%;
  overflow-y: auto;
  padding: 20px;
  background: #f5f7fa;
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 8px;
  margin-bottom: 20px;
  color: #fff;
}

.header-left {
  display: flex;
  align-items: center;
}

.table-icon {
  font-size: 40px;
  margin-right: 16px;
}

.table-meta {
  display: flex;
  flex-direction: column;
}

.table-name {
  font-size: 24px;
  font-weight: 600;
  margin: 0 0 4px 0;
}

.table-comment {
  font-size: 14px;
  margin: 0;
  opacity: 0.9;
}

.section-card {
  margin-bottom: 20px;
}

.section-card :deep(.el-card__header) {
  padding: 12px 20px;
  background: #fafafa;
}

.section-header {
  display: flex;
  align-items: center;
  font-size: 16px;
  font-weight: 500;
}

.section-header .el-icon {
  margin-right: 8px;
  color: #409eff;
}

.field-name {
  display: flex;
  align-items: center;
  gap: 6px;
}

.primary-icon {
  color: #e6a23c;
  font-size: 14px;
}

.check-icon {
  color: #67c23a;
  font-size: 16px;
}

.default-value {
  font-family: monospace;
  font-size: 12px;
  color: #606266;
}

.comment-text {
  font-size: 12px;
  color: #909399;
}

.primary-keys {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.pk-tag {
  display: flex;
  align-items: center;
  gap: 6px;
}

.index-columns {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.index-col-tag {
  margin: 2px;
}

/* 滚动条样式 */
.table-details::-webkit-scrollbar {
  width: 6px;
}

.table-details::-webkit-scrollbar-thumb {
  background: #c0c4cc;
  border-radius: 3px;
}

.table-details::-webkit-scrollbar-track {
  background: #f5f7fa;
}
</style>
