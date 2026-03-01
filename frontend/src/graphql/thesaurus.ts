import { gql } from '@apollo/client/core'

// =========================================================================
// Thesaurus Queries (Requirements 3.1, 3.2, 3.4, 9.1)
// =========================================================================

/**
 * Query paginated term pairs with optional filtering
 */
export const TERM_PAIRS_QUERY = gql`
  query TermPairs(
    $languagePairId: String!
    $catalogId: String
    $search: String
    $page: Int
    $pageSize: Int
  ) {
    termPairs(
      languagePairId: $languagePairId
      catalogId: $catalogId
      search: $search
      page: $page
      pageSize: $pageSize
    ) {
      items {
        id
        languagePairId
        catalogId
        sourceTerm
        targetTerm
        createdAt
        updatedAt
      }
      total
      page
      pageSize
      hasNext
    }
  }
`

/**
 * Query all catalogs for a language pair with term counts
 */
export const CATALOGS_QUERY = gql`
  query Catalogs($languagePairId: String!) {
    catalogs(languagePairId: $languagePairId) {
      id
      languagePairId
      name
      description
      termCount
      createdAt
      updatedAt
    }
  }
`

/**
 * Export term pairs as CSV content
 */
export const EXPORT_TERMS_CSV_QUERY = gql`
  query ExportTermsCsv($languagePairId: String!, $catalogId: String!) {
    exportTermsCsv(languagePairId: $languagePairId, catalogId: $catalogId)
  }
`

// =========================================================================
// Thesaurus Mutations (Requirements 1.1, 1.3, 1.5, 2.1, 4.1, 4.2, 5.1-5.4)
// =========================================================================

/**
 * Add or update a term pair (upsert behavior)
 */
export const ADD_TERM_PAIR_MUTATION = gql`
  mutation AddTermPair(
    $languagePairId: String!
    $catalogId: String!
    $sourceTerm: String!
    $targetTerm: String!
  ) {
    addTermPair(
      languagePairId: $languagePairId
      catalogId: $catalogId
      sourceTerm: $sourceTerm
      targetTerm: $targetTerm
    ) {
      id
      languagePairId
      catalogId
      sourceTerm
      targetTerm
      createdAt
      updatedAt
    }
  }
`

/**
 * Edit an existing term pair's target term
 */
export const EDIT_TERM_PAIR_MUTATION = gql`
  mutation EditTermPair($termId: String!, $targetTerm: String!) {
    editTermPair(termId: $termId, targetTerm: $targetTerm) {
      id
      languagePairId
      catalogId
      sourceTerm
      targetTerm
      createdAt
      updatedAt
    }
  }
`

/**
 * Delete a term pair by ID
 */
export const DELETE_TERM_PAIR_MUTATION = gql`
  mutation DeleteTermPair($termId: String!) {
    deleteTermPair(termId: $termId)
  }
`

/**
 * Delete all term pairs in a catalog
 */
export const BULK_DELETE_TERM_PAIRS_MUTATION = gql`
  mutation BulkDeleteTermPairs($languagePairId: String!, $catalogId: String!) {
    bulkDeleteTermPairs(languagePairId: $languagePairId, catalogId: $catalogId)
  }
`

/**
 * Import term pairs from CSV content
 */
export const IMPORT_TERMS_CSV_MUTATION = gql`
  mutation ImportTermsCsv(
    $languagePairId: String!
    $catalogId: String!
    $csvContent: String!
  ) {
    importTermsCsv(
      languagePairId: $languagePairId
      catalogId: $catalogId
      csvContent: $csvContent
    ) {
      created
      updated
      skipped
      errors
    }
  }
`

/**
 * Create a new catalog
 */
export const CREATE_CATALOG_MUTATION = gql`
  mutation CreateCatalog(
    $languagePairId: String!
    $name: String!
    $description: String
  ) {
    createCatalog(
      languagePairId: $languagePairId
      name: $name
      description: $description
    ) {
      id
      languagePairId
      name
      description
      termCount
      createdAt
      updatedAt
    }
  }
`

/**
 * Update a catalog's name or description
 */
export const UPDATE_CATALOG_MUTATION = gql`
  mutation UpdateCatalog(
    $languagePairId: String!
    $catalogId: String!
    $name: String
    $description: String
  ) {
    updateCatalog(
      languagePairId: $languagePairId
      catalogId: $catalogId
      name: $name
      description: $description
    ) {
      id
      languagePairId
      name
      description
      termCount
      createdAt
      updatedAt
    }
  }
`

/**
 * Delete a catalog and all its term pairs
 */
export const DELETE_CATALOG_MUTATION = gql`
  mutation DeleteCatalog($languagePairId: String!, $catalogId: String!) {
    deleteCatalog(languagePairId: $languagePairId, catalogId: $catalogId)
  }
`
