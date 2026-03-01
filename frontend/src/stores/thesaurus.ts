import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { apolloClient } from '@/services/apollo'
import type { TermPair, Catalog, ImportResult, PaginatedTermPairs } from '@/types'
import {
  TERM_PAIRS_QUERY,
  CATALOGS_QUERY,
  EXPORT_TERMS_CSV_QUERY,
  ADD_TERM_PAIR_MUTATION,
  EDIT_TERM_PAIR_MUTATION,
  DELETE_TERM_PAIR_MUTATION,
  BULK_DELETE_TERM_PAIRS_MUTATION,
  IMPORT_TERMS_CSV_MUTATION,
  CREATE_CATALOG_MUTATION,
  UPDATE_CATALOG_MUTATION,
  DELETE_CATALOG_MUTATION,
} from '@/graphql/thesaurus'

const CATALOGS_STORAGE_KEY = 'thesaurus_catalogs'

// GraphQL Response Types
interface CatalogsQueryResult {
  catalogs: Catalog[]
}

interface TermPairsQueryResult {
  termPairs: PaginatedTermPairs
}

interface ExportTermsCsvQueryResult {
  exportTermsCsv: string
}

interface CreateCatalogMutationResult {
  createCatalog: Catalog
}

interface UpdateCatalogMutationResult {
  updateCatalog: Catalog
}

interface DeleteCatalogMutationResult {
  deleteCatalog: number
}

interface AddTermPairMutationResult {
  addTermPair: TermPair
}

interface EditTermPairMutationResult {
  editTermPair: TermPair
}

interface DeleteTermPairMutationResult {
  deleteTermPair: boolean
}

interface BulkDeleteTermPairsMutationResult {
  bulkDeleteTermPairs: number
}

interface ImportTermsCsvMutationResult {
  importTermsCsv: ImportResult
}

export const useThesaurusStore = defineStore('thesaurus', () => {
  // State
  const termPairs = ref<TermPair[]>([])
  const catalogs = ref<Catalog[]>([])
  const selectedLanguagePairId = ref<string | null>(null)
  const selectedCatalogId = ref<string | null>(null)
  const searchText = ref<string>('')
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  
  // Pagination state
  const currentPage = ref(1)
  const pageSize = ref(100)
  const totalItems = ref(0)
  const hasNextPage = ref(false)

  // Computed properties
  const hasCatalogs = computed(() => catalogs.value.length > 0)
  
  const hasTermPairs = computed(() => termPairs.value.length > 0)
  
  const selectedCatalog = computed(() => 
    catalogs.value.find((c: Catalog) => c.id === selectedCatalogId.value) || null
  )
  
  const totalPages = computed(() => 
    Math.ceil(totalItems.value / pageSize.value)
  )
  
  const getCatalogById = computed(() => (id: string) =>
    catalogs.value.find((c: Catalog) => c.id === id)
  )

  // =========================================================================
  // Catalog Actions
  // =========================================================================

  /**
   * Fetch all catalogs for a language pair
   */
  async function fetchCatalogs(languagePairId: string): Promise<Catalog[]> {
    isLoading.value = true
    error.value = null
    
    try {
      const { data } = await apolloClient.query<CatalogsQueryResult>({
        query: CATALOGS_QUERY,
        variables: { languagePairId },
        fetchPolicy: 'network-only',
      })
      
      catalogs.value = data?.catalogs ? [...data.catalogs] : []
      selectedLanguagePairId.value = languagePairId
      persistCatalogs()
      return catalogs.value
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch catalogs'
      error.value = errorMessage
      throw err
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Create a new catalog
   */
  async function createCatalog(
    languagePairId: string,
    name: string,
    description?: string
  ): Promise<Catalog> {
    isLoading.value = true
    error.value = null
    
    try {
      const { data } = await apolloClient.mutate<CreateCatalogMutationResult>({
        mutation: CREATE_CATALOG_MUTATION,
        variables: { languagePairId, name, description },
      })
      
      if (!data?.createCatalog) {
        throw new Error('Failed to create catalog')
      }
      
      const newCatalog = data.createCatalog
      catalogs.value = [...catalogs.value, newCatalog]
      persistCatalogs()
      return newCatalog
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to create catalog'
      error.value = errorMessage
      throw err
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Update a catalog's name or description
   */
  async function updateCatalog(
    languagePairId: string,
    catalogId: string,
    name?: string,
    description?: string
  ): Promise<Catalog> {
    isLoading.value = true
    error.value = null
    
    try {
      const { data } = await apolloClient.mutate<UpdateCatalogMutationResult>({
        mutation: UPDATE_CATALOG_MUTATION,
        variables: { languagePairId, catalogId, name, description },
      })
      
      if (!data?.updateCatalog) {
        throw new Error('Failed to update catalog')
      }
      
      const updatedCatalog = data.updateCatalog
      const index = catalogs.value.findIndex((c: Catalog) => c.id === catalogId)
      if (index !== -1) {
        catalogs.value[index] = updatedCatalog
        catalogs.value = [...catalogs.value]
      }
      persistCatalogs()
      return updatedCatalog
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to update catalog'
      error.value = errorMessage
      throw err
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Delete a catalog and all its term pairs
   */
  async function deleteCatalog(
    languagePairId: string,
    catalogId: string
  ): Promise<number> {
    isLoading.value = true
    error.value = null
    
    try {
      const { data } = await apolloClient.mutate<DeleteCatalogMutationResult>({
        mutation: DELETE_CATALOG_MUTATION,
        variables: { languagePairId, catalogId },
      })
      
      catalogs.value = catalogs.value.filter((c: Catalog) => c.id !== catalogId)
      
      // Clear term pairs if the deleted catalog was selected
      if (selectedCatalogId.value === catalogId) {
        selectedCatalogId.value = null
        termPairs.value = []
        totalItems.value = 0
      }
      
      persistCatalogs()
      return data?.deleteCatalog ?? 0
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete catalog'
      error.value = errorMessage
      throw err
    } finally {
      isLoading.value = false
    }
  }

  // =========================================================================
  // Term Pair Actions
  // =========================================================================

  /**
   * Fetch term pairs with optional filtering and pagination
   */
  async function fetchTermPairs(
    languagePairId: string,
    catalogId?: string,
    search?: string,
    page: number = 1,
    size: number = 100
  ): Promise<PaginatedTermPairs> {
    isLoading.value = true
    error.value = null
    
    try {
      const { data } = await apolloClient.query<TermPairsQueryResult>({
        query: TERM_PAIRS_QUERY,
        variables: {
          languagePairId,
          catalogId: catalogId || null,
          search: search || null,
          page,
          pageSize: size,
        },
        fetchPolicy: 'network-only',
      })
      
      if (!data?.termPairs) {
        throw new Error('Failed to fetch term pairs')
      }
      
      const result = data.termPairs
      termPairs.value = [...result.items]
      totalItems.value = result.total
      currentPage.value = result.page
      pageSize.value = result.pageSize
      hasNextPage.value = result.hasNext
      selectedLanguagePairId.value = languagePairId
      selectedCatalogId.value = catalogId || null
      searchText.value = search || ''
      
      return result
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch term pairs'
      error.value = errorMessage
      throw err
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Add or update a term pair (upsert behavior)
   */
  async function addTermPair(
    languagePairId: string,
    catalogId: string,
    sourceTerm: string,
    targetTerm: string
  ): Promise<TermPair> {
    isLoading.value = true
    error.value = null
    
    try {
      const { data } = await apolloClient.mutate<AddTermPairMutationResult>({
        mutation: ADD_TERM_PAIR_MUTATION,
        variables: { languagePairId, catalogId, sourceTerm, targetTerm },
      })
      
      if (!data?.addTermPair) {
        throw new Error('Failed to add term pair')
      }
      
      const newTermPair = data.addTermPair
      
      // Update local state - check if it's an update or new
      const existingIndex = termPairs.value.findIndex(
        (t: TermPair) => t.sourceTerm === sourceTerm && t.catalogId === catalogId
      )
      
      if (existingIndex !== -1) {
        termPairs.value[existingIndex] = newTermPair
        termPairs.value = [...termPairs.value]
      } else {
        termPairs.value = [newTermPair, ...termPairs.value]
        totalItems.value += 1
        
        // Update catalog term count
        const catalogIndex = catalogs.value.findIndex((c: Catalog) => c.id === catalogId)
        if (catalogIndex !== -1) {
          const existingCatalog = catalogs.value[catalogIndex]
          if (existingCatalog) {
            catalogs.value[catalogIndex] = {
              ...existingCatalog,
              termCount: existingCatalog.termCount + 1,
            }
            catalogs.value = [...catalogs.value]
            persistCatalogs()
          }
        }
      }
      
      return newTermPair
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to add term pair'
      error.value = errorMessage
      throw err
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Edit an existing term pair's target term
   */
  async function editTermPair(
    termId: string,
    targetTerm: string
  ): Promise<TermPair> {
    isLoading.value = true
    error.value = null
    
    try {
      const { data } = await apolloClient.mutate<EditTermPairMutationResult>({
        mutation: EDIT_TERM_PAIR_MUTATION,
        variables: { termId, targetTerm },
      })
      
      if (!data?.editTermPair) {
        throw new Error('Failed to edit term pair')
      }
      
      const updatedTermPair = data.editTermPair
      const index = termPairs.value.findIndex((t: TermPair) => t.id === termId)
      if (index !== -1) {
        termPairs.value[index] = updatedTermPair
        termPairs.value = [...termPairs.value]
      }
      
      return updatedTermPair
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to edit term pair'
      error.value = errorMessage
      throw err
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Delete a term pair by ID
   */
  async function deleteTermPair(termId: string): Promise<boolean> {
    isLoading.value = true
    error.value = null
    
    try {
      const termToDelete = termPairs.value.find((t: TermPair) => t.id === termId)
      
      const { data } = await apolloClient.mutate<DeleteTermPairMutationResult>({
        mutation: DELETE_TERM_PAIR_MUTATION,
        variables: { termId },
      })
      
      const deleted = data?.deleteTermPair ?? false
      
      if (deleted) {
        termPairs.value = termPairs.value.filter((t: TermPair) => t.id !== termId)
        totalItems.value = Math.max(0, totalItems.value - 1)
        
        // Update catalog term count
        if (termToDelete) {
          const catalogIndex = catalogs.value.findIndex(
            (c: Catalog) => c.id === termToDelete.catalogId
          )
          if (catalogIndex !== -1) {
            const existingCatalog = catalogs.value[catalogIndex]
            if (existingCatalog) {
              catalogs.value[catalogIndex] = {
                ...existingCatalog,
                termCount: Math.max(0, existingCatalog.termCount - 1),
              }
              catalogs.value = [...catalogs.value]
              persistCatalogs()
            }
          }
        }
      }
      
      return deleted
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete term pair'
      error.value = errorMessage
      throw err
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Delete all term pairs in a catalog
   */
  async function bulkDeleteTermPairs(
    languagePairId: string,
    catalogId: string
  ): Promise<number> {
    isLoading.value = true
    error.value = null
    
    try {
      const { data } = await apolloClient.mutate<BulkDeleteTermPairsMutationResult>({
        mutation: BULK_DELETE_TERM_PAIRS_MUTATION,
        variables: { languagePairId, catalogId },
      })
      
      const deletedCount = data?.bulkDeleteTermPairs ?? 0
      
      // Clear term pairs if the deleted catalog was selected
      if (selectedCatalogId.value === catalogId) {
        termPairs.value = []
        totalItems.value = 0
      }
      
      // Update catalog term count
      const catalogIndex = catalogs.value.findIndex((c: Catalog) => c.id === catalogId)
      if (catalogIndex !== -1) {
        const existingCatalog = catalogs.value[catalogIndex]
        if (existingCatalog) {
          catalogs.value[catalogIndex] = {
            ...existingCatalog,
            termCount: 0,
          }
          catalogs.value = [...catalogs.value]
          persistCatalogs()
        }
      }
      
      return deletedCount
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to bulk delete term pairs'
      error.value = errorMessage
      throw err
    } finally {
      isLoading.value = false
    }
  }

  // =========================================================================
  // Import/Export Actions
  // =========================================================================

  /**
   * Import term pairs from CSV content
   */
  async function importFromCsv(
    languagePairId: string,
    catalogId: string,
    csvContent: string
  ): Promise<ImportResult> {
    isLoading.value = true
    error.value = null
    
    try {
      const { data } = await apolloClient.mutate<ImportTermsCsvMutationResult>({
        mutation: IMPORT_TERMS_CSV_MUTATION,
        variables: { languagePairId, catalogId, csvContent },
      })
      
      if (!data?.importTermsCsv) {
        throw new Error('Failed to import CSV')
      }
      
      const result = data.importTermsCsv
      
      // Refresh term pairs and catalogs after import
      await fetchTermPairs(languagePairId, catalogId, searchText.value, currentPage.value, pageSize.value)
      await fetchCatalogs(languagePairId)
      
      return result
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to import CSV'
      error.value = errorMessage
      throw err
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Export term pairs as CSV content
   */
  async function exportToCsv(
    languagePairId: string,
    catalogId: string
  ): Promise<string> {
    isLoading.value = true
    error.value = null
    
    try {
      const { data } = await apolloClient.query<ExportTermsCsvQueryResult>({
        query: EXPORT_TERMS_CSV_QUERY,
        variables: { languagePairId, catalogId },
        fetchPolicy: 'network-only',
      })
      
      if (!data?.exportTermsCsv) {
        throw new Error('Failed to export CSV')
      }
      
      return data.exportTermsCsv
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to export CSV'
      error.value = errorMessage
      throw err
    } finally {
      isLoading.value = false
    }
  }

  // =========================================================================
  // Utility Actions
  // =========================================================================

  /**
   * Set selected language pair. Clears related data when the pair changes.
   */
  function setSelectedLanguagePair(languagePairId: string | null) {
    // Only clear data if the language pair is actually changing
    if (languagePairId !== selectedLanguagePairId.value) {
      catalogs.value = []
      termPairs.value = []
      selectedCatalogId.value = null
      totalItems.value = 0
    }
    selectedLanguagePairId.value = languagePairId
  }

  /**
   * Set selected catalog
   */
  function setSelectedCatalog(catalogId: string | null) {
    selectedCatalogId.value = catalogId
  }

  /**
   * Set search text
   */
  function setSearchText(text: string) {
    searchText.value = text
  }

  /**
   * Set current page
   */
  function setCurrentPage(page: number) {
    currentPage.value = page
  }

  /**
   * Clear error
   */
  function clearError() {
    error.value = null
  }

  /**
   * Reset store state
   */
  function reset() {
    termPairs.value = []
    catalogs.value = []
    selectedLanguagePairId.value = null
    selectedCatalogId.value = null
    searchText.value = ''
    currentPage.value = 1
    totalItems.value = 0
    hasNextPage.value = false
    error.value = null
    localStorage.removeItem(CATALOGS_STORAGE_KEY)
  }

  /**
   * Persist catalogs to localStorage
   */
  function persistCatalogs() {
    try {
      const catalogData = JSON.stringify(catalogs.value)
      localStorage.setItem(CATALOGS_STORAGE_KEY, catalogData)
    } catch (err) {
      console.error('Failed to persist catalogs:', err)
    }
  }

  /**
   * Load catalogs from localStorage
   */
  function loadCatalogs() {
    try {
      const catalogData = localStorage.getItem(CATALOGS_STORAGE_KEY)
      if (catalogData) {
        catalogs.value = JSON.parse(catalogData)
      }
    } catch (err) {
      console.error('Failed to load catalogs:', err)
      catalogs.value = []
    }
  }

  return {
    // State
    termPairs,
    catalogs,
    selectedLanguagePairId,
    selectedCatalogId,
    searchText,
    isLoading,
    error,
    currentPage,
    pageSize,
    totalItems,
    hasNextPage,

    // Computed
    hasCatalogs,
    hasTermPairs,
    selectedCatalog,
    totalPages,
    getCatalogById,

    // Catalog Actions
    fetchCatalogs,
    createCatalog,
    updateCatalog,
    deleteCatalog,

    // Term Pair Actions
    fetchTermPairs,
    addTermPair,
    editTermPair,
    deleteTermPair,
    bulkDeleteTermPairs,

    // Import/Export Actions
    importFromCsv,
    exportToCsv,

    // Utility Actions
    setSelectedLanguagePair,
    setSelectedCatalog,
    setSearchText,
    setCurrentPage,
    clearError,
    reset,
    loadCatalogs,
  }
})
