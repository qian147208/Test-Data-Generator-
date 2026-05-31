<template>
  <div class="generate-config">
    <el-card class="config-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <el-icon class="header-icon"><Setting /></el-icon>
          <span>数据生成配置</span>
        </div>
      </template>

      <el-form :model="localConfig" label-width="100px" class="config-form">
        <el-form-item label="生成策略" required>
          <el-select v-model="localConfig.strategy" placeholder="选择生成策略" style="width: 100%" class="strategy-select">
            <el-option label="正常数据" value="normal">
              <div class="strategy-option">
                <span class="strategy-label">正常数据</span>
                <span class="strategy-desc">生成符合业务规则的正常数据</span>
              </div>
            </el-option>
            <el-option label="边界值" value="boundary">
              <div class="strategy-option">
                <span class="strategy-label">边界值</span>
                <span class="strategy-desc">生成边界值和极限值数据</span>
              </div>
            </el-option>
            <el-option label="异常数据" value="abnormal">
              <div class="strategy-option">
                <span class="strategy-label">异常数据</span>
                <span class="strategy-desc">生成异常和错误场景数据</span>
              </div>
            </el-option>
            <el-option label="混合模式" value="mixed">
              <div class="strategy-option">
                <span class="strategy-label">混合模式</span>
                <span class="strategy-desc">混合生成各类数据</span>
              </div>
            </el-option>
          </el-select>
        </el-form-item>

        <el-form-item label="生成数量" required>
          <el-input-number
            v-model="localConfig.count"
            :min="1"
            :max="10000"
            :step="10"
            style="width: 100%"
            class="count-input"
          />
        </el-form-item>

        <el-form-item label="语言区域">
          <el-select v-model="localConfig.locale" placeholder="选择语言区域" style="width: 100%">
            <el-option label="中文 (中国)" value="zh_CN" />
            <el-option label="英文 (美国)" value="en_US" />
            <el-option label="日文 (日本)" value="ja_JP" />
          </el-select>
        </el-form-item>

        <el-form-item label="批量大小">
          <el-input-number
            v-model="localConfig.batchSize"
            :min="1"
            :max="1000"
            :step="10"
            style="width: 100%"
          />
          <div class="form-tip">每条 INSERT 语句包含的行数</div>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="column-rules-card" v-if="tableColumns.length > 0" shadow="hover">
      <template #header>
        <div class="card-header">
          <el-icon class="header-icon"><Edit /></el-icon>
          <span>字段规则配置</span>
          <el-tag type="info" size="small" style="margin-left: 8px">
            可选，覆盖默认规则
          </el-tag>
        </div>
      </template>

      <div class="table-container">
        <el-table :data="tableColumns" style="width: 100%" size="small" stripe border>
          <el-table-column prop="name" label="字段名" width="150">
            <template #default="{ row }">
              <div class="column-name" :title="row.name">{{ row.name }}</div>
            </template>
          </el-table-column>
          <el-table-column prop="data_type" label="类型" width="120" />
          <el-table-column prop="comment" label="注释" width="150">
            <template #default="{ row }">
              <span class="column-comment">{{ row.comment || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="可空" width="60">
            <template #default="{ row }">
              <el-tag :type="row.is_nullable ? 'success' : 'danger'" size="small" effect="plain">
                {{ row.is_nullable ? '是' : '否' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="自定义规则" min-width="300">
            <template #default="{ row }">
              <div class="column-rule-config">
                <el-select
                  v-model="columnRulesMap[row.name]"
                  placeholder="选择生成器"
                  clearable
                  size="small"
                  style="width: 140px"
                  @change="handleGeneratorChange(row.name, $event)"
                  class="generator-select"
                >
                  <el-option-group label="基础类型">
                    <el-option label="自动推断" value="" />
                    <el-option label="固定值" value="fixed" />
                    <el-option label="随机选择" value="choice" />
                    <el-option label="递增序列" value="sequence" />
                  </el-option-group>
                  <el-option-group label="文本类型">
                    <el-option label="姓名" value="name" />
                    <el-option label="邮箱" value="email" />
                    <el-option label="电话" value="phone" />
                    <el-option label="地址" value="address" />
                    <el-option label="公司名" value="company" />
                    <el-option label="句子" value="sentence" />
                    <el-option label="段落" value="paragraph" />
                    <el-option label="汉字" value="chinese" />
                    <el-option label="字母" value="letters" />
                    <el-option label="字符" value="characters" />
                  </el-option-group>
                  <el-option-group label="数字类型">
                    <el-option label="整数" value="integer" />
                    <el-option label="小数" value="float" />
                    <el-option label="金额" value="money" />
                    <el-option label="随机数字" value="random_number" />
                  </el-option-group>
                  <el-option-group label="日期时间">
                    <el-option label="日期" value="date" />
                    <el-option label="时间" value="time" />
                    <el-option label="日期时间" value="datetime" />
                  </el-option-group>
                </el-select>

                <el-input
                  v-if="columnRulesMap[row.name] === 'fixed'"
                  v-model="columnParamsMap[row.name]"
                  placeholder="固定值"
                  size="small"
                  style="width: 120px; margin-left: 8px"
                  @change="handleParamsChange(row.name, $event)"
                  class="param-input"
                />

                <el-input
                  v-if="columnRulesMap[row.name] === 'choice'"
                  v-model="columnParamsMap[row.name]"
                  placeholder="选项(逗号分隔)"
                  size="small"
                  style="width: 150px; margin-left: 8px"
                  @change="handleParamsChange(row.name, $event)"
                  class="param-input"
                />

                <el-input-number
                  v-if="columnRulesMap[row.name] === 'sequence'"
                  v-model="columnParamsMap[row.name]"
                  placeholder="起始值"
                  size="small"
                  style="width: 100px; margin-left: 8px"
                  @change="handleParamsChange(row.name, $event)"
                  class="param-input"
                />
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <div class="action-buttons">
      <el-button
        type="primary"
        :disabled="!tableName"
        @click="handleGenerate"
        class="action-button primary-button"
      >
        <el-icon><MagicStick /></el-icon>
        生成数据
      </el-button>

      <el-button
        :disabled="!tableName"
        @click="handlePreview"
        class="action-button"
      >
        <el-icon><View /></el-icon>
        预览数据
      </el-button>

      <el-button @click="handleReset" class="action-button">
        <el-icon><RefreshRight /></el-icon>
        重置配置
      </el-button>
    </div>

    <el-dialog
      v-model="previewVisible"
      title="数据预览"
      width="80%"
      destroy-on-close
      :close-on-click-modal="false"
      custom-class="preview-dialog"
    >
      <div class="preview-content">
        <el-table :data="previewData" style="width: 100%" max-height="400" stripe border>
          <el-table-column
            v-for="col in previewColumns"
            :key="col"
            :prop="col"
            :label="col"
            min-width="120"
          >
            <template #default="{ row }">
              <div class="cell-content" :title="row[col]">
                {{ row[col] }}
              </div>
            </template>
          </el-table-column>
        </el-table>
        <div v-if="previewData.length === 0" class="no-data">
          <el-empty description="暂无数据" />
        </div>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="previewVisible = false">关闭</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useGenerateStore } from '@/stores/generate'
import { useTablesStore } from '@/stores/tables'

const props = defineProps({
  tableName: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['generated', 'error'])

const generateStore = useGenerateStore()
const tablesStore = useTablesStore()

const localConfig = reactive({
  strategy: 'normal',
  count: 10,
  locale: 'zh_CN',
  batchSize: 100,
})

const columnRulesMap = reactive({})
const columnParamsMap = reactive({})
const previewVisible = ref(false)
const previewData = ref([])



const tableColumns = computed(() => {
  if (!props.tableName) return []
  const details = tablesStore.tableDetails[props.tableName]
  return details?.columns || []
})

const previewColumns = computed(() => {
  if (previewData.value.length === 0) return []
  return Object.keys(previewData.value[0])
})

watch(() => props.tableName, (newVal) => {
  if (newVal) {
    generateStore.setTableName(newVal)
    Object.keys(columnRulesMap).forEach(key => delete columnRulesMap[key])
    Object.keys(columnParamsMap).forEach(key => delete columnParamsMap[key])
  }
})

watch(localConfig, (newVal) => {
  generateStore.setStrategy(newVal.strategy)
  generateStore.setCount(newVal.count)
}, { deep: true })

function handleGeneratorChange(columnName, generator) {
  if (generator) {
    columnParamsMap[columnName] = ''
  } else {
    delete columnParamsMap[columnName]
    generateStore.clearColumnRule(columnName)
  }
}

function handleParamsChange(columnName, params) {
  const generator = columnRulesMap[columnName]
  if (!generator) return

  let rule = { column_name: columnName, strategy: generator }

  if (generator === 'fixed') {
    rule.custom_values = [params]
  } else if (generator === 'choice') {
    rule.custom_values = params.split(',').map(s => s.trim()).filter(s => s)
  } else if (generator === 'sequence') {
    rule.generator_params = { start: params || 1 }
  }

  generateStore.updateColumnRule(columnName, rule)
}

async function handleGenerate() {
  try {
    const data = await generateStore.generate()
    emit('generated', data)
  } catch (error) {
    emit('error', error)
  }
}

async function handlePreview() {
  try {
    const data = await generateStore.generatePreview(
      props.tableName,
      5,
      localConfig.strategy
    )
    previewData.value = data
    previewVisible.value = true
  } catch (error) {
    // 错误处理已在API层完成
  }
}

function handleReset() {
  localConfig.strategy = 'normal'
  localConfig.count = 10
  localConfig.locale = 'zh_CN'
  localConfig.batchSize = 100
  
  Object.keys(columnRulesMap).forEach(key => delete columnRulesMap[key])
  Object.keys(columnParamsMap).forEach(key => delete columnParamsMap[key])
  
  generateStore.setColumnRules([])
  ElMessage.success('配置已重置')
}
</script>

<style scoped>
.generate-config {
  padding: 24px;
  max-width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.config-card,
.column-rules-card {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(96, 165, 250, 0.1);
  border-radius: 16px;
  backdrop-filter: blur(10px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  overflow: hidden;
  transition: all 0.3s ease;
}

.config-card:hover,
.column-rules-card:hover {
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

.config-form {
  padding: 24px;
  background: rgba(30, 41, 59, 0.4);
}

:deep(.el-form-item__label) {
  color: #f8fafc;
  font-weight: 500;
}

:deep(.el-input__inner),
:deep(.el-select__input),
:deep(.el-input-number__input) {
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid rgba(96, 165, 250, 0.1);
  color: #f8fafc;
  border-radius: 8px;
  transition: all 0.3s ease;
}

:deep(.el-input__inner:hover),
:deep(.el-select__input:hover),
:deep(.el-input-number__input:hover) {
  border-color: rgba(59, 130, 246, 0.5);
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
}

:deep(.el-input__inner:focus),
:deep(.el-select__input:focus),
:deep(.el-input-number__input:focus) {
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
}

:deep(.el-select-dropdown) {
  background: rgba(15, 23, 42, 0.95);
  border: 1px solid rgba(96, 165, 250, 0.1);
  border-radius: 8px;
  backdrop-filter: blur(10px);
}

:deep(.el-select-dropdown__item) {
  color: #f8fafc;
  transition: all 0.3s ease;
}

:deep(.el-select-dropdown__item:hover) {
  background: rgba(59, 130, 246, 0.1);
}

:deep(.el-select-dropdown__item.selected) {
  background: rgba(59, 130, 246, 0.2);
  color: #3b82f6;
}

.form-tip {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 6px;
  line-height: 1.4;
}

.strategy-option {
  display: flex;
  flex-direction: column;
  padding: 8px 0;
  min-width: 220px;
}

.strategy-label {
  font-weight: 500;
  font-size: 14px;
  margin-bottom: 4px;
  color: #f8fafc;
}

.strategy-desc {
  font-size: 12px;
  color: #94a3b8;
  line-height: 1.4;
}

.table-container {
  overflow-x: auto;
  background: rgba(30, 41, 59, 0.4);
}

.column-rule-config {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.column-name {
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #f8fafc;
}

.column-comment {
  font-size: 12px;
  color: #94a3b8;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}

.action-buttons {
  display: flex;
  gap: 16px;
  justify-content: center;
  padding: 24px 0;
  flex-wrap: wrap;
  margin-top: auto;
}

.action-button {
  min-width: 140px;
  height: 44px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  transition: all 0.3s ease;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05);
  color: #f8fafc;
}

.action-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  border-color: rgba(96, 165, 250, 0.5);
}

.primary-button {
  background: linear-gradient(135deg, #60a5fa 0%, #3b82f6 100%);
  border: none;
  color: #0f172a;
  font-weight: 600;
}

.primary-button:hover {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: #0f172a;
  box-shadow: 0 4px 16px rgba(59, 130, 246, 0.4);
}

.preview-dialog {
  border-radius: 16px;
  overflow: hidden;
  background: rgba(15, 23, 42, 0.95);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

:deep(.el-dialog__header) {
  background: rgba(15, 23, 42, 0.8);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  padding: 20px 24px;
}

:deep(.el-dialog__title) {
  color: #f8fafc;
  font-weight: 600;
  font-size: 16px;
}

:deep(.el-dialog__close) {
  color: #94a3b8;
  transition: all 0.3s ease;
}

:deep(.el-dialog__close:hover) {
  color: #f8fafc;
}

.preview-content {
  padding: 24px;
  max-height: 500px;
  overflow-y: auto;
}

.cell-content {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
  color: #f8fafc;
}

.no-data {
  text-align: center;
  padding: 40px 0;
}

:deep(.el-empty__description) {
  color: #94a3b8;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  padding: 16px 24px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(15, 23, 42, 0.8);
}

:deep(.el-button) {
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05);
  color: #f8fafc;
  border-radius: 8px;
  transition: all 0.3s ease;
}

:deep(.el-button:hover) {
  border-color: rgba(96, 165, 250, 0.5);
  background: rgba(96, 165, 250, 0.1);
  color: #f8fafc;
}

:deep(.el-button--primary) {
  background: linear-gradient(135deg, #60a5fa 0%, #3b82f6 100%);
  border: none;
  color: #0f172a;
  font-weight: 600;
}

:deep(.el-button--primary:hover) {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: #0f172a;
}

/* 表格样式优化 */
:deep(.el-table) {
  border-radius: 8px;
  overflow: hidden;
  background: transparent;
}

:deep(.el-table th) {
  background: rgba(15, 23, 42, 0.8);
  font-weight: 600;
  text-align: left;
  color: #f8fafc;
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
}

:deep(.el-table td) {
  background: rgba(30, 41, 59, 0.6);
  color: #f1f5f9;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

:deep(.el-table tr:hover > td) {
  background: rgba(96, 165, 250, 0.15) !important;
}

:deep(.el-table--striped .el-table__row--striped td) {
  background: rgba(30, 41, 59, 0.8);
}

:deep(.cell) {
  color: #f1f5f9 !important;
  font-size: 14px;
  line-height: 1.5;
}

:deep(.column-name) {
  color: #f8fafc !important;
  font-weight: 500;
}

:deep(.column-comment) {
  color: #94a3b8 !important;
  font-size: 12px;
}

:deep(.el-tag) {
  border-radius: 4px;
  font-size: 12px;
  padding: 2px 8px;
}

:deep(.el-tag--success) {
  background: rgba(16, 185, 129, 0.2);
  border: 1px solid rgba(16, 185, 129, 0.3);
  color: #10b981;
}

:deep(.el-tag--danger) {
  background: rgba(239, 68, 68, 0.2);
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: #ef4444;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .generate-config {
    padding: 16px;
  }

  .config-form {
    padding: 20px;
  }

  .action-buttons {
    flex-direction: column;
    align-items: stretch;
  }

  .action-button {
    width: 100%;
  }

  .preview-content {
    padding: 20px;
  }
}

/* 动画效果 */
.strategy-select,
.generator-select,
.param-input,
.count-input {
  transition: all 0.3s ease;
}

/* 下拉菜单样式 */
:deep(.el-select-dropdown) {
  max-height: 400px !important;
  min-width: 200px !important;
}

:deep(.el-option-group) {
  margin: 8px 0;
}

:deep(.el-option) {
  padding: 8px 16px !important;
  line-height: 1.4;
}

:deep(.el-option:hover) {
  background: rgba(59, 130, 246, 0.1) !important;
}

:deep(.el-option__content) {
  white-space: normal !important;
  word-wrap: break-word;
  line-height: 1.4;
  min-height: 32px;
  display: flex;
  align-items: center;
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
  background: rgba(96, 165, 250, 0.5);
  border-radius: 4px;
  transition: all 0.3s ease;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(96, 165, 250, 0.7);
}
</style>
