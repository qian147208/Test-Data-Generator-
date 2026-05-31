// 表状态管理
import { defineStore } from 'pinia'
import { getTablesApi, getTableDetailsApi, getTableDependenciesApi } from '@/api/tables'

export const useTablesStore = defineStore('tables', {
  state: () => ({
    // 表列表
    tables: [],
    // 当前选中的表
    currentTable: null,
    // 加载状态
    loading: false,
    // 表详情缓存
    tableDetails: {},
    // 表依赖关系缓存
    tableDependencies: {},
    // 搜索关键词
    searchKeyword: '',
  }),

  getters: {
    // 过滤后的表列表
    filteredTables: (state) => {
      if (!state.searchKeyword) {
        return state.tables
      }
      const keyword = state.searchKeyword.toLowerCase()
      return state.tables.filter(table => {
        const tableName = (table.name || table.table_name || '').toLowerCase()
        const comment = (table.comment || table.table_comment || '').toLowerCase()
        return tableName.includes(keyword) || comment.includes(keyword)
      })
    },

    // 当前表详情
    currentTableDetails: (state) => {
      if (!state.currentTable) return null
      const tableName = state.currentTable.name || state.currentTable.table_name
      return state.tableDetails[tableName] || null
    },

    // 当前表依赖关系
    currentTableDependencies: (state) => {
      if (!state.currentTable) return null
      const tableName = state.currentTable.name || state.currentTable.table_name
      return state.tableDependencies[tableName] || null
    },
  },

  actions: {
    /**
     * 获取表列表
     */
    async fetchTables() {
      console.log('开始获取表列表...')
      this.loading = true
      try {
        const data = await getTablesApi({
          batchSize: 15,
          onProgress: (progress) => {
            console.log(`获取表列表进度: ${progress}%`)
            // 可以在这里添加进度条更新逻辑
          }
        })
        console.log('获取表列表响应:', data)
        console.log('响应类型:', typeof data)
        console.log('是否为数组:', Array.isArray(data))
        this.tables = Array.isArray(data) ? data : (data.tables || [])
        console.log('处理后的表列表:', this.tables)
        console.log('表数量:', this.tables.length)
        return this.tables
      } catch (error) {
        console.error('获取表列表失败:', error)
        console.error('错误堆栈:', error.stack)
        throw error
      } finally {
        this.loading = false
        console.log('获取表列表完成')
      }
    },

    /**
     * 防抖函数
     */
    debounce(func, wait) {
      let timeout
      return function executedFunction(...args) {
        const later = () => {
          clearTimeout(timeout)
          func(...args)
        }
        clearTimeout(timeout)
        timeout = setTimeout(later, wait)
      }
    },

    /**
     * 初始化防抖方法
     */
    initDebouncedMethods() {
      // 防抖搜索
      this.debouncedSearch = this.debounce((keyword) => {
        this.searchTables(keyword)
      }, 300)
    },

    /**
     * 获取表详情
     * @param {string} tableName - 表名
     */
    async fetchTableDetails(tableName) {
      this.loading = true
      try {
        const data = await getTableDetailsApi(tableName)
        this.tableDetails[tableName] = data
        return data
      } catch (error) {
        console.error('获取表详情失败:', error)
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * 获取表依赖关系
     * @param {string} tableName - 表名
     */
    async fetchTableDependencies(tableName) {
      try {
        const data = await getTableDependenciesApi(tableName)
        this.tableDependencies[tableName] = data
        return data
      } catch (error) {
        console.error('获取表依赖关系失败:', error)
        throw error
      }
    },

    /**
     * 选中表
     * @param {Object} table - 表对象
     */
    async selectTable(table) {
      this.currentTable = table
      const tableName = table.table_name

      // 批量获取表详情和依赖关系，避免多次单独请求
      const requests = []
      
      // 如果没有缓存，则获取详情
      if (!this.tableDetails[tableName]) {
        requests.push(this.fetchTableDetails(tableName))
      }

      // 获取依赖关系
      if (!this.tableDependencies[tableName]) {
        requests.push(
          this.fetchTableDependencies(tableName).catch(error => {
            // 依赖关系获取失败不影响主流程
            console.warn('获取依赖关系失败:', error)
          })
        )
      }

      // 并行执行请求
      if (requests.length > 0) {
        await Promise.all(requests)
      }
    },

    /**
     * 批量获取表详情
     * @param {Array} tableNames - 表名数组
     */
    async fetchBatchTableDetails(tableNames) {
      const requests = tableNames.map(tableName => {
        if (!this.tableDetails[tableName]) {
          return this.fetchTableDetails(tableName).catch(error => {
            console.warn(`获取表 ${tableName} 详情失败:`, error)
          })
        }
        return Promise.resolve()
      })
      
      await Promise.all(requests)
    },

    /**
     * 搜索表
     * @param {string} keyword - 搜索关键词
     */
    searchTables(keyword) {
      this.searchKeyword = keyword
    },

    /**
     * 清除当前选中
     */
    clearCurrentTable() {
      this.currentTable = null
    },

    /**
     * 重置状态
     */
    reset() {
      this.tables = []
      this.currentTable = null
      this.loading = false
      this.tableDetails = {}
      this.tableDependencies = {}
      this.searchKeyword = ''
    },
  },
})
