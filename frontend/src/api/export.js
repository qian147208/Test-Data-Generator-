// 导出相关 API
import { ElMessage } from 'element-plus'

// API 基础地址
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

/**
 * 统一请求处理函数
 */
async function request(url, options = {}) {
  try {
    const response = await fetch(`${API_BASE_URL}${url}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const data = await response.json()
    return data
  } catch (error) {
    console.error('API request error:', error)
    throw error
  }
}

/**
 * 导出 SQL INSERT 语句
 * @param {Object} data - 导出配置
 * @param {string} data.table_name - 表名
 * @param {number} data.count - 生成数量
 * @param {string} data.strategy - 生成策略
 * @param {Object} data.column_config - 列配置
 */
export async function exportSQLApi(data) {
  try {
    const result = await request('/api/export/sql', {
      method: 'POST',
      body: JSON.stringify(data),
    })
    return result
  } catch (error) {
    ElMessage.error('导出 SQL 失败: ' + error.message)
    throw error
  }
}

/**
 * 下载 SQL 文件
 * @param {Object} data - 导出配置
 * @param {string} data.table_name - 表名
 * @param {number} data.count - 生成数量
 * @param {string} data.strategy - 生成策略
 * @param {Object} data.column_config - 列配置
 * @param {string} data.filename - 文件名
 */
export async function downloadSQLApi(data) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/export/sql/download`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    // 获取文件名
    const contentDisposition = response.headers.get('Content-Disposition')
    let filename = 'export.sql'
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/)
      if (filenameMatch && filenameMatch[1]) {
        filename = filenameMatch[1].replace(/['"]/g, '')
      }
    }

    // 创建 Blob 并下载
    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)

    return { success: true, filename }
  } catch (error) {
    ElMessage.error('下载 SQL 文件失败: ' + error.message)
    throw error
  }
}

/**
 * 获取导出历史记录
 */
export async function getExportHistoryApi() {
  try {
    const result = await request('/api/export/history')
    return result.data || result
  } catch (error) {
    ElMessage.error('获取导出历史失败: ' + error.message)
    throw error
  }
}
