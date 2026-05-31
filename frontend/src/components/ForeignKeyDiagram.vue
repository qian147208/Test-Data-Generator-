<template>
  <div class="foreign-key-diagram">
    <div class="diagram-container" ref="diagramRef">
      <!-- 当前表 -->
      <div class="table-node current-table" :style="currentTableStyle">
        <div class="node-header">
          <el-icon><Grid /></el-icon>
          <span>{{ tableName }}</span>
        </div>
        <div class="node-body">
          <div class="node-label">当前表</div>
        </div>
      </div>

      <!-- 关联表 -->
      <div
        v-for="(fk, index) in foreignKeys"
        :key="index"
        class="table-node related-table"
        :style="getRelatedTableStyle(index)"
      >
        <div class="node-header">
          <el-icon><Grid /></el-icon>
          <span>{{ fk.referenced_table || fk.ref_table_name }}</span>
        </div>
        <div class="node-body">
          <div class="field-item">
            <el-icon class="key-icon"><Key /></el-icon>
            <span>{{ fk.referenced_column || fk.ref_column_name }}</span>
          </div>
        </div>

        <!-- 连接线 -->
        <svg class="connection-line" :style="getLineStyle(index)">
          <defs>
            <marker
              id="arrowhead"
              markerWidth="10"
              markerHeight="7"
              refX="9"
              refY="3.5"
              orient="auto"
            >
              <polygon points="0 0, 10 3.5, 0 7" fill="#409eff" />
            </marker>
          </defs>
          <line
            x1="0"
            y1="50%"
            x2="100%"
            y2="50%"
            stroke="#409eff"
            stroke-width="2"
            marker-end="url(#arrowhead)"
            stroke-dasharray="5,5"
          />
        </svg>

        <!-- 关系标签 -->
        <div class="relation-label" :style="getLabelStyle(index)">
          <el-tag size="small" type="warning">
            {{ fk.column || fk.column_name }} -> {{ fk.referenced_column || fk.ref_column_name }}
          </el-tag>
        </div>
      </div>
    </div>

    <!-- 图例 -->
    <div class="legend">
      <div class="legend-item">
        <div class="legend-color current"></div>
        <span>当前表</span>
      </div>
      <div class="legend-item">
        <div class="legend-color related"></div>
        <span>关联表</span>
      </div>
      <div class="legend-item">
        <svg width="40" height="10">
          <line x1="0" y1="5" x2="40" y2="5" stroke="#409eff" stroke-width="2" stroke-dasharray="5,5" />
        </svg>
        <span>外键关系</span>
      </div>
    </div>

    <!-- 空状态 -->
    <el-empty v-if="!foreignKeys || foreignKeys.length === 0" description="暂无外键关系" />
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  tableName: {
    type: String,
    required: true
  },
  foreignKeys: {
    type: Array,
    default: () => []
  }
})

const diagramRef = ref(null)

// 当前表位置
const currentTableStyle = computed(() => ({
  left: '20px',
  top: '50%',
  transform: 'translateY(-50%)'
}))

// 获取关联表位置
const getRelatedTableStyle = (index) => {
  const total = props.foreignKeys.length
  const spacing = Math.min(120, 400 / total)
  const startY = 50 - (total - 1) * spacing / 2

  return {
    right: '20px',
    top: `${startY + index * spacing}%`,
    transform: 'translateY(-50%)'
  }
}

// 获取连接线样式
const getLineStyle = (index) => {
  const total = props.foreignKeys.length
  const spacing = Math.min(120, 400 / total)
  const startY = 50 - (total - 1) * spacing / 2

  return {
    position: 'absolute',
    left: '180px',
    top: `${startY + index * spacing}%`,
    width: 'calc(100% - 360px)',
    height: '2px',
    transform: 'translateY(-50%)'
  }
}

// 获取标签位置
const getLabelStyle = (index) => {
  const total = props.foreignKeys.length
  const spacing = Math.min(120, 400 / total)
  const startY = 50 - (total - 1) * spacing / 2

  return {
    left: '50%',
    top: `${startY + index * spacing}%`,
    transform: 'translate(-50%, -150%)'
  }
}
</script>

<style scoped>
.foreign-key-diagram {
  position: relative;
  width: 100%;
  min-height: 300px;
  background: #fafafa;
  border-radius: 8px;
  overflow: hidden;
}

.diagram-container {
  position: relative;
  width: 100%;
  height: 300px;
  padding: 20px;
}

.table-node {
  position: absolute;
  min-width: 150px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  transition: all 0.3s;
}

.table-node:hover {
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  transform: translateY(-50%) scale(1.02);
}

.current-table {
  border: 2px solid #667eea;
}

.current-table .node-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.related-table {
  border: 2px solid #67c23a;
}

.related-table .node-header {
  background: linear-gradient(135deg, #67c23a 0%, #85ce61 100%);
}

.node-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  color: #fff;
  font-weight: 500;
  font-size: 14px;
}

.node-body {
  padding: 10px 12px;
}

.node-label {
  font-size: 12px;
  color: #909399;
}

.field-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #606266;
}

.key-icon {
  color: #e6a23c;
  font-size: 12px;
}

.connection-line {
  pointer-events: none;
  z-index: 1;
}

.relation-label {
  position: absolute;
  z-index: 2;
  white-space: nowrap;
}

.legend {
  position: absolute;
  bottom: 10px;
  left: 10px;
  display: flex;
  gap: 20px;
  padding: 10px 15px;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 6px;
  font-size: 12px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.legend-color {
  width: 16px;
  height: 16px;
  border-radius: 4px;
}

.legend-color.current {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.legend-color.related {
  background: linear-gradient(135deg, #67c23a 0%, #85ce61 100%);
}

/* 响应式 */
@media (max-width: 768px) {
  .diagram-container {
    height: auto;
    min-height: 400px;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 40px 20px;
  }

  .table-node {
    position: relative !important;
    left: auto !important;
    right: auto !important;
    top: auto !important;
    transform: none !important;
    margin-bottom: 20px;
  }

  .table-node:hover {
    transform: scale(1.02);
  }

  .connection-line {
    display: none;
  }

  .relation-label {
    position: relative;
    left: auto !important;
    top: auto !important;
    transform: none !important;
    margin-bottom: 10px;
  }
}
</style>
