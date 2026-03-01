export default {
  // Application
  app: {
    title: '文档翻译'
  },

  // Navigation
  nav: {
    main: '主页',
    settings: '设置',
    thesaurus: '术语库',
    users: '用户管理',
    logout: '退出登录',
    logoutSuccess: '退出成功',
    seeYou: '下次再见！'
  },

  // Login Page
  login: {
    title: '登录',
    username: '用户名',
    password: '密码',
    submit: '登录',
    submitting: '登录中...',
    error: '用户名或密码错误',
    required: '请输入{field}',
    welcome: '欢迎回来',
    welcomeSubtitle: '请输入您的登录信息。',
    success: '登录成功',
    welcomeBack: '欢迎回来！'
  },

  // Main Page - File Upload
  fileUpload: {
    title: '文件上传',
    dragDrop: '拖拽文件到此处或点击上传',
    selectFiles: '选择文件',
    selectedFiles: '已选择的文件',
    noFiles: '未选择文件',
    fileCount: '{count} 个文件',
    fileName: '文件名',
    fileSize: '大小',
    remove: '移除',
    clear: '清除所有',
    uploadError: '上传失败',
    invalidFormat: '支持的格式：.xlsx, .docx, .pptx, .pdf, .txt, .md',
    uploading: '上传中...',
    supportedFormats: '支持的格式：Excel (.xlsx)、Word (.docx)、PowerPoint (.pptx)、PDF (.pdf)、文本 (.txt)、Markdown (.md)',
    uploadComplete: '上传完成',
    uploadSuccess: '成功上传 {count} 个文件{failed}',
    failed: '失败'
  },

  // Document Types
  documentType: {
    excel: 'Excel 表格',
    word: 'Word 文档',
    powerpoint: 'PowerPoint 演示文稿',
    pdf: 'PDF 文档',
    text: '文本',
    markdown: 'Markdown',
    unknown: '未知类型'
  },

  // Main Page - Language Pair
  languagePair: {
    title: '语言对',
    select: '选择语言对',
    source: '源语言',
    target: '目标语言',
    noLanguagePairs: '未配置语言对，请前往设置页面添加',
    required: '请选择语言对'
  },

  // Main Page - Translation
  translation: {
    title: '翻译仪表板',
    subtitle: '上传您的文档并立即翻译。',
    start: '开始翻译',
    starting: '启动中...',
    processing: '翻译中...',
    selectFiles: '请先选择文件',
    selectLanguagePair: '请先选择语言对',
    error: '翻译失败',
    success: '翻译完成',
    actionDescription: '准备好翻译了吗？点击下方按钮开始。',
    validationUpload: '请至少上传一个文档',
    validationLanguage: '请选择语言对'
  },

  // Job
  job: {
    history: '历史记录',
    noJobs: '暂无已完成的任务',
    files: '个文件',
    failedFiles: '失败的文件'
  },

  // Progress Tracker
  progress: {
    title: '翻译进度',
    overall: '总体进度',
    currentFile: '当前文件',
    filesCompleted: '个文件已完成',
    filesTotal: '总文件数',
    cellsTranslated: '已翻译单元格',
    cellsTotal: '总单元格数',
    segmentsTranslated: '已翻译段落',
    segmentsTotal: '总段落数',
    segments: '段落',
    status: {
      pending: '等待中',
      processing: '处理中',
      completed: '已完成',
      failed: '失败',
      partial: '部分成功'
    },
    errors: '错误',
    noErrors: '无错误',
    jobTitle: '翻译任务',
    loading: '正在加载任务状态...',
    noActiveJob: '没有进行中的翻译任务',
    started: '开始时间',
    completed: '完成时间'
  },

  // File Download
  download: {
    title: '下载文件',
    button: '下载',
    downloading: '下载中...',
    success: '下载成功',
    error: '下载失败',
    noFiles: '暂无可下载文件'
  },

  // Settings Page
  settings: {
    title: '设置',
    subtitle: '管理翻译模型和语言配置。',
    languagePairs: '语言对管理',
    addLanguagePair: '添加语言对',
    removeLanguagePair: '删除',
    sourceLanguage: '源语言',
    targetLanguage: '目标语言',
    sourceCode: '源语言代码',
    targetCode: '目标语言代码',
    save: '保存',
    saving: '保存中...',
    saved: '保存成功',
    cancel: '取消',
    reset: '重置',
    noLanguagePairs: '暂无配置的语言对',
    addSuccess: '添加成功',
    addError: '添加失败',
    removeSuccess: '删除成功',
    removeError: '删除失败',
    uiLanguage: '界面语言',
    chinese: '中文',
    vietnamese: 'Tiếng Việt',
    english: 'English',
    translationModel: '翻译模型',
    selectModel: '选择AI模型',
    currentModel: '当前使用的模型',
    configuredPairs: '已配置的语言对',
    confirmDelete: '确定要删除这个语言对吗？',
    appearance: '外观',
    // Validation messages
    validation: {
      sourceLanguageRequired: '请输入源语言',
      targetLanguageRequired: '请输入目标语言',
      sourceCodeRequired: '请输入源语言代码',
      targetCodeRequired: '请输入目标语言代码',
      languageNameMinLength: '语言名称至少2个字符',
      codeLength: '语言代码必须是2-5个字符',
      codeFormat: '语言代码只能是小写字母'
    },
    // Message keys
    loadLanguagePairsError: '加载语言对失败',
    languagePairExists: '此语言对已存在',
    languagePairAdded: '语言对添加成功',
    languagePairAddError: '添加语言对失败',
    languagePairRemoved: '语言对移除成功',
    languagePairRemoveError: '移除语言对失败',
    loadModelError: '加载模型配置失败',
    modelUpdated: '模型已更新为 {modelName}',
    updateModelError: '更新模型失败'
  },

  // Notifications
  notification: {
    success: '成功',
    error: '错误',
    warning: '警告',
    info: '信息'
  },

  // Validation
  validation: {
    required: '此字段为必填项',
    invalidFormat: '格式无效',
    tooLong: '输入内容过长',
    tooShort: '输入内容过短',
    duplicate: '该项已存在'
  },

  // Common
  common: {
    loading: '加载中...',
    confirm: '确认',
    cancel: '取消',
    close: '关闭',
    save: '保存',
    delete: '删除',
    edit: '编辑',
    add: '添加',
    search: '搜索',
    filter: '筛选',
    refresh: '刷新',
    back: '返回',
    next: '下一步',
    previous: '上一步',
    submit: '提交',
    reset: '重置',
    clear: '清除',
    yes: '是',
    no: '否',
    ok: '确定',
    to: '到',
    bytes: '字节',
    kb: 'KB',
    mb: 'MB',
    gb: 'GB',
    optional: '可选',
    actions: '操作',
    justNow: '刚刚',
    minutesAgo: '分钟前',
    hoursAgo: '小时前',
    daysAgo: '天前'
  },

  // Thesaurus
  thesaurus: {
    title: '术语库',
    subtitle: '管理翻译术语对，确保术语一致性。',
    languageAndCatalog: '语言和目录',
    catalog: '目录',
    selectCatalog: '选择目录',
    termPairs: '术语对',
    sourceTerm: '源术语',
    targetTerm: '目标术语',
    lastModified: '最后修改',
    addTerm: '添加术语',
    editTerm: '编辑术语',
    import: '导入 CSV',
    export: '导出 CSV',
    searchPlaceholder: '搜索源术语...',
    selectLanguagePairFirst: '请先选择语言对',
    selectCatalogFirst: '请选择或创建目录',
    confirmDelete: '删除此术语对？',
    termDeleted: '术语删除成功',
    termAdded: '术语添加成功',
    termUpdated: '术语更新成功',
    exportSuccess: '导出完成',
    manageCatalogs: '管理目录',
    createCatalog: '创建新目录',
    catalogName: '名称',
    catalogNamePlaceholder: '例如：IT术语',
    catalogDescription: '描述',
    catalogDescriptionPlaceholder: '可选描述',
    existingCatalogs: '现有目录',
    noCatalogs: '暂无目录',
    confirmDeleteCatalog: '删除此目录及其所有术语？',
    catalogCreated: '目录创建成功',
    catalogRenamed: '目录重命名成功',
    catalogDeleted: '目录已删除',
    terms: '个术语',
    sourceTermPlaceholder: '输入源术语',
    targetTermPlaceholder: '输入目标术语翻译',
    sourceTermReadonly: '编辑时无法更改源术语',
    emptyTermError: '术语不能为空或仅包含空格',
    termTooLong: '术语不能超过500个字符',
    importTerms: '从 CSV 导入术语',
    dragCsvHere: '点击或拖拽 CSV 文件到此区域',
    csvFormat: 'CSV 必须包含列：source_term, target_term',
    preview: '预览',
    rows: '行',
    parseWarnings: '部分行存在问题',
    importNow: '立即导入',
    importComplete: '导入完成',
    created: '已创建',
    updated: '已更新',
    skipped: '已跳过',
    viewErrors: '查看错误',
    emptyFile: '文件为空',
    insufficientColumns: '列数不足',
    emptyTerms: '源术语或目标术语为空',
    selectCatalogs: '选择术语目录',
    catalogSelectorHelp: '选择用于翻译的目录。拖动以调整优先级。',
    noCatalogsAvailable: '此语言对没有可用目录',
    availableCatalogs: '可用',
    selectedCatalogs: '已选择',
    dragToReorder: '（拖动调整优先级）',
    totalTermsSelected: '术语总数',
    termLimitWarning: '仅使用前200个术语',
    termCatalogs: '术语目录'
  },

  // Output Mode
  outputMode: {
    label: '输出模式',
    tooltip: '选择原文和译文在输出文档中的组合方式。',
    replace: '替换',
    replaceDescription: '用译文替换原文',
    append: '追加',
    appendDescription: '将译文追加到原文后面',
    interleaved: '交错',
    interleavedDescription: '原文和译文逐行交错排列'
  },

  // Error Messages
  error: {
    network: '网络错误',
    server: '服务器错误',
    unauthorized: '未授权，请重新登录',
    forbidden: '无权限访问',
    notFound: '未找到',
    timeout: '请求超时',
    unknown: '未知错误',
    // Document processing errors
    passwordProtected: '此文件受密码保护，请移除密码后重试',
    corrupted: '此文件已损坏或格式错误，无法读取',
    scannedPdf: '此 PDF 仅包含扫描图像，请先使用 OCR 软件转换',
    emptyDocument: '此文档不包含可翻译的文本',
    unsupportedFormat: '不支持的文件格式。支持的格式：.xlsx, .docx, .pptx, .pdf, .txt, .md',
    processingFailed: '文档处理失败：{reason}',
    // ErrorDisplay component
    retrying: '重试中...',
    retry: '重试',
    defaultTitle: '错误',
    unexpectedError: '发生意外错误'
  },

  // Not Found Page
  notFound: {
    title: '404',
    subtitle: '抱歉，您访问的页面不存在。',
    backHome: '返回首页',
    goBack: '返回上页'
  },

  // User Management
  userManagement: {
    title: '用户管理',
    subtitle: '管理系统用户账户',
    createUser: '创建用户',
    editUser: '编辑用户',
    deleteUser: '删除用户',
    confirmDelete: '确定要删除用户 "{username}" 吗？',
    username: '用户名',
    password: '密码',
    confirmPassword: '确认密码',
    role: '角色',
    status: '状态',
    createdAt: '创建时间',
    lastLoginAt: '最后登录',
    neverLoggedIn: '从未登录',
    currentUser: '当前用户',
    noUsers: '暂无用户',
    unlock: '解锁',
    usernamePlaceholder: '请输入用户名',
    passwordPlaceholder: '请输入密码',
    passwordEditPlaceholder: '留空表示不修改',
    confirmPasswordPlaceholder: '请再次输入密码',
    usernameLength: '用户名长度3-50字符',
    usernameFormat: '只允许字母、数字、下划线',
    passwordMinLength: '密码至少6个字符',
    cannotChangeOwnRole: '不能修改自己的角色',
    createSuccess: '用户创建成功',
    createError: '创建失败',
    updateSuccess: '用户更新成功',
    updateError: '更新失败',
    deleteSuccess: '用户删除成功',
    deleteError: '删除失败',
    unlockSuccess: '用户解锁成功',
    unlockError: '解锁失败',
    roles: {
      admin: '管理员',
      user: '普通用户'
    },
    statuses: {
      PENDING_PASSWORD: '待修改密码',
      ACTIVE: '活跃',
      LOCKED: '已锁定',
      DELETED: '已删除'
    },
    errors: {
      userAlreadyExists: '用户名已存在',
      cannotDeleteSelf: '不能删除自己',
      cannotChangeOwnRole: '不能修改自己的角色'
    }
  },

  // Change Password
  changePassword: {
    title: '修改密码',
    subtitle: '首次登录需要修改密码才能继续使用系统',
    currentPassword: '当前密码',
    newPassword: '新密码',
    confirmPassword: '确认新密码',
    currentPasswordPlaceholder: '请输入当前密码',
    newPasswordPlaceholder: '请输入新密码',
    confirmPasswordPlaceholder: '请再次输入新密码',
    submit: '确认修改',
    strength: {
      weak: '弱',
      medium: '中',
      strong: '强'
    },
    errors: {
      invalidCurrentPassword: '当前密码错误',
      passwordSameAsOld: '新密码不能与旧密码相同',
      passwordMismatch: '两次输入的密码不一致'
    },
    success: '密码修改成功'
  }

}