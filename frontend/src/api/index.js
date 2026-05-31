import axios from 'axios'
import { ElMessage, ElLoading } from 'element-plus'

const apiClient = axios.create({
  baseURL: '/api',
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' }
})

let loadingInstance = null
let activeRequests = 0

const showLoading = () => {
  if (!loadingInstance) {
    loadingInstance = ElLoading.service({
      lock: true,
      text: '处理中...',
      background: 'rgba(0, 0, 0, 0.7)'
    })
  }
}

const hideLoading = () => {
  if (activeRequests <= 0 && loadingInstance) {
    loadingInstance.close()
    loadingInstance = null
  }
}

apiClient.interceptors.request.use((config) => {
  if (config.showLoading !== false && config.method !== 'get') {
    activeRequests++
    showLoading()
  }
  return config
}, (error) => {
  activeRequests = Math.max(0, activeRequests - 1)
  hideLoading()
  return Promise.reject(error)
})

apiClient.interceptors.response.use(
  (response) => {
    activeRequests = Math.max(0, activeRequests - 1)
    hideLoading()
    return response.data
  },
  (error) => {
    activeRequests = Math.max(0, activeRequests - 1)
    hideLoading()

    const serverDetail = error.response?.data?.detail || error.response?.data?.message
    let message = serverDetail || error.message || 'Request failed'

    if (error.response) {
      const statusMap = {
        400: '请求参数错误',
        404: '资源不存在',
        500: '服务器内部错误',
        503: '服务不可用，请先连接数据库'
      }
      message = serverDetail || statusMap[error.response.status] || message
    }

    ElMessage.error(message)
    return Promise.reject(new Error(message))
  }
)

export const request = (config) => apiClient(config)

export const get = (url, config = {}) => request({ method: 'get', url, ...config })
export const post = (url, data, config = {}) => request({ method: 'post', url, data, ...config })
export const put = (url, data, config = {}) => request({ method: 'put', url, data, ...config })
export const del = (url, config = {}) => request({ method: 'delete', url, ...config })

export const connection = {
  connect: (config) => post('/connect', {
    db_type: config.type,
    host: config.host,
    port: config.port,
    database: config.database,
    username: config.username,
    password: config.password,
    pool_size: config.pool_size || 5,
    max_overflow: config.max_overflow || 10
  }),

  disconnect: () => post('/disconnect'),
  test: (config) => post('/test', {
    db_type: config.type,
    host: config.host,
    port: config.port,
    database: config.database,
    username: config.username,
    password: config.password
  }),
  getStatus: () => get('/status')
}

export const tables = {
  getAll: (schema) => get('/tables', { params: { schema } }),
  getDetails: (tableName) => get(`/tables/${encodeURIComponent(tableName)}`),
  getDependencies: (tableName) => get(`/tables/${encodeURIComponent(tableName)}/dependencies`),
  getColumns: (tableName) => get(`/tables/${encodeURIComponent(tableName)}/columns`),
  getAllDependencies: (schema) => get('/tables/dependencies/all', { params: { schema } })
}

export const generate = {
  single: (params) => post('/generate', {
    table_name: params.table_name,
    count: params.count,
    strategy: params.strategy || 'normal',
    column_rules: params.column_rules,
    locale: params.locale || 'zh_CN'
  }),
  preview: (params) => post('/generate/preview', {
    table_name: params.table_name,
    count: params.count || 5,
    strategy: params.strategy || 'normal'
  }),
  batch: (params) => post('/generate/batch', {
    tables: params.tables,
    count_per_table: params.count_per_table || 10,
    strategy: params.strategy || 'normal',
    respect_dependencies: params.respect_dependencies !== false
  }),
  getStrategies: () => get('/generate/strategies', { showLoading: false }),
  getTypes: () => get('/generate/types', { showLoading: false }),
  clearData: (tableName) => del(`/generate/data/${tableName}`),
  clearAllData: () => del('/generate/data')
}

export const exportData = {
  toSql: (params) => post('/export/sql', {
    table_name: params.table_name,
    data: params.data,
    batch_size: params.batch_size || 100
  }),
  downloadSql: (params) => post('/export/download', {
    table_name: params.table_name,
    data: params.data,
    batch_size: params.batch_size || 100
  }, { responseType: 'blob' }),
  batch: (params) => post('/export/batch', {
    tables_data: params.tables_data,
    batch_size: params.batch_size || 100
  }),
  batchDownload: (params) => post('/export/batch/download', {
    tables_data: params.tables_data,
    batch_size: params.batch_size || 100
  }, { responseType: 'blob' }),
  getStored: (tableName) => get(`/export/data/${tableName}`)
}

export default apiClient
