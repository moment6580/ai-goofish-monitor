import { ref, reactive, watch, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import type { ResultInsights, ResultItem } from '@/types/result.d.ts'
import * as resultsApi from '@/api/results'
import type { GetResultContentParams } from '@/api/results'
import { useWebSocket } from '@/composables/useWebSocket'
import * as tasksApi from '@/api/tasks'

export function useResults() {
  const { t } = useI18n()
  const route = useRoute()
  // State
  const files = ref<string[]>([])
  const selectedFile = ref<string | null>(null)
  const results = ref<ResultItem[]>([])
  const insights = ref<ResultInsights | null>(null)
  const totalItems = ref(0)
  const page = ref(1)
  const blacklistKeywords = ref<string[]>([])
  const taskNameByKeyword = ref<Record<string, string>>({})
  const isFileOptionsReady = ref(false)
  const hasFetchedFiles = ref(false)
  const hasFetchedTasks = ref(false)
  const isSavingBlacklist = ref(false)
  const readyDelayMs = 200
  let readyTimer: ReturnType<typeof setTimeout> | null = null
  
  const STORAGE_KEY_FILTERS = 'resultFilters'

  function loadPersistedFilters(): Required<Omit<GetResultContentParams, 'page' | 'limit'>> {
    const defaults: Required<Omit<GetResultContentParams, 'page' | 'limit'>> = {
      recommended_only: false,
      ai_recommended_only: false,
      keyword_recommended_only: false,
      include_hidden: false,
      sort_by: 'crawl_time',
      sort_order: 'desc',
    }
    try {
      const saved = localStorage.getItem(STORAGE_KEY_FILTERS)
      if (saved) return { ...defaults, ...JSON.parse(saved) }
    } catch { /* ignore */ }
    return defaults
  }

  const filters = reactive<Required<Omit<GetResultContentParams, 'page' | 'limit'>>>(loadPersistedFilters())

  const isLoading = ref(false)
  const isLoadingMore = ref(false)
  const error = ref<Error | null>(null)
  const { on } = useWebSocket()

  const PAGE_SIZE = 100

  function normalizeKeyword(value: string) {
    return value.trim().toLowerCase().replace(/\s+/g, '_')
  }

  function getKeywordFromFilename(filename: string) {
    return filename.replace(/_full_data\.jsonl$/i, '').toLowerCase()
  }

  const hasMoreResults = computed(() => results.value.length < totalItems.value)

  // Methods
  async function fetchFiles() {
    try {
      const fileList = await resultsApi.getResultFiles()
      files.value = fileList
      // If a file is selected that no longer exists, reset it.
      // Otherwise, if nothing is selected, select the first file by default.
      if (selectedFile.value && fileList.includes(selectedFile.value)) {
        return
      }

      const lastSelected = localStorage.getItem('lastSelectedResultFile')
      if (lastSelected && fileList.includes(lastSelected)) {
        selectedFile.value = lastSelected
        return
      }

      selectedFile.value = fileList[0] || null
    } catch (e) {
      if (e instanceof Error) error.value = e
    } finally {
      hasFetchedFiles.value = true
      scheduleFileOptionsReady()
    }
  }

  async function fetchResults() {
    if (!selectedFile.value) {
      results.value = []
      totalItems.value = 0
      page.value = 1
      return
    }

    isLoading.value = true
    error.value = null
    page.value = 1
    try {
      const data = await resultsApi.getResultContent(selectedFile.value, {
        ...filters,
        page: 1,
        limit: PAGE_SIZE,
      })
      results.value = data.items
      totalItems.value = data.total_items
    } catch (e) {
      if (e instanceof Error) error.value = e
      results.value = []
      totalItems.value = 0
    } finally {
      isLoading.value = false
    }
  }

  /** 追加加载下一页（真正的服务端分页，支持超过 100 条的结果集）。 */
  async function loadMoreResults() {
    if (!selectedFile.value || isLoading.value || isLoadingMore.value) return
    if (!hasMoreResults.value) return

    isLoadingMore.value = true
    try {
      const nextPage = page.value + 1
      const data = await resultsApi.getResultContent(selectedFile.value, {
        ...filters,
        page: nextPage,
        limit: PAGE_SIZE,
      })
      // 去重后追加，避免与已加载项重复
      const existingIds = new Set(results.value.map((item) => item.商品信息?.商品ID))
      const appended = data.items.filter((item) => !existingIds.has(item.商品信息?.商品ID))
      results.value = [...results.value, ...appended]
      totalItems.value = data.total_items
      page.value = nextPage
    } catch (e) {
      if (e instanceof Error) error.value = e
    } finally {
      isLoadingMore.value = false
    }
  }

  /** 重新拉取已加载的页（用于实时更新/黑名单变更后保持一致）。 */
  async function refreshLoadedPages() {
    if (!selectedFile.value) return
    const loadedPages = Math.max(1, Math.ceil(results.value.length / PAGE_SIZE))
    try {
      const pages = await Promise.all(
        Array.from({ length: loadedPages }, (_, index) =>
          resultsApi.getResultContent(selectedFile.value as string, {
            ...filters,
            page: index + 1,
            limit: PAGE_SIZE,
          }),
        ),
      )
      const merged: ResultItem[] = []
      for (const data of pages) {
        merged.push(...data.items)
      }
      results.value = merged
      totalItems.value = pages[0]?.total_items ?? merged.length
      page.value = loadedPages
    } catch (e) {
      if (e instanceof Error) error.value = e
    }
  }

  async function fetchInsights() {
    if (!selectedFile.value) {
      insights.value = null
      return
    }

    try {
      insights.value = await resultsApi.getResultInsights(selectedFile.value)
    } catch (e) {
      if (e instanceof Error) error.value = e
      insights.value = null
    }
  }

  async function fetchBlacklistRules() {
    if (!selectedFile.value) {
      blacklistKeywords.value = []
      return
    }

    try {
      const data = await resultsApi.getResultBlacklistRules(selectedFile.value)
      blacklistKeywords.value = data.keywords || []
    } catch (e) {
      if (e instanceof Error) error.value = e
      blacklistKeywords.value = []
    }
  }

  async function fetchTaskNameMap() {
    try {
      const tasks = await tasksApi.getAllTasks()
      const mapping: Record<string, string> = {}
      tasks.forEach((task) => {
        if (task.keyword) {
          mapping[normalizeKeyword(task.keyword)] = task.task_name
        }
      })
      taskNameByKeyword.value = mapping
    } catch (e) {
      if (e instanceof Error) error.value = e
    } finally {
      hasFetchedTasks.value = true
      scheduleFileOptionsReady()
    }
  }

  function scheduleFileOptionsReady() {
    if (isFileOptionsReady.value || !hasFetchedFiles.value || !hasFetchedTasks.value) return
    if (readyTimer) return
    readyTimer = setTimeout(() => {
      isFileOptionsReady.value = true
      readyTimer = null
    }, readyDelayMs)
  }

  // Real-time updates
  on('results_updated', async () => {
    const oldFile = selectedFile.value
    await fetchFiles()
    // If the selected file remains the same, refresh all currently loaded pages
    // If it changed (e.g. from null to new file), the watcher will handle it.
    if (selectedFile.value && selectedFile.value === oldFile) {
      refreshLoadedPages()
      fetchInsights()
    }
  })

  on('tasks_updated', () => {
    fetchTaskNameMap()
  })

  async function refreshResults() {
    const current = selectedFile.value
    await fetchFiles()
    if (selectedFile.value && selectedFile.value === current) {
      await fetchResults()
      await fetchInsights()
      await fetchBlacklistRules()
    }
  }

  function exportSelectedResults() {
    if (!selectedFile.value) return
    resultsApi.downloadResultExport(selectedFile.value, { ...filters })
  }

  async function deleteSelectedFile(filename?: string) {
    const target = filename || selectedFile.value
    if (!target) return
    isLoading.value = true
    error.value = null
    try {
      await resultsApi.deleteResultFile(target)
      if (selectedFile.value === target) {
        const lastSelected = localStorage.getItem('lastSelectedResultFile')
        if (lastSelected === target) {
          localStorage.removeItem('lastSelectedResultFile')
        }
      }
      await fetchFiles()
    } catch (e) {
      if (e instanceof Error) error.value = e
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function toggleItemBlock(item: ResultItem) {
    if (!selectedFile.value) return
    const itemId = item.商品信息?.商品ID
    if (!itemId) return
    const newStatus = item._status === 'hidden' ? 'active' : 'hidden'
    // 乐观更新，交互即时响应
    item._status = newStatus
    item._effective_hidden = newStatus === 'hidden'
    try {
      await resultsApi.updateItemStatus(selectedFile.value, itemId, newStatus)
      // 后台按服务端重新校准（总数/隐藏原因/黑名单命中都以服务端为准）
      await refreshLoadedPages()
    } catch (e) {
      if (e instanceof Error) error.value = e
      // 失败回滚
      item._status = newStatus === 'hidden' ? 'active' : 'hidden'
      item._effective_hidden = item._status === 'hidden'
    }
  }

  async function saveBlacklistRules(keywords: string[]) {
    if (!selectedFile.value) return
    isSavingBlacklist.value = true
    error.value = null
    try {
      const data = await resultsApi.updateResultBlacklistRules(selectedFile.value, keywords)
      blacklistKeywords.value = data.keywords || []
      await fetchResults()
      await fetchInsights()
    } catch (e) {
      if (e instanceof Error) error.value = e
      throw e
    } finally {
      isSavingBlacklist.value = false
    }
  }

  // Watchers
  watch(filters, (val) => {
    localStorage.setItem(STORAGE_KEY_FILTERS, JSON.stringify(val))
  }, { deep: true })
  watch([selectedFile, filters], fetchResults, { deep: true })
  watch(selectedFile, () => {
    fetchInsights()
    fetchBlacklistRules()
  })
  watch(selectedFile, (value) => {
    if (value) localStorage.setItem('lastSelectedResultFile', value)
  })
  watch(
    [() => route.query.file, files],
    ([routeFile, currentFiles]) => {
      if (typeof routeFile !== 'string') return
      if (currentFiles.includes(routeFile)) {
        selectedFile.value = routeFile
      }
    },
    { immediate: true }
  )

  const fileOptions = computed(() =>
    files.value.map((file) => {
      const keyword = getKeywordFromFilename(file)
      const taskName = taskNameByKeyword.value[keyword]
      return {
        value: file,
        taskName: taskName || t('common.unnamed'),
        label: t('results.filters.taskNameLabel', {
          task: taskName || t('common.unnamed'),
        }),
      }
    })
  )

  // Lifecycle
  onMounted(() => {
    fetchFiles()
    fetchTaskNameMap()
  })

  return {
    files,
    selectedFile,
    results,
    insights,
    totalItems,
    hasMoreResults,
    isLoadingMore,
    filters,
    isLoading,
    error,
    fetchFiles, // Expose to allow manual refresh
    refreshResults,
    loadMoreResults,
    exportSelectedResults,
    deleteSelectedFile,
    toggleItemBlock,
    blacklistKeywords,
    isSavingBlacklist,
    saveBlacklistRules,
    fileOptions,
    isFileOptionsReady,
  }
}
