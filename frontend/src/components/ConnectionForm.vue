<template>
  <el-card class="connection-form-card">
    <template #header>
      <div class="card-header">
        <el-icon class="header-icon"><Connection /></el-icon>
        <span>数据库连接配置</span>
      </div>
    </template>

    <el-form
      ref="formRef"
      :model="formData"
      :rules="rules"
      label-width="100px"
      label-position="left"
      :disabled="connecting"
    >
      <!-- 数据库类型选择 -->
      <el-form-item label="数据库类型" prop="type">
        <el-select
          v-model="formData.type"
          placeholder="请选择数据库类型"
          style="width: 100%"
          @change="handleTypeChange"
        >
          <el-option label="MySQL" value="mysql">
            <el-icon><Coin /></el-icon>
            <span style="margin-left: 8px">MySQL</span>
          </el-option>
          <el-option label="PostgreSQL" value="postgresql">
            <el-icon><Coin /></el-icon>
            <span style="margin-left: 8px">PostgreSQL</span>
          </el-option>
          <el-option label="SQLite" value="sqlite">
            <el-icon><Document /></el-icon>
            <span style="margin-left: 8px">SQLite</span>
          </el-option>
        </el-select>
      </el-form-item>

      <!-- SQLite 文件路径 -->
      <el-form-item
        v-if="formData.type === 'sqlite'"
        label="数据库文件"
        prop="database"
      >
        <el-input
          v-model="formData.database"
          placeholder="请输入数据库文件路径"
          clearable
        >
          <template #prefix>
            <el-icon><Document /></el-icon>
          </template>
        </el-input>
      </el-form-item>

      <!-- MySQL/PostgreSQL 配置 -->
      <template v-if="formData.type && formData.type !== 'sqlite'">
        <!-- 主机地址 -->
        <el-form-item label="主机地址" prop="host">
          <el-input
            v-model="formData.host"
            placeholder="请输入主机地址，如 localhost"
            clearable
          >
            <template #prefix>
              <el-icon><Monitor /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <!-- 端口号 -->
        <el-form-item label="端口号" prop="port">
          <el-input-number
            v-model="formData.port"
            :min="1"
            :max="65535"
            placeholder="端口号"
            style="width: 100%"
          />
        </el-form-item>

        <!-- 数据库名 -->
        <el-form-item label="数据库名" prop="database">
          <el-input
            v-model="formData.database"
            placeholder="请输入数据库名"
            clearable
          >
            <template #prefix>
              <el-icon><Database /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <!-- 用户名 -->
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="formData.username"
            placeholder="请输入用户名"
            clearable
          >
            <template #prefix>
              <el-icon><User /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <!-- 密码 -->
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="formData.password"
            type="password"
            placeholder="请输入密码"
            show-password
            clearable
          >
            <template #prefix>
              <el-icon><Lock /></el-icon>
            </template>
          </el-input>
        </el-form-item>
      </template>

      <!-- 按钮组 -->
      <el-form-item>
        <el-button
          type="primary"
          :loading="connecting"
          :disabled="!formData.type"
          @click="handleConnect"
        >
          <el-icon v-if="!connecting"><Link /></el-icon>
          {{ connecting ? '连接中...' : '连接' }}
        </el-button>
        <el-button
          :disabled="!formData.type || connecting"
          @click="handleTestConnection"
        >
          <el-icon><CircleCheck /></el-icon>
          测试连接
        </el-button>
        <el-button @click="handleReset">
          <el-icon><RefreshRight /></el-icon>
          重置
        </el-button>
      </el-form-item>
    </el-form>
  </el-card>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useConnectionStore } from '@/stores/connection'

const connectionStore = useConnectionStore()
const formRef = ref(null)

// 表单数据
const formData = reactive({
  type: '',
  host: 'localhost',
  port: 3306,
  database: '',
  username: '',
  password: ''
})

// 连接中状态
const connecting = computed(() => connectionStore.connecting)

// 默认端口映射
const defaultPorts = {
  mysql: 3306,
  postgresql: 5432,
  sqlite: null
}

// 验证规则
const rules = {
  type: [
    { required: true, message: '请选择数据库类型', trigger: 'change' }
  ],
  host: [
    { required: true, message: '请输入主机地址', trigger: 'blur' }
  ],
  port: [
    { required: true, message: '请输入端口号', trigger: 'blur' },
    { type: 'number', min: 1, max: 65535, message: '端口号范围为 1-65535', trigger: 'blur' }
  ],
  database: [
    { required: true, message: '请输入数据库名或文件路径', trigger: 'blur' }
  ],
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ]
}

// 数据库类型改变
const handleTypeChange = (type) => {
  // 设置默认端口
  if (defaultPorts[type]) {
    formData.port = defaultPorts[type]
  }
  // 清空其他字段
  if (type === 'sqlite') {
    formData.host = ''
    formData.port = null
    formData.username = ''
    formData.password = ''
  } else {
    formData.host = 'localhost'
    formData.database = ''
    formData.username = ''
    formData.password = ''
  }
}

// 连接
const handleConnect = async () => {
  if (!formRef.value) return

  try {
    await formRef.value.validate()

    const result = await connectionStore.connect(formData)

    if (result.success) {
      ElMessage.success('数据库连接成功')
    } else {
      ElMessage.error(result.message || '连接失败')
    }
  } catch (error) {
    ElMessage.warning('请完善表单信息')
  }
}

// 测试连接
const handleTestConnection = async () => {
  if (!formRef.value) return

  try {
    await formRef.value.validate()

    const result = await connectionStore.testConnection(formData)

    if (result.success) {
      ElMessage.success('连接测试成功')
    } else {
      ElMessage.error(result.message || '连接测试失败')
    }
  } catch (error) {
    ElMessage.warning('请完善表单信息')
  }
}

// 重置表单
const handleReset = () => {
  if (formRef.value) {
    formRef.value.resetFields()
  }
  formData.type = ''
  formData.host = 'localhost'
  formData.port = 3306
  formData.database = ''
  formData.username = ''
  formData.password = ''
}
</script>

<style scoped>
.connection-form-card {
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

.el-form-item:last-child {
  margin-bottom: 0;
}

.el-button + .el-button {
  margin-left: 12px;
}

/* 输入框图标样式 */
:deep(.el-input__prefix) {
  color: #909399;
}

/* Select 选项样式 */
:deep(.el-select-dropdown__item) {
  display: flex;
  align-items: center;
}
</style>
