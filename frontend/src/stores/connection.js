import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  connectApi,
  disconnectApi,
  testConnectionApi,
  getStatusApi
} from '@/api/connection'
import { useTablesStore } from './tables'

export const useConnectionStore = defineStore('connection', () => {
  // 状态
  const connected = ref(false)
  const connecting = ref(false)
  const config = ref(null)
  const error = ref(null)
  const connectionInfo = ref(null)

  // 连接数据库
  const connect = async (connectionConfig) => {
    try {
      connecting.value = true
      error.value = null

      const response = await connectApi(connectionConfig)

      // 处理 ConnectionResponse 格式
      if (response.connected !== undefined) {
        connected.value = response.connected
        config.value = connectionConfig
        connectionInfo.value = response
        
        // 连接成功后获取表列表
        if (response.connected) {
          const tablesStore = useTablesStore()
          await tablesStore.fetchTables()
        }
        
        return { success: true }
      }
      // 处理 APIResponse 格式
      else if (response.success) {
        connected.value = true
        config.value = connectionConfig
        connectionInfo.value = response.data
        
        // 连接成功后获取表列表
        const tablesStore = useTablesStore()
        await tablesStore.fetchTables()
        
        return { success: true }
      } else {
        error.value = response.message || '连接失败'
        return { success: false, message: error.value }
      }
    } catch (err) {
      error.value = err.message || '连接失败'
      return { success: false, message: error.value }
    } finally {
      connecting.value = false
    }
  }

  // 断开连接
  const disconnect = async () => {
    try {
      connecting.value = true
      error.value = null

      const response = await disconnectApi()

      // 处理 APIResponse 格式
      if (response.success) {
        connected.value = false
        config.value = null
        connectionInfo.value = null
        
        // 断开连接后重置表状态
        const tablesStore = useTablesStore()
        tablesStore.reset()
        
        return { success: true }
      } else {
        error.value = response.message || '断开连接失败'
        return { success: false, message: error.value }
      }
    } catch (err) {
      error.value = err.message || '断开连接失败'
      return { success: false, message: error.value }
    } finally {
      connecting.value = false
    }
  }

  // 测试连接
  const testConnection = async (connectionConfig) => {
    try {
      error.value = null

      const response = await testConnectionApi(connectionConfig)

      if (response.success) {
        return { success: true, message: response.message || '连接测试成功' }
      } else {
        return { success: false, message: response.message || '连接测试失败' }
      }
    } catch (err) {
      return { success: false, message: err.message || '连接测试失败' }
    }
  }

  // 获取连接状态
  const getStatus = async () => {
    try {
      const response = await getStatusApi()

      if (response.connected !== undefined) {
        connected.value = response.connected
        connectionInfo.value = {
          db_type: response.db_type,
          database: response.database,
          pool_status: response.pool_status
        }
        return { success: true, data: response }
      } else if (response.success) {
        connected.value = response.data.connected
        connectionInfo.value = response.data.info || null
        return { success: true, data: response.data }
      } else {
        return { success: false, message: response.message }
      }
    } catch (err) {
      return { success: false, message: err.message }
    }
  }

  // 设置状态
  const setStatus = (status) => {
    if (status.connected !== undefined) {
      connected.value = status.connected
    }
    if (status.connecting !== undefined) {
      connecting.value = status.connecting
    }
    if (status.config !== undefined) {
      config.value = status.config
    }
    if (status.error !== undefined) {
      error.value = status.error
    }
    if (status.connectionInfo !== undefined) {
      connectionInfo.value = status.connectionInfo
    }
  }

  // 清除错误
  const clearError = () => {
    error.value = null
  }

  return {
    // 状态
    connected,
    connecting,
    config,
    error,
    connectionInfo,
    // 方法
    connect,
    disconnect,
    testConnection,
    getStatus,
    setStatus,
    clearError
  }
})
