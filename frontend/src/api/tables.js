// 表结构相关 API
import { ElMessage } from 'element-plus'
import axios from 'axios'

// 创建 axios 实例
const apiClient = axios.create({
  baseURL: '/api',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    const message = error.response?.data?.detail || error.response?.data?.message || error.message || 'Request failed'
    return Promise.reject(new Error(message))
  }
)

/**
 * 获取表列表
 * @param {Object} options - 选项
 * @param {number} options.batchSize - 每批获取的表数量
 * @param {Function} options.onProgress - 进度回调函数
 */
export async function getTablesApi(options = {}) {
  const { batchSize = 10, onProgress } = options
  
  try {
    // 首先获取所有表基本信息
    const allTables = await apiClient.get('/tables')
    
    if (!allTables || allTables.length === 0) {
      return []
    }
    
    // 调用进度回调 - 初始进度
    if (onProgress) {
      onProgress(10)
    }
    
    // 分批获取表详情
    const batches = []
    for (let i = 0; i < allTables.length; i += batchSize) {
      batches.push(allTables.slice(i, i + batchSize))
    }
    
    const results = []
    for (let i = 0; i < batches.length; i++) {
      const batch = batches[i]
      // 并行获取当前批次的表详情
      const batchPromises = batch.map(table => 
        getTableDetailsApi(table.table_name).catch(err => {
          console.warn(`获取表 ${table.table_name} 详情失败:`, err)
          return table // 失败时返回基本信息
        })
      )
      
      const batchResults = await Promise.all(batchPromises)
      results.push(...batchResults)
      
      // 调用进度回调
      if (onProgress) {
        const progress = Math.round(10 + ((i + 1) / batches.length) * 90)
        onProgress(progress)
      }
      
      // 每批之间短暂暂停，避免请求过多
      if (i < batches.length - 1) {
        await new Promise(resolve => setTimeout(resolve, 100))
      }
    }
    
    // 完成进度
    if (onProgress) {
      onProgress(100)
    }
    
    return results
  } catch (error) {
    ElMessage.error('获取表列表失败: ' + error.message)
    throw error
  }
}

/**
 * 获取表详情
 * @param {string} tableName - 表名
 */
export async function getTableDetailsApi(tableName) {
  try {
    const result = await apiClient.get(`/tables/${encodeURIComponent(tableName)}`)
    return result
  } catch (error) {
    ElMessage.error('获取表详情失败: ' + error.message)
    throw error
  }
}

/**
 * 获取表依赖关系
 * @param {string} tableName - 表名
 */
export async function getTableDependenciesApi(tableName) {
  try {
    const result = await apiClient.get(`/tables/${encodeURIComponent(tableName)}/dependencies`)
    return result
  } catch (error) {
    ElMessage.error('获取表依赖关系失败: ' + error.message)
    throw error
  }
}
