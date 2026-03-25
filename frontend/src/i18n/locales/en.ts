export default {
  // Application
  app: {
    title: 'Doc Translation'
  },

  // Navigation
  nav: {
    main: 'Home',
    settings: 'Settings',
    thesaurus: 'Thesaurus',
    users: 'User Management',
    logout: 'Logout',
    logoutSuccess: 'Logout successful',
    seeYou: 'See you next time!'
  },

  // Login Page
  login: {
    username: 'Username',
    password: 'Password',
    submit: 'Login',
    submitting: 'Logging in...',
    error: 'Invalid username or password',
    required: 'Please enter {field}',
    welcome: 'Welcome Back',
    welcomeSubtitle: 'Please enter your details to sign in.',
    success: 'Login successful',
    welcomeBack: 'Welcome back!'
  },

  // Main Page - File Upload
  fileUpload: {
    title: 'File Upload',
    dragDrop: 'Drag and drop files here or click to upload',
    selectedFiles: 'Selected Files',
    remove: 'Remove',
    invalidFormat: 'Supported formats: .xlsx, .docx, .pptx, .pdf, .txt, .md',
    uploading: 'Uploading...',
    uploadComplete: 'Upload Complete',
    uploadSuccess: 'Successfully uploaded {count} file(s){failed}',
    failed: 'failed'
  },

  // Main Page - Language Pair
  languagePair: {
    title: 'Language Pair',
    select: 'Select Language Pair'
  },

  // Main Page - Translation
  translation: {
    title: 'Translation Dashboard',
    subtitle: 'Upload your documents and translate them instantly.',
    start: 'Start Translation',
    actionDescription: 'Ready to translate? Click below to start the process.',
    validationUpload: 'Please upload at least one file',
    validationLanguage: 'Please select a language pair'
  },

  // Job
  job: {
    history: 'Translated Files',
    noJobs: 'No completed jobs yet',
    files: 'files',
    failedFiles: 'Failed Files',
    translationWarnings: 'Translation Warnings',
    totalJobs: 'Total {count} jobs',
    started: 'Translation Started',
    startedDesc: 'Your files are now being translated.',
    completed: 'Translation Complete',
    completedDesc: '{filesCompleted} files translated successfully.',
    completedWithWarnings: 'Translation Complete with Warnings',
    completedWithWarningsDesc: '{filesCompleted} files translated, but {failedSegments} segments failed in {warningFiles} file(s).',
    partialSuccess: 'Translation Partially Complete',
    partialSuccessDesc: '{filesCompleted} files succeeded, {filesFailed} failed.',
    failed: 'Translation Failed',
    failedDesc: 'Please check the error details.'
  },

  // Progress Tracker
  progress: {
    title: 'Translation Progress',
    overall: 'Overall Progress',
    currentFile: 'Current File',
    filesCompleted: 'files completed',
    segments: 'segments',
    errors: 'Errors',
    warnings: 'Warnings',
    jobTitle: 'Translation Job',
    loading: 'Loading job status...',
    noActiveJob: 'No active translation job',
    started: 'Started',
    completed: 'Completed'
  },

  // File Download
  download: {
    button: 'Download'
  },

  // Settings Page
  settings: {
    subtitle: 'Manage translation models and language configurations.',
    languagePairs: 'Language Pair Management',
    addLanguagePair: 'Add Language Pair',
    sourceLanguage: 'Source Language',
    targetLanguage: 'Target Language',
    sourceCode: 'Source Code',
    targetCode: 'Target Code',
    noLanguagePairs: 'No language pairs configured',
    uiLanguage: 'Interface Language',
    translationModel: 'Translation Model',
    selectModel: 'Select AI Model',
    currentModel: 'Current active model',
    configuredPairs: 'Configured Language Pairs',
    confirmDelete: 'Are you sure you want to delete this language pair?',
    appearance: 'Appearance',
    // Validation messages
    validation: {
      sourceLanguageRequired: 'Please enter source language',
      targetLanguageRequired: 'Please enter target language',
      sourceCodeRequired: 'Please enter source language code',
      targetCodeRequired: 'Please enter target language code',
      languageNameMinLength: 'Language name must be at least 2 characters',
      codeLength: 'Language code must be 2-5 characters',
      codeFormat: 'Language code must be lowercase letters only'
    },
    // Message keys
    loadLanguagePairsError: 'Failed to load language pairs',
    languagePairExists: 'This language pair already exists',
    languagePairAdded: 'Language pair added successfully',
    languagePairAddError: 'Failed to add language pair',
    languagePairRemoved: 'Language pair removed successfully',
    languagePairRemoveError: 'Failed to remove language pair',
    loadModelError: 'Failed to load model configuration',
    modelUpdated: 'Model updated to {modelName}',
    updateModelError: 'Failed to update model'
  },

  // Validation
  validation: {
    required: 'This field is required',
    tooLong: 'Input is too long',
    tooShort: 'Input is too short'
  },

  // Common
  common: {
    cancel: 'Cancel',
    save: 'Save',
    delete: 'Delete',
    edit: 'Edit',
    add: 'Add',
    yes: 'Yes',
    no: 'No',
    ok: 'OK',
    to: 'to',
    optional: 'Optional',
    actions: 'Actions'
  },

  // Thesaurus
  thesaurus: {
    title: 'Term Thesaurus',
    subtitle: 'Manage translation term pairs for consistent terminology.',
    languageAndCatalog: 'Language & Catalog',
    catalog: 'Catalog',
    selectCatalog: 'Select catalog',
    termPairs: 'Term Pairs',
    sourceTerm: 'Source Term',
    targetTerm: 'Target Term',
    lastModified: 'Last Modified',
    addTerm: 'Add Term',
    editTerm: 'Edit Term',
    import: 'Import CSV',
    export: 'Export CSV',
    searchPlaceholder: 'Search source terms...',
    selectLanguagePairFirst: 'Please select a language pair first',
    selectCatalogFirst: 'Please select or create a catalog',
    confirmDelete: 'Delete this term pair?',
    termDeleted: 'Term deleted successfully',
    termAdded: 'Term added successfully',
    termUpdated: 'Term updated successfully',
    exportSuccess: 'Export completed',
    catalogNamePlaceholder: 'e.g., IT Terms',
    catalogs: 'Catalogs',
    confirmDeleteCatalog: 'Delete this catalog and all its terms?',
    catalogCreated: 'Catalog created successfully',
    catalogRenamed: 'Catalog renamed successfully',
    catalogDeleted: 'Catalog deleted',
    catalogDeletedTerms: '{count} terms were also deleted',
    totalTerms: 'Total {total} terms',
    sourceTermPlaceholder: 'Enter source term',
    targetTermPlaceholder: 'Enter target term translation',
    sourceTermReadonly: 'Source term cannot be changed when editing',
    emptyTermError: 'Term cannot be empty or whitespace only',
    termTooLong: 'Term cannot exceed 500 characters',
    importTerms: 'Import Terms from CSV',
    dragCsvHere: 'Click or drag CSV file to this area',
    csvFormat: 'CSV must have columns: source_term, target_term',
    preview: 'Preview',
    rows: 'rows',
    parseWarnings: 'Some rows have issues',
    importNow: 'Import Now',
    importComplete: 'Import Complete',
    created: 'created',
    updated: 'updated',
    skipped: 'skipped',
    viewErrors: 'View Errors',
    emptyFile: 'File is empty',
    insufficientColumns: 'Insufficient columns',
    emptyTerms: 'Empty source or target term',
    catalogSelectorHelp: 'Select catalogs to use for translation. Drag to reorder priority.',
    noCatalogsAvailable: 'No catalogs available for this language pair',
    availableCatalogs: 'Available',
    selectedCatalogs: 'Selected',
    dragToReorder: '(drag to reorder priority)',
    totalTermsSelected: 'Total terms',
    termLimitWarning: 'Only first 200 terms will be used',
    termCatalogs: 'Term Catalogs'
  },

  // Output Mode
  outputMode: {
    label: 'Output Mode',
    tooltip: 'Choose how original and translated text are combined in the output document.',
    replace: 'Replace',
    append: 'Append',
    interleaved: 'Interleaved'
  },

  // Error Messages
  error: {
    unknown: 'Unknown error',
    // ErrorDisplay component
    retrying: 'Retrying...',
    retry: 'Retry',
    defaultTitle: 'Error',
    unexpectedError: 'An unexpected error occurred'
  },

  // Not Found Page
  notFound: {
    title: '404',
    subtitle: 'Sorry, the page you visited does not exist.',
    backHome: 'Back Home',
    goBack: 'Go Back'
  },

  // User Management
  userManagement: {
    title: 'User Management',
    subtitle: 'Manage system user accounts',
    createUser: 'Create User',
    editUser: 'Edit User',
    deleteUser: 'Delete User',
    confirmDelete: 'Are you sure you want to delete user "{username}"?',
    username: 'Username',
    password: 'Password',
    confirmPassword: 'Confirm Password',
    role: 'Role',
    status: 'Status',
    createdAt: 'Created',
    currentUser: 'Current User',
    noUsers: 'No users yet',
    unlock: 'Unlock',
    usernamePlaceholder: 'Enter username',
    passwordPlaceholder: 'Enter password',
    passwordEditPlaceholder: 'Leave empty to keep unchanged',
    confirmPasswordPlaceholder: 'Re-enter password',
    usernameLength: 'Username must be 3-50 characters',
    usernameFormat: 'Only letters, numbers, and underscores allowed',
    passwordMinLength: 'Password must be at least 6 characters',
    cannotChangeOwnRole: 'Cannot change your own role',
    createSuccess: 'User created successfully',
    createError: 'Failed to create user',
    updateSuccess: 'User updated successfully',
    updateError: 'Failed to update user',
    deleteSuccess: 'User deleted successfully',
    deleteError: 'Failed to delete user',
    unlockSuccess: 'User unlocked successfully',
    unlockError: 'Failed to unlock user',
    roles: {
      admin: 'Administrator',
      user: 'Regular User'
    },
    statuses: {
      PENDING_PASSWORD: 'Pending Password Change',
      ACTIVE: 'Active',
      LOCKED: 'Locked',
      DELETED: 'Deleted'
    },
    errors: {
      userAlreadyExists: 'Username already exists'
    }
  },

  // Change Password
  changePassword: {
    title: 'Change Password',
    subtitle: 'You must change your password on first login to continue using the system',
    currentPassword: 'Current Password',
    newPassword: 'New Password',
    confirmPassword: 'Confirm New Password',
    currentPasswordPlaceholder: 'Enter current password',
    newPasswordPlaceholder: 'Enter new password',
    confirmPasswordPlaceholder: 'Re-enter new password',
    submit: 'Confirm Change',
    strength: {
      weak: 'Weak',
      medium: 'Medium',
      strong: 'Strong'
    },
    errors: {
      invalidCurrentPassword: 'Current password is incorrect',
      passwordSameAsOld: 'New password cannot be the same as old password',
      passwordMismatch: 'Passwords do not match'
    },
    success: 'Password changed successfully'
  }
}
