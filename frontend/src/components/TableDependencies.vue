<template>
  <div class="table-dependencies">
    <el-card class="dependencies-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <el-icon class="header-icon"><Link /></el-icon>
          <span>表依赖关系</span>
        </div>
      </template>

      <div class="dependencies-content" v-loading="loading">
        <div v-if="dependencies" class="dependencies-container">
          <!-- 依赖的表 -->
          <div class="dependency-section" v-if="dependencies.depends_on && dependencies.depends_on.length > 0">
            <h3 class="section-title">
              <el-icon class="section-icon"><ArrowDown /></el-icon>
              依赖的表 ({{ dependencies.depends_on.length }})
            </h3>
            <div class="dependency-list">
              <el-tag
                v-for="table in dependencies.depends_on"
                :key="table"
                size="medium"
                class="dependency-tag"
                @click="handleTableClick(table)"
              >
                {{ table }}
              </el-tag>
            </div>
          </div>

          <!-- 被依赖的表 -->
          <div class="dependency-section" v-if="dependencies.depended_by && dependencies.depended_by.length > 0">
            <h3 class="section-title">
              <el-icon class="section-icon"><ArrowUp /></el-icon>
              被依赖的表 ({{ dependencies.depended_by.length }})
            </h3>
            <div class="dependency-list">
              <el-tag
                v-for="table in dependencies.depended_by"
                :key="table"
                size="medium"
                class="dependency-tag"
                @click="handleTableClick(table)"
              >
                {{ table }}
              </el-tag>
            </div>
          </div>

          <!-- 无依赖 -->
          <div v-if="(!dependencies.depends_on || dependencies.depends_on.length === 0) && (!dependencies.depended_by || dependencies.depended_by.length === 0)" class="no-dependencies">
            <el-empty description="无依赖关系" :image-size="60" />
          </div>
        </div>

        <div v-else class="no-data">
          <el-empty description="请先选择表" :image-size="60" />
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useTablesStore } from '@/stores/tables'
import { storeToRefs } from 'pinia'

const props = defineProps({
  tableName: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['table-click'])

const tablesStore = useTablesStore()
const { tableDependencies, loading } = storeToRefs(tablesStore)

const dependencies = computed(() => {
  if (!props.tableName) return null
  return tableDependencies.value[props.tableName] || null
})

watch(() => props.tableName, async (newVal) => {
  if (newVal) {
    await tablesStore.fetchTableDependencies(newVal)
  }
})

async function handleTableClick(tableName) {
  // 查找表对象
  const table = tablesStore.tables.find(t => t.table_name === tableName)
  if (table) {
    await tablesStore.selectTable(table)
    emit('table-click', table)
  }
}

onMounted(async () => {
  if (props.tableName) {
    await tablesStore.fetchTableDependencies(props.tableName)
  }
})
</script>

<style scoped>
.table-dependencies {
  padding: 24px;
  max-width: 100%;
}

.dependencies-card {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(96, 165, 250, 0.1);
  border-radius: 16px;
  backdrop-filter: blur(10px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  overflow: hidden;
  transition: all 0.3s ease;
}

.dependencies-card:hover {
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4) !important;
  transform: translateY(-4px);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 16px;
  font-weight: 600;
  padding: 20px 24px;
  background: rgba(15, 23, 42, 0.8);
  border-bottom: 1px solid rgba(96, 165, 250, 0.1);
}

.header-icon {
  color: #3b82f6;
  font-size: 20px;
}

.dependencies-content {
  padding: 24px;
  background: rgba(30, 41, 59, 0.4);
}

.dependencies-container {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.dependency-section {
  border: 1px solid rgba(96, 165, 250, 0.1);
  border-radius: 12px;
  padding: 16px;
  background: rgba(15, 23, 42, 0.4);
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #f8fafc;
  margin: 0 0 16px 0;
}

.section-icon {
  color: #60a5fa;
  font-size: 16px;
}

.dependency-list {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.dependency-tag {
  background: rgba(96, 165, 250, 0.1);
  border: 1px solid rgba(96, 165, 250, 0.3);
  color: #60a5fa;
  cursor: pointer;
  transition: all 0.3s ease;
  padding: 6px 16px;
  border-radius: 20px;
}

.dependency-tag:hover {
  background: rgba(96, 165, 250, 0.2);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.no-dependencies,
.no-data {
  text-align: center;
  padding: 40px 0;
}

:deep(.el-empty__description) {
  color: #94a3b8;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .table-dependencies {
    padding: 16px;
  }

  .dependencies-content {
    padding: 20px;
  }

  .dependency-list {
    justify-content: center;
  }
}
</style>