import { defineStore } from 'pinia'
import { ref } from 'vue'
import { connection } from '@/api'

export const useConnectionStore = defineStore('connection', () => {
  const connected = ref(false)
  const connecting = ref(false)
  const config = ref(null)
  const error = ref(null)
  const connectionInfo = ref(null)

  const connect = async (connectionConfig) => {
    try {
      connecting.value = true
      error.value = null

      const response = await connection.connect(connectionConfig)

      if (!response.connected) {
        connected.value = false
        error.value = response.message || '连接失败'
        return { success: false, message: error.value }
      }

      connected.value = true
      config.value = connectionConfig
      connectionInfo.value = response

      const { useTablesStore } = await import('./tables')
      const tablesStore = useTablesStore()
      await tablesStore.fetchTables()

      return { success: true }
    } catch (err) {
      error.value = err.message
      return { success: false, message: err.message }
    } finally {
      connecting.value = false
    }
  }

  const disconnecting = ref(false)

  const disconnect = async () => {
    try {
      disconnecting.value = true
      error.value = null

      const response = await connection.disconnect()

      if (!response.success) {
        error.value = response.message || '断开连接失败'
        return { success: false, message: error.value }
      }

      connected.value = false
      config.value = null
      connectionInfo.value = null
      const { useTablesStore } = await import('./tables')
      useTablesStore().reset()

      return { success: true }
    } catch (err) {
      error.value = err.message
      return { success: false, message: err.message }
    } finally {
      disconnecting.value = false
    }
  }

  const testConnection = async (connectionConfig) => {
    try {
      error.value = null
      await connection.test(connectionConfig)
      return { success: true, message: '连接测试成功' }
    } catch (err) {
      return { success: false, message: err.message }
    }
  }

  const getStatus = async () => {
    try {
      const response = await connection.getStatus()
      connected.value = response.connected
      connectionInfo.value = {
        db_type: response.db_type,
        database: response.database,
        pool_status: response.pool_status
      }
      return { success: true, data: response }
    } catch (err) {
      return { success: false, message: err.message }
    }
  }

  const setStatus = (status) => {
    Object.entries(status).forEach(([key, value]) => {
      if (['connected', 'connecting', 'config', 'error', 'connectionInfo'].includes(key)) {
        if (key === 'error') error.value = value
        else if (key === 'connectionInfo') connectionInfo.value = value
        else if (key === 'connected') connected.value = value
        else if (key === 'connecting') connecting.value = value
        else config.value = value
      }
    })
  }

  const clearError = () => { error.value = null }

  return {
    connected, connecting, disconnecting, config, error, connectionInfo,
    connect, disconnect, testConnection, getStatus, setStatus, clearError
  }
})
