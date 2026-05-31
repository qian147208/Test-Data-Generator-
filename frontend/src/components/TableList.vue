<template>
  <div class="table-list">
    <!-- 搜索框 -->
    <div class="search-box">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索表名或注释"
        clearable
        @input="handleSearch"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
    </div>

    <!-- 表列表 -->
    <div class="list-container" v-loading="loading">
      <el-scrollbar>
        <div class="table-items">
          <div
            v-for="table in filteredTables"
            :key="table.table_name"
            class="table-item"
            :class="{ active: isSelected(table) }"
            @click="handleSelect(table)"
          >
            <div class="table-icon">
              <el-icon><Grid /></el-icon>
            </div>
            <div class="table-info">
              <div class="table-name">{{ table.table_name }}</div>
              <div class="table-comment" v-if="table.comment">
                {{ table.comment }}
              </div>
              <div class="table-stats">
                <el-tag size="small" type="info">
                  {{ table.columns_count }} 字段
                </el-tag>
                <el-tag size="small" type="warning" v-if="table.foreign_keys_count">
                  {{ table.foreign_keys_count }} 外键
                </el-tag>
              </div>
            </div>
          </div>

          <!-- 空状态 -->
          <el-empty
            v-if="!loading && filteredTables.length === 0"
            description="暂无表数据"
            :image-size="100"
          />
        </div>
      </el-scrollbar>
    </div>

    <!-- 统计信息 -->
    <div class="stats-footer">
      <el-text type="info">
        共 {{ tables.length }} 张表
        <template v-if="searchKeyword">
          ，筛选 {{ filteredTables.length }} 张
        </template>
      </el-text>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useTablesStore } from '@/stores/tables'
import { storeToRefs } from 'pinia'

const tablesStore = useTablesStore()
const { tables, filteredTables, loading, currentTable } = storeToRefs(tablesStore)

// 本地搜索关键词
const searchKeyword = ref('')

// 同步搜索关键词到 store
watch(searchKeyword, (val) => {
  tablesStore.searchTables(val)
})

// 处理搜索
const handleSearch = () => {
  tablesStore.searchTables(searchKeyword.value)
}

// 判断是否选中
const isSelected = (table) => {
  if (!currentTable.value) return false
  const currentName = currentTable.value.table_name
  const tableName = table.table_name
  return currentName === tableName
}

// 选中表
const handleSelect = (table) => {
  tablesStore.selectTable(table)
}
</script>

<style scoped>
.table-list {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #fff;
  border-right: 1px solid #e4e7ed;
}

.search-box {
  padding: 16px;
  border-bottom: 1px solid #e4e7ed;
}

.list-container {
  flex: 1;
  overflow: hidden;
}

.table-items {
  padding: 8px;
}

.table-item {
  display: flex;
  align-items: flex-start;
  padding: 12px;
  margin-bottom: 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s;
  border: 1px solid transparent;
}

.table-item:hover {
  background-color: #f5f7fa;
  border-color: #e4e7ed;
}

.table-item.active {
  background-color: #ecf5ff;
  border-color: #409eff;
}

.table-icon {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 8px;
  color: #fff;
  margin-right: 12px;
}

.table-item.active .table-icon {
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
}

.table-info {
  flex: 1;
  min-width: 0;
}

.table-name {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.table-comment {
  font-size: 12px;
  color: #909399;
  margin-bottom: 6px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.table-stats {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.stats-footer {
  padding: 12px 16px;
  border-top: 1px solid #e4e7ed;
  background: #fafafa;
}
</style>
