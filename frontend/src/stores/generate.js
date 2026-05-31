import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { generate, exportData } from '@/api'
import { ElMessage } from 'element-plus'

export const useGenerateStore = defineStore('generate', () => {
  const config = ref({
    tableName: '',
    count: 10,
    strategy: 'normal',
    locale: 'zh_CN',
    columnRules: []
  })

  const generatedData = ref([])
  const sqlStatements = ref([])
  const previewData = ref([])
  const history = ref([])
  const maxHistory = 20

  const hasData = computed(() => generatedData.value.length > 0)
  const hasSql = computed(() => sqlStatements.value.length > 0)
  const sqlText = computed(() => sqlStatements.value.join('\n'))
  const sqlFileSize = computed(() => new Blob([sqlText.value]).size)

  const setTableName = (name) => { config.value.tableName = name }
  const setCount = (count) => { config.value.count = count }
  const setStrategy = (strategy) => { config.value.strategy = strategy }
  const setColumnRules = (rules) => { config.value.columnRules = rules }

  const updateColumnRule = (columnName, rule) => {
    const idx = config.value.columnRules.findIndex(r => r.column_name === columnName)
    if (idx >= 0) {
      config.value.columnRules[idx] = { ...config.value.columnRules[idx], ...rule }
    } else {
      config.value.columnRules.push({ column_name: columnName, ...rule })
    }
  }

  const clearColumnRule = (columnName) => {
    const idx = config.value.columnRules.findIndex(r => r.column_name === columnName)
    if (idx >= 0) config.value.columnRules.splice(idx, 1)
  }

  const generatePreview = async (tableName, count = 5, strategy = 'normal') => {
    try {
      const data = await generate.preview({ table_name: tableName, count, strategy })
      previewData.value = data.data || []
      return previewData.value
    } catch (error) {
      console.error('生成预览失败:', error)
      throw error
    }
  }

  const generateData = async () => {
    if (!config.value.tableName) throw new Error('请先选择表')

    try {
      const result = await generate.single({
        table_name: config.value.tableName,
        count: config.value.count,
        strategy: config.value.strategy,
        column_rules: config.value.columnRules.length > 0 ? config.value.columnRules : null,
        locale: config.value.locale
      })

      generatedData.value = result.data || []
      addToHistory({
        type: 'generate',
        tableName: config.value.tableName,
        count: config.value.count,
        strategy: config.value.strategy,
        timestamp: new Date().toISOString(),
        rowCount: generatedData.value.length
      })

      return generatedData.value
    } catch (error) {
      console.error('生成数据失败:', error)
      throw error
    }
  }

  const exportSql = async () => {
    if (generatedData.value.length === 0) throw new Error('没有可导出的数据')

    try {
      const result = await exportData.toSql({
        table_name: config.value.tableName,
        data: generatedData.value,
        batch_size: 100
      })

      sqlStatements.value = result.sql_statements || []
      addToHistory({
        type: 'export',
        tableName: config.value.tableName,
        timestamp: new Date().toISOString(),
        rowCount: generatedData.value.length,
        sqlCount: sqlStatements.value.length
      })

      return sqlStatements.value
    } catch (error) {
      console.error('导出 SQL 失败:', error)
      throw error
    }
  }

  const downloadSql = (tableName, data) => {
    if (!data || data.length === 0) {
      ElMessage.warning('没有数据可下载')
      return
    }

    const sqlContent = data.map(row => {
      const columns = Object.keys(row)
      const values = Object.values(row).map(v => {
        if (v === null || v === undefined) return 'NULL'
        if (typeof v === 'string') return `'${v.replace(/'/g, "''")}'`
        if (v instanceof Date) return `'${v.toISOString()}'`
        return v
      })
      return `INSERT INTO \`${tableName}\` (\`${columns.join('`, `')}\`) VALUES (${values.join(', ')});`
    }).join('\n')

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
  }

  const addToHistory = (record) => {
    history.value.unshift(record)
    if (history.value.length > maxHistory) history.value.pop()
  }

  const clearData = () => {
    generatedData.value = []
    sqlStatements.value = []
    previewData.value = []
  }

  const resetConfig = () => {
    config.value = {
      tableName: '',
      count: 10,
      strategy: 'normal',
      locale: 'zh_CN',
      columnRules: []
    }
  }

  const reset = () => {
    resetConfig()
    clearData()
    history.value = []
  }

  return {
    config,
    generatedData,
    sqlStatements,
    previewData,
    history,
    hasData,
    hasSql,
    sqlText,
    sqlFileSize,
    setTableName,
    setCount,
    setStrategy,
    setColumnRules,
    updateColumnRule,
    clearColumnRule,
    generatePreview,
    generate: generateData,
    exportSql,
    downloadSql,
    addToHistory,
    clearData,
    resetConfig,
    reset
  }
})
