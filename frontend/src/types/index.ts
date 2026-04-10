// GraphQL Types

// User Role Enum
export const UserRole = {
  ADMIN: 'admin',
  USER: 'user',
} as const

export type UserRole = typeof UserRole[keyof typeof UserRole]

// User Status Enum
export const UserStatus = {
  PENDING_PASSWORD: 'PENDING_PASSWORD',
  ACTIVE: 'ACTIVE',
  LOCKED: 'LOCKED',
  DELETED: 'DELETED',
} as const

export type UserStatus = typeof UserStatus[keyof typeof UserStatus]

// Password Strength Enum
export const PasswordStrength = {
  WEAK: 'weak',
  MEDIUM: 'medium',
  STRONG: 'strong',
} as const

export type PasswordStrength = typeof PasswordStrength[keyof typeof PasswordStrength]

export interface User {
  username: string
  role?: UserRole
  status?: UserStatus
  mustChangePassword?: boolean
  failedLoginCount?: number
  createdAt?: string
  updatedAt?: string
  deletedAt?: string
}

// User Form Data
export interface UserFormData {
  username: string
  password?: string
  confirmPassword?: string
  role: UserRole
}

// Change Password Data
export interface ChangePasswordData {
  currentPassword: string
  newPassword: string
  confirmPassword: string
}

// Create User Input
export interface CreateUserInput {
  username: string
  password: string
  role: UserRole
}

// Update User Input
export interface UpdateUserInput {
  password?: string
  role?: UserRole
}

// Change Password Input
export interface ChangePasswordInput {
  currentPassword: string
  newPassword: string
}

export interface AuthPayload {
  token: string
  user: User
}

export interface LanguagePair {
  id: string
  sourceLanguage: string
  targetLanguage: string
  sourceLanguageCode: string
  targetLanguageCode: string
}

export interface ModelInfo {
  name: string
  id: string
}

export interface ModelConfig {
  modelId: string
  modelName: string
  availableModels: ModelInfo[]
}

export const JobStatus = {
  PENDING: 'PENDING',
  PROCESSING: 'PROCESSING',
  COMPLETED: 'COMPLETED',
  FAILED: 'FAILED',
  PARTIAL_SUCCESS: 'PARTIAL_SUCCESS',
} as const

export type JobStatus = typeof JobStatus[keyof typeof JobStatus]

export const DocumentType = {
  EXCEL: 'excel',
  WORD: 'word',
  POWERPOINT: 'powerpoint',
  PDF: 'pdf',
  TEXT: 'text',
  MARKDOWN: 'markdown',
} as const

export type DocumentType = typeof DocumentType[keyof typeof DocumentType]

export interface FileProgress {
  filename: string
  progress: number
  cellsTotal: number
  cellsTranslated: number
  segmentsTotal: number
  segmentsTranslated: number
  documentType?: DocumentType
}

export interface FileError {
  filename: string
  error: string
  errorType?: string
}

export interface CompletedFile {
  originalFilename: string
  outputFilename: string
  cellsTranslated: number
  segmentsFailed?: number
  translationWarning?: string
}

export interface TranslationJob {
  id: string
  status: JobStatus
  progress: number
  filesTotal: number
  filesCompleted: number
  filesProcessing: FileProgress[]
  filesFailed: FileError[]
  completedFiles: CompletedFile[]
  languagePair?: { sourceLanguage: string; targetLanguage: string }
  outputMode?: OutputMode
  createdAt: string
  completedAt?: string
}

// Output mode type for UI - determines how original and translated text are combined
export type OutputMode = 'replace' | 'append' | 'prepend' | 'interleave' | 'interleave_reverse'

export interface FileUpload {
  id: string
  filename: string
  size: number
  documentType?: DocumentType
}

// Thesaurus Types (Requirements 3.3)

export interface TermPair {
  id: string
  languagePairId: string
  catalogId: string
  sourceTerm: string
  targetTerm: string
  createdAt: string
  updatedAt: string
}

export interface Catalog {
  id: string
  languagePairId: string
  name: string
  description?: string | null
  termCount: number
  createdAt: string
  updatedAt: string
}

export interface ImportResult {
  created: number
  updated: number
  skipped: number
  errors: string[]
}

export interface PaginatedTermPairs {
  items: TermPair[]
  total: number
  page: number
  pageSize: number
  hasNext: boolean
}

// API Response Types

export interface ApiError {
  message: string
  extensions?: Record<string, any>
}

export interface GraphQLResponse<T> {
  data?: T
  errors?: ApiError[]
}

// Environment Variables

export interface EnvConfig {
  apiUrl: string
  pollIntervalMs: number
}
