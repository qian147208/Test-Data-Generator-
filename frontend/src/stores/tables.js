import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { tables } from '@/api'

export const useTablesStore = defineStore('tables', () => {
  const tablesList = ref([])
  const currentTable = ref(null)
  const loading = ref(false)
  const tableDetails = ref({})
  const tableDependencies = ref({})
  const searchKeyword = ref('')

  const filteredTables = computed(() => {
    if (!searchKeyword.value) return tablesList.value
    const keyword = searchKeyword.value.toLowerCase()
    return tablesList.value.filter(t => {
      const name = (t.table_name || '').toLowerCase()
      const comment = (t.comment || '').toLowerCase()
      return name.includes(keyword) || comment.includes(keyword)
    })
  })

  const currentTableDetails = computed(() => {
    if (!currentTable.value) return null
    return tableDetails.value[currentTable.value.table_name] || null
  })

  const currentTableDependencies = computed(() => {
    if (!currentTable.value) return null
    return tableDependencies.value[currentTable.value.table_name] || null
  })

  const fetchTables = async () => {
    loading.value = true
    try {
      const data = await tables.getAll()
      tablesList.value = Array.isArray(data) ? data : []
      return tablesList.value
    } catch (error) {
      console.error('获取表列表失败:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  const fetchTableDetails = async (tableName) => {
    loading.value = true
    try {
      const data = await tables.getDetails(tableName)
      tableDetails.value[tableName] = data
      return data
    } catch (error) {
      console.error('获取表详情失败:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  const fetchTableDependencies = async (tableName) => {
    try {
      const data = await tables.getDependencies(tableName)
      tableDependencies.value[tableName] = data
      return data
    } catch (error) {
      console.warn('获取依赖关系失败:', error)
    }
  }

  const selectTable = async (table) => {
    currentTable.value = table
    const tableName = table.table_name
    const requests = []

    if (!tableDetails.value[tableName]) {
      requests.push(fetchTableDetails(tableName))
    }
    if (!tableDependencies.value[tableName]) {
      requests.push(fetchTableDependencies(tableName).catch(err => console.warn(err)))
    }

    if (requests.length > 0) {
      await Promise.all(requests)
    }
  }

  const fetchBatchTableDetails = async (tableNames) => {
    await Promise.all(
      tableNames.map(name =>
        !tableDetails.value[name]
          ? fetchTableDetails(name).catch(err => console.warn(`获取 ${name} 详情失败:`, err))
          : Promise.resolve()
      )
    )
  }

  const searchTables = (keyword) => {
    searchKeyword.value = keyword
  }

  const clearCurrentTable = () => {
    currentTable.value = null
  }

  const reset = () => {
    tablesList.value = []
    currentTable.value = null
    loading.value = false
    tableDetails.value = {}
    tableDependencies.value = {}
    searchKeyword.value = ''
  }

  return {
    tables: tablesList,
    currentTable,
    loading,
    tableDetails,
    tableDependencies,
    searchKeyword,
    filteredTables,
    currentTableDetails,
    currentTableDependencies,
    fetchTables,
    fetchTableDetails,
    fetchTableDependencies,
    selectTable,
    fetchBatchTableDetails,
    searchTables,
    clearCurrentTable,
    reset
  }
})
