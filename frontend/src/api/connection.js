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
    // 可以在这里添加 token 等
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
 * 连接数据库
 * @param {Object} config - 连接配置
 * @param {string} config.type - 数据库类型 (mysql, postgresql, sqlite)
 * @param {string} config.host - 主机地址
 * @param {number} config.port - 端口号
 * @param {string} config.database - 数据库名
 * @param {string} config.username - 用户名
 * @param {string} config.password - 密码
 * @returns {Promise}
 */
export const connectApi = (config) => {
  // 转换字段名
  const requestData = {
    db_type: config.type,
    host: config.host,
    port: config.port,
    database: config.database,
    username: config.username,
    password: config.password,
    pool_size: 5,
    max_overflow: 10
  }
  return apiClient.post('/connect', requestData)
}

/**
 * 断开数据库连接
 * @returns {Promise}
 */
export const disconnectApi = () => {
  return apiClient.post('/disconnect')
}

/**
 * 测试数据库连接
 * @param {Object} config - 连接配置
 * @returns {Promise}
 */
export const testConnectionApi = (config) => {
  // 转换字段名
  const requestData = {
    db_type: config.type,
    host: config.host,
    port: config.port,
    database: config.database,
    username: config.username,
    password: config.password,
    pool_size: 5,
    max_overflow: 10
  }
  return apiClient.post('/test', requestData)
}

/**
 * 获取连接状态
 * @returns {Promise}
 */
export const getStatusApi = () => {
  return apiClient.get('/status')
}
