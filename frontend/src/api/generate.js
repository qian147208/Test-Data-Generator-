// 数据生成相关 API
import { ElMessage, ElLoading } from 'element-plus'
import axios from 'axios'

// 创建 axios 实例
const apiClient = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 加载实例
let loadingInstance = null

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 显示加载动画
    if (config.showLoading !== false) {
      loadingInstance = ElLoading.service({
        lock: true,
        text: '处理中...',
        background: 'rgba(0, 0, 0, 0.7)'
      })
    }
    return config
  },
  (error) => {
    // 关闭加载动画
    if (loadingInstance) {
      loadingInstance.close()
      loadingInstance = null
    }
    return Promise.reject(error)
  }
)

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    // 关闭加载动画
    if (loadingInstance) {
      loadingInstance.close()
      loadingInstance = null
    }
    return response.data
  },
  (error) => {
    if (loadingInstance) {
      loadingInstance.close()
      loadingInstance = null
    }
    
    const serverDetail = error.response?.data?.detail || error.response?.data?.message
    let message = serverDetail || 'Request failed'
    if (error.response) {
      const status = error.response.status
      switch (status) {
        case 400:
          message = serverDetail || 'Bad request'
          break
        case 404:
          message = serverDetail || 'Resource not found'
          break
        case 500:
          message = serverDetail || 'Internal server error'
          break
        case 503:
          message = serverDetail || 'Service unavailable, please connect to database first'
          break
      }
    } else if (error.message) {
      if (error.message.includes('timeout')) {
        message = 'Request timeout, please check network'
      } else if (error.message.includes('Network Error')) {
        message = 'Network error, please check connection'
      } else {
        message = error.message
      }
    }
    
    ElMessage.error(message)
    return Promise.reject(new Error(message))
  }
)

/**
 * 生成数据
 * @param {Object} params - 生成参数
 * @param {boolean} showLoading - 是否显示加载动画
 */
export async function generateDataApi(params, showLoading = true) {
  try {
    const result = await apiClient.post('/generate', params, { showLoading })
    ElMessage.success(`成功生成 ${result.total_rows} 条数据`)
    return result
  } catch (error) {
    throw error
  }
}

/**
 * 生成预览数据
 * @param {string} tableName - 表名
 * @param {number} count - 预览行数
 * @param {string} strategy - 生成策略
 * @param {boolean} showLoading - 是否显示加载动画
 */
export async function generatePreviewApi(tableName, count = 5, strategy = 'normal', showLoading = true) {
  try {
    const result = await apiClient.post('/generate/preview', {
      table_name: tableName,
      count,
      strategy,
    }, { showLoading })
    return result
  } catch (error) {
    throw error
  }
}

/**
 * 批量生成数据
 * @param {Object} params - 批量生成参数
 * @param {boolean} showLoading - 是否显示加载动画
 */
export async function generateBatchApi(params, showLoading = true) {
  try {
    const result = await apiClient.post('/generate/batch', params, { showLoading })
    if (result.processed_tables > 0) {
      ElMessage.success(`成功生成 ${result.processed_tables} 张表的数据`)
    }
    return result
  } catch (error) {
    throw error
  }
}

/**
 * 导出 SQL
 * @param {Object} params - 导出参数
 * @param {boolean} showLoading - 是否显示加载动画
 */
export async function exportSqlApi(params, showLoading = true) {
  try {
    const result = await apiClient.post('/export/sql', params, { showLoading })
    ElMessage.success('SQL 导出成功')
    return result
  } catch (error) {
    throw error
  }
}

/**
 * 批量导出 SQL
 * @param {Object} params - 批量导出参数
 * @param {boolean} showLoading - 是否显示加载动画
 */
export async function exportBatchSqlApi(params, showLoading = true) {
  try {
    const result = await apiClient.post('/export/batch', params, { showLoading })
    ElMessage.success('批量 SQL 导出成功')
    return result
  } catch (error) {
    throw error
  }
}

/**
 * 下载 SQL 文件
 * @param {string} tableName - 表名
 * @param {Array} data - 数据
 */
export function downloadSqlFile(tableName, data) {
  try {
    if (!data || data.length === 0) {
      ElMessage.warning('没有数据可下载')
      return
    }
    
    const sqlStatements = data.map(row => {
      const columns = Object.keys(row)
      const values = Object.values(row).map(v => {
        if (v === null || v === undefined) return 'NULL'
        if (typeof v === 'string') return `'${v.replace(/'/g, "''")}'`
        if (v instanceof Date) return `'${v.toISOString()}'`
        return v
      })
      
      return `INSERT INTO \`${tableName}\` (\`${columns.join('\`, \`')}\`) VALUES (${values.join(', ')});`
    })

    const sqlContent = sqlStatements.join('\n')
    const blob = new Blob([sqlContent], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${tableName}_data_${new Date().toISOString().slice(0, 10)}.sql`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
    
    ElMessage.success('SQL 文件下载成功')
  } catch (error) {
    ElMessage.error('下载 SQL 文件失败: ' + error.message)
  }
}

/**
 * 获取支持的生成策略
 */
export async function getStrategiesApi() {
  try {
    const result = await apiClient.get('/generate/strategies', { showLoading: false })
    return result.data
  } catch (error) {
    console.error('获取策略失败:', error)
    return []
  }
}

/**
 * 获取支持的数据类型
 */
export async function getSupportedTypesApi() {
  try {
    const result = await apiClient.get('/generate/types', { showLoading: false })
    return result.data
  } catch (error) {
    console.error('获取支持的数据类型失败:', error)
    return []
  }
}