// 数据生成状态管理
import { defineStore } from 'pinia'
import { generateDataApi, generatePreviewApi, exportSqlApi } from '@/api/generate'

export const useGenerateStore = defineStore('generate', {
  state: () => ({
    // 生成配置
    config: {
      tableName: '',
      count: 10,
      strategy: 'normal',
      locale: 'zh_CN',
      columnRules: [],
    },
    // 生成的数据
    generatedData: [],
    // SQL 语句
    sqlStatements: [],
    // 预览数据
    previewData: [],
    // 历史记录
    history: [],
    // 最大历史记录数
    maxHistory: 20,
    // 设置项
    defaultCount: 10,
    batchLimit: 1000,
    sqlDelimiter: ';',
    includeAutoIncrement: false,
  }),

  getters: {
    // 是否有生成数据
    hasData: (state) => state.generatedData.length > 0,
    
    // 是否有 SQL 语句
    hasSql: (state) => state.sqlStatements.length > 0,
    
    // SQL 文本
    sqlText: (state) => state.sqlStatements.join('\n'),
    
    // SQL 文件大小
    sqlFileSize: (state) => {
      const text = state.sqlStatements.join('\n')
      return new Blob([text]).size
    },
  },

  actions: {
    /**
     * 设置表名
     */
    setTableName(tableName) {
      this.config.tableName = tableName
    },

    /**
     * 设置生成数量
     */
    setCount(count) {
      this.config.count = count
    },

    /**
     * 设置生成策略
     */
    setStrategy(strategy) {
      this.config.strategy = strategy
    },

    /**
     * 设置字段规则
     */
    setColumnRules(rules) {
      this.config.columnRules = rules
    },

    /**
     * 更新单个字段规则
     */
    updateColumnRule(columnName, rule) {
      const index = this.config.columnRules.findIndex(r => r.column_name === columnName)
      if (index >= 0) {
        this.config.columnRules[index] = { ...this.config.columnRules[index], ...rule }
      } else {
        this.config.columnRules.push({ column_name: columnName, ...rule })
      }
    },

    /**
     * 清除字段规则
     */
    clearColumnRule(columnName) {
      const index = this.config.columnRules.findIndex(r => r.column_name === columnName)
      if (index >= 0) {
        this.config.columnRules.splice(index, 1)
      }
    },

    /**
     * 生成预览数据
     */
    async generatePreview(tableName, count = 5, strategy = 'normal') {
      try {
        const data = await generatePreviewApi(tableName, count, strategy, true)
        this.previewData = data.data || []
        return this.previewData
      } catch (error) {
        console.error('生成预览失败:', error)
        throw error
      }
    },

    /**
     * 生成数据
     */
    async generate() {
      if (!this.config.tableName) {
        throw new Error('请先选择表')
      }

      try {
        const result = await generateDataApi({
          table_name: this.config.tableName,
          count: this.config.count,
          strategy: this.config.strategy,
          column_rules: this.config.columnRules.length > 0 ? this.config.columnRules : null,
          locale: this.config.locale,
        }, true)

        this.generatedData = result.data || []
        
        // 添加到历史记录
        this.addToHistory({
          type: 'generate',
          tableName: this.config.tableName,
          count: this.config.count,
          strategy: this.config.strategy,
          timestamp: new Date().toISOString(),
          rowCount: this.generatedData.length,
        })

        return this.generatedData
      } catch (error) {
        console.error('生成数据失败:', error)
        throw error
      }
    },

    /**
     * 导出 SQL
     */
    async exportSql() {
      if (this.generatedData.length === 0) {
        throw new Error('没有可导出的数据')
      }

      try {
        const result = await exportSqlApi({
          table_name: this.config.tableName,
          data: this.generatedData,
          batch_size: 100,
        }, true)

        this.sqlStatements = result.sql_statements || []
        
        // 添加到历史记录
        this.addToHistory({
          type: 'export',
          tableName: this.config.tableName,
          timestamp: new Date().toISOString(),
          rowCount: this.generatedData.length,
          sqlCount: this.sqlStatements.length,
        })

        return this.sqlStatements
      } catch (error) {
        console.error('导出 SQL 失败:', error)
        throw error
      }
    },

    /**
     * 添加到历史记录
     */
    addToHistory(record) {
      this.history.unshift(record)
      if (this.history.length > this.maxHistory) {
        this.history.pop()
      }
    },

    /**
     * 清除生成数据
     */
    clearData() {
      this.generatedData = []
      this.sqlStatements = []
      this.previewData = []
    },

    /**
     * 重置配置
     */
    resetConfig() {
      this.config = {
        tableName: '',
        count: 10,
        strategy: 'normal',
        locale: 'zh_CN',
        columnRules: [],
      }
    },

    /**
     * 完全重置
     */
    reset() {
      this.resetConfig()
      this.clearData()
      this.history = []
    },
  },
})
