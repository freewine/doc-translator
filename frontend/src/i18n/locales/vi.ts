export default {
  // Application
  app: {
    title: 'Dịch thuật tài liệu'
  },

  // Navigation
  nav: {
    main: 'Trang chính',
    settings: 'Cài đặt',
    thesaurus: 'Từ điển thuật ngữ',
    users: 'Quản lý người dùng',
    logout: 'Đăng xuất',
    logoutSuccess: 'Đăng xuất thành công',
    seeYou: 'Hẹn gặp lại!'
  },

  // Login Page
  login: {
    username: 'Tên người dùng',
    password: 'Mật khẩu',
    submit: 'Đăng nhập',
    submitting: 'Đang đăng nhập...',
    error: 'Tên người dùng hoặc mật khẩu không đúng',
    required: 'Vui lòng nhập {field}',
    welcome: 'Chào mừng trở lại',
    welcomeSubtitle: 'Vui lòng nhập thông tin đăng nhập của bạn.',
    success: 'Đăng nhập thành công',
    welcomeBack: 'Chào mừng trở lại!'
  },

  // Main Page - File Upload
  fileUpload: {
    title: 'Tải tệp lên',
    dragDrop: 'Kéo thả tệp vào đây hoặc nhấp để tải lên',
    selectedFiles: 'Tệp đã chọn',
    remove: 'Xóa',
    invalidFormat: 'Các định dạng hỗ trợ: .xlsx, .docx, .pptx, .pdf, .txt, .md',
    uploading: 'Đang tải lên...',
    uploadComplete: 'Tải lên hoàn tất',
    uploadSuccess: 'Đã tải lên thành công {count} tệp{failed}',
    failed: 'thất bại'
  },

  // Main Page - Language Pair
  languagePair: {
    title: 'Cặp ngôn ngữ',
    select: 'Chọn cặp ngôn ngữ'
  },

  // Main Page - Translation
  translation: {
    title: 'Bảng điều khiển dịch',
    subtitle: 'Tải lên tài liệu và dịch ngay lập tức.',
    start: 'Bắt đầu dịch',
    actionDescription: 'Sẵn sàng dịch? Nhấp vào nút bên dưới để bắt đầu.',
    validationUpload: 'Vui lòng tải lên ít nhất một tài liệu',
    validationLanguage: 'Vui lòng chọn cặp ngôn ngữ'
  },

  // Job
  job: {
    history: 'Tệp đã dịch',
    noJobs: 'Chưa có công việc hoàn thành',
    files: 'tệp',
    failedFiles: 'Tệp thất bại',
    translationWarnings: 'Cảnh báo dịch thuật',
    totalJobs: 'Tổng cộng {count} công việc',
    started: 'Đã bắt đầu dịch',
    startedDesc: 'Các tệp của bạn đang được dịch.',
    completed: 'Dịch hoàn tất',
    completedDesc: 'Đã dịch thành công {filesCompleted} tệp.',
    completedWithWarnings: 'Dịch hoàn tất với cảnh báo',
    completedWithWarningsDesc: 'Đã dịch {filesCompleted} tệp, nhưng {failedSegments} đoạn dịch thất bại trong {warningFiles} tệp.',
    partialSuccess: 'Dịch hoàn tất một phần',
    partialSuccessDesc: '{filesCompleted} tệp thành công, {filesFailed} tệp thất bại.',
    failed: 'Dịch thất bại',
    failedDesc: 'Vui lòng kiểm tra chi tiết lỗi.'
  },

  // Progress Tracker
  progress: {
    title: 'Tiến độ dịch',
    overall: 'Tiến độ tổng thể',
    currentFile: 'Tệp hiện tại',
    filesCompleted: 'tệp đã hoàn thành',
    segments: 'đoạn',
    errors: 'Lỗi',
    warnings: 'Cảnh báo',
    jobTitle: 'Công việc dịch',
    loading: 'Đang tải trạng thái công việc...',
    noActiveJob: 'Không có công việc dịch đang hoạt động',
    started: 'Bắt đầu',
    completed: 'Hoàn thành'
  },

  // File Download
  download: {
    button: 'Tải xuống'
  },

  // Settings Page
  settings: {
    subtitle: 'Quản lý mô hình dịch và cấu hình ngôn ngữ.',
    languagePairs: 'Quản lý cặp ngôn ngữ',
    addLanguagePair: 'Thêm cặp ngôn ngữ',
    sourceLanguage: 'Ngôn ngữ nguồn',
    targetLanguage: 'Ngôn ngữ đích',
    sourceCode: 'Mã ngôn ngữ nguồn',
    targetCode: 'Mã ngôn ngữ đích',
    noLanguagePairs: 'Chưa có cặp ngôn ngữ được cấu hình',
    uiLanguage: 'Ngôn ngữ giao diện',
    translationModel: 'Mô hình dịch',
    selectModel: 'Chọn mô hình AI',
    currentModel: 'Mô hình đang sử dụng',
    configuredPairs: 'Cặp ngôn ngữ đã cấu hình',
    confirmDelete: 'Bạn có chắc muốn xóa cặp ngôn ngữ này?',
    appearance: 'Giao diện',
    // Validation messages
    validation: {
      sourceLanguageRequired: 'Vui lòng nhập ngôn ngữ nguồn',
      targetLanguageRequired: 'Vui lòng nhập ngôn ngữ đích',
      sourceCodeRequired: 'Vui lòng nhập mã ngôn ngữ nguồn',
      targetCodeRequired: 'Vui lòng nhập mã ngôn ngữ đích',
      languageNameMinLength: 'Tên ngôn ngữ phải có ít nhất 2 ký tự',
      codeLength: 'Mã ngôn ngữ phải từ 2-5 ký tự',
      codeFormat: 'Mã ngôn ngữ chỉ được dùng chữ cái thường'
    },
    // Message keys
    loadLanguagePairsError: 'Tải cặp ngôn ngữ thất bại',
    languagePairExists: 'Cặp ngôn ngữ này đã tồn tại',
    languagePairAdded: 'Đã thêm cặp ngôn ngữ thành công',
    languagePairAddError: 'Thêm cặp ngôn ngữ thất bại',
    languagePairRemoved: 'Đã xóa cặp ngôn ngữ thành công',
    languagePairRemoveError: 'Xóa cặp ngôn ngữ thất bại',
    loadModelError: 'Tải cấu hình mô hình thất bại',
    modelUpdated: 'Đã cập nhật mô hình thành {modelName}',
    updateModelError: 'Cập nhật mô hình thất bại'
  },

  // Validation
  validation: {
    required: 'Trường này là bắt buộc',
    tooLong: 'Nội dung nhập quá dài',
    tooShort: 'Nội dung nhập quá ngắn'
  },

  // Common
  common: {
    cancel: 'Hủy',
    save: 'Lưu',
    delete: 'Xóa',
    edit: 'Chỉnh sửa',
    add: 'Thêm',
    yes: 'Có',
    no: 'Không',
    ok: 'OK',
    to: 'đến',
    optional: 'Tùy chọn',
    actions: 'Hành động'
  },

  // Thesaurus
  thesaurus: {
    title: 'Từ điển thuật ngữ',
    subtitle: 'Quản lý cặp thuật ngữ dịch để đảm bảo tính nhất quán.',
    languageAndCatalog: 'Ngôn ngữ & Danh mục',
    catalog: 'Danh mục',
    selectCatalog: 'Chọn danh mục',
    termPairs: 'Cặp thuật ngữ',
    sourceTerm: 'Thuật ngữ nguồn',
    targetTerm: 'Thuật ngữ đích',
    lastModified: 'Sửa đổi lần cuối',
    addTerm: 'Thêm thuật ngữ',
    editTerm: 'Sửa thuật ngữ',
    import: 'Nhập CSV',
    export: 'Xuất CSV',
    searchPlaceholder: 'Tìm kiếm thuật ngữ nguồn...',
    selectLanguagePairFirst: 'Vui lòng chọn cặp ngôn ngữ trước',
    selectCatalogFirst: 'Vui lòng chọn hoặc tạo danh mục',
    confirmDelete: 'Xóa cặp thuật ngữ này?',
    termDeleted: 'Đã xóa thuật ngữ thành công',
    termAdded: 'Đã thêm thuật ngữ thành công',
    termUpdated: 'Đã cập nhật thuật ngữ thành công',
    exportSuccess: 'Xuất hoàn tất',
    catalogNamePlaceholder: 'Ví dụ: Thuật ngữ CNTT',
    catalogs: 'Danh mục',
    confirmDeleteCatalog: 'Xóa danh mục này và tất cả thuật ngữ?',
    catalogCreated: 'Đã tạo danh mục thành công',
    catalogRenamed: 'Đã đổi tên danh mục thành công',
    catalogDeleted: 'Đã xóa danh mục',
    catalogDeletedTerms: '{count} thuật ngữ cũng đã bị xóa',
    totalTerms: 'Tổng cộng {total} thuật ngữ',
    sourceTermPlaceholder: 'Nhập thuật ngữ nguồn',
    targetTermPlaceholder: 'Nhập bản dịch thuật ngữ đích',
    sourceTermReadonly: 'Không thể thay đổi thuật ngữ nguồn khi chỉnh sửa',
    emptyTermError: 'Thuật ngữ không được để trống hoặc chỉ có khoảng trắng',
    termTooLong: 'Thuật ngữ không được vượt quá 500 ký tự',
    importTerms: 'Nhập thuật ngữ từ CSV',
    dragCsvHere: 'Nhấp hoặc kéo tệp CSV vào khu vực này',
    csvFormat: 'CSV phải có các cột: source_term, target_term',
    preview: 'Xem trước',
    rows: 'hàng',
    parseWarnings: 'Một số hàng có vấn đề',
    importNow: 'Nhập ngay',
    importComplete: 'Nhập hoàn tất',
    created: 'đã tạo',
    updated: 'đã cập nhật',
    skipped: 'đã bỏ qua',
    viewErrors: 'Xem lỗi',
    emptyFile: 'Tệp trống',
    insufficientColumns: 'Không đủ cột',
    emptyTerms: 'Thuật ngữ nguồn hoặc đích trống',
    catalogSelectorHelp: 'Chọn danh mục để sử dụng cho dịch. Kéo để sắp xếp ưu tiên.',
    noCatalogsAvailable: 'Không có danh mục cho cặp ngôn ngữ này',
    availableCatalogs: 'Có sẵn',
    selectedCatalogs: 'Đã chọn',
    dragToReorder: '(kéo để sắp xếp ưu tiên)',
    totalTermsSelected: 'Tổng thuật ngữ',
    termLimitWarning: 'Chỉ sử dụng 200 thuật ngữ đầu tiên',
    termCatalogs: 'Danh mục thuật ngữ'
  },

  // Output Mode
  outputMode: {
    label: 'Chế độ xuất',
    tooltip: 'Chọn cách kết hợp văn bản gốc và bản dịch trong tài liệu xuất.',
    replace: 'Thay thế',
    append: 'Nối thêm',
    interleaved: 'Xen kẽ'
  },

  // Error Messages
  error: {
    unknown: 'Lỗi không xác định',
    // ErrorDisplay component
    retrying: 'Đang thử lại...',
    retry: 'Thử lại',
    defaultTitle: 'Lỗi',
    unexpectedError: 'Đã xảy ra lỗi không mong muốn'
  },

  // Not Found Page
  notFound: {
    title: '404',
    subtitle: 'Xin lỗi, trang bạn truy cập không tồn tại.',
    backHome: 'Về trang chủ',
    goBack: 'Quay lại'
  },

  // User Management
  userManagement: {
    title: 'Quản lý người dùng',
    subtitle: 'Quản lý tài khoản người dùng hệ thống',
    createUser: 'Tạo người dùng',
    editUser: 'Chỉnh sửa người dùng',
    deleteUser: 'Xóa người dùng',
    confirmDelete: 'Bạn có chắc muốn xóa người dùng "{username}"?',
    username: 'Tên người dùng',
    password: 'Mật khẩu',
    confirmPassword: 'Xác nhận mật khẩu',
    role: 'Vai trò',
    status: 'Trạng thái',
    createdAt: 'Ngày tạo',
    currentUser: 'Người dùng hiện tại',
    noUsers: 'Chưa có người dùng',
    unlock: 'Mở khóa',
    usernamePlaceholder: 'Nhập tên người dùng',
    passwordPlaceholder: 'Nhập mật khẩu',
    passwordEditPlaceholder: 'Để trống nếu không thay đổi',
    confirmPasswordPlaceholder: 'Nhập lại mật khẩu',
    usernameLength: 'Tên người dùng từ 3-50 ký tự',
    usernameFormat: 'Chỉ cho phép chữ cái, số, gạch dưới',
    passwordMinLength: 'Mật khẩu ít nhất 6 ký tự',
    cannotChangeOwnRole: 'Không thể thay đổi vai trò của chính mình',
    createSuccess: 'Tạo người dùng thành công',
    createError: 'Tạo thất bại',
    updateSuccess: 'Cập nhật người dùng thành công',
    updateError: 'Cập nhật thất bại',
    deleteSuccess: 'Xóa người dùng thành công',
    deleteError: 'Xóa thất bại',
    unlockSuccess: 'Mở khóa người dùng thành công',
    unlockError: 'Mở khóa thất bại',
    roles: {
      admin: 'Quản trị viên',
      user: 'Người dùng thường'
    },
    statuses: {
      PENDING_PASSWORD: 'Chờ đổi mật khẩu',
      ACTIVE: 'Hoạt động',
      LOCKED: 'Đã khóa',
      DELETED: 'Đã xóa'
    },
    errors: {
      userAlreadyExists: 'Tên người dùng đã tồn tại'
    }
  },

  // Change Password
  changePassword: {
    title: 'Đổi mật khẩu',
    subtitle: 'Đăng nhập lần đầu cần đổi mật khẩu để tiếp tục sử dụng hệ thống',
    currentPassword: 'Mật khẩu hiện tại',
    newPassword: 'Mật khẩu mới',
    confirmPassword: 'Xác nhận mật khẩu mới',
    currentPasswordPlaceholder: 'Nhập mật khẩu hiện tại',
    newPasswordPlaceholder: 'Nhập mật khẩu mới',
    confirmPasswordPlaceholder: 'Nhập lại mật khẩu mới',
    submit: 'Xác nhận đổi',
    strength: {
      weak: 'Yếu',
      medium: 'Trung bình',
      strong: 'Mạnh'
    },
    errors: {
      invalidCurrentPassword: 'Mật khẩu hiện tại không đúng',
      passwordSameAsOld: 'Mật khẩu mới không được giống mật khẩu cũ',
      passwordMismatch: 'Hai mật khẩu không khớp'
    },
    success: 'Đổi mật khẩu thành công'
  }
}
