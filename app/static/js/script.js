/**
 * 医疗图像分析系统前端JavaScript
 * 处理图像上传、预览、处理与分析结果显示，以及Token管理
 */

// 全局配置变量
let API_BASE_URL = '';

// DOM元素 - 通用
const navItems = document.querySelectorAll('.nav-item');
const tabContents = document.querySelectorAll('.tab-content');
const mobileMenuBtn = document.getElementById('mobileMenuBtn');
const sidebar = document.querySelector('.sidebar');

// DOM元素 - 图像分析
const dropZone = document.getElementById('dropZone');
const uploadContent = document.getElementById('uploadContent');
const imagePreview = document.getElementById('imagePreview');
const previewImg = document.getElementById('previewImg');
const fileInput = document.getElementById('fileInput');
const tokenInput = document.getElementById('tokenInput');
const uploadButton = document.getElementById('uploadButton');
const removeImageBtn = document.getElementById('removeImage');
const resultSection = document.getElementById('resultSection');
const loader = document.getElementById('loader');
const resultContent = document.getElementById('resultContent');
const resultCategory = document.getElementById('resultCategory');
const resultBrand = document.getElementById('resultBrand');
const resultTime = document.getElementById('resultTime');
const resultValues = document.getElementById('resultValues');
const resultAnalysis = document.getElementById('resultAnalysis');
const confidenceBar = document.getElementById('confidenceBar');
const confidenceValue = document.getElementById('confidenceValue');
const rawData = document.getElementById('rawData');
const newAnalysisBtn = document.getElementById('newAnalysisBtn');

// DOM元素 - Token管理
const centerIdInput = document.getElementById('centerIdInput');
const customTokenInput = document.getElementById('customTokenInput');
const useTimesInput = document.getElementById('useTimesInput');
const createTokenBtn = document.getElementById('createTokenBtn');
const tokenResultSection = document.getElementById('tokenResultSection');
const tokenLoader = document.getElementById('tokenLoader');
const tokenResultContent = document.getElementById('tokenResultContent');
const tokenSuccess = document.getElementById('tokenSuccess');
const tokenError = document.getElementById('tokenError');
const tokenId = document.getElementById('tokenId');
const tokenValue = document.getElementById('tokenValue');
const tokenUseTimes = document.getElementById('tokenUseTimes');
const tokenErrorMessage = document.getElementById('tokenErrorMessage');
const copyTokenBtn = document.getElementById('copyTokenBtn');
const newTokenBtn = document.getElementById('newTokenBtn');

// 状态变量
let selectedFile = null;

/**
 * 获取API配置
 */
async function loadConfig() {
    try {
        // 首先尝试从当前域名获取配置
        const response = await fetch('/upload/config');
        if (response.ok) {
            const config = await response.json();
            API_BASE_URL = config.api_base_url;
            console.log('API配置加載成功:', API_BASE_URL);
        } else {
            // 如果获取失败，使用默认配置
            API_BASE_URL = window.location.origin;
            console.log('使用默認API配置:', API_BASE_URL);
        }
    } catch (error) {
        console.error('API配置加載失敗:', error);
        // 如果获取失败，使用当前域名作为默认值
        API_BASE_URL = window.location.origin;
        console.log('使用默認API配置:', API_BASE_URL);
    }
}

/**
 * 初始化应用
 */
async function initApp() {
    await loadConfig();
    initNavigation();
    initMobileMenu();
    initUploadArea();
    initTokenManagement();
}

/**
 * 初始化導航功能
 */
function initNavigation() {
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const targetTab = item.getAttribute('data-tab');
            switchTab(targetTab);
            // 在移動端點擊導航後關閉側邊欄
            if (window.innerWidth <= 768) {
                closeMobileMenu();
            }
        });
    });
}

/**
 * 初始化移動端菜單
 */
function initMobileMenu() {
    if (mobileMenuBtn) {
        mobileMenuBtn.addEventListener('click', toggleMobileMenu);
    }
    
    // 點擊側邊欄外部區域關閉菜單
    document.addEventListener('click', (e) => {
        if (window.innerWidth <= 768 && sidebar && !sidebar.contains(e.target) && !mobileMenuBtn.contains(e.target)) {
            closeMobileMenu();
        }
    });
}

/**
 * 切換移動端菜單
 */
function toggleMobileMenu() {
    if (sidebar) {
        sidebar.classList.toggle('mobile-open');
    }
}

/**
 * 關閉移動端菜單
 */
function closeMobileMenu() {
    if (sidebar) {
        sidebar.classList.remove('mobile-open');
    }
}

/**
 * 切換選項卡
 */
function switchTab(targetTab) {
    // 移除所有活動狀態
    navItems.forEach(item => item.classList.remove('active'));
    tabContents.forEach(content => content.classList.remove('active'));

    // 添加活動狀態到目標選項卡
    const targetNavItem = document.querySelector(`[data-tab="${targetTab}"]`);
    const targetContent = document.getElementById(`${targetTab}Tab`);
    
    if (targetNavItem) targetNavItem.classList.add('active');
    if (targetContent) targetContent.classList.add('active');

    // 重置相關狀態
    if (targetTab === 'analysis') {
        resetAnalysis();
    } else if (targetTab === 'token') {
        resetTokenForm();
    }
}

/**
 * 初始化Token管理功能
 */
function initTokenManagement() {
    console.log('初始化Token管理功能...');

    // 等待一小段时间确保DOM完全加载
    setTimeout(() => {
        // 重新获取DOM元素
        const createTokenBtn = document.getElementById('createTokenBtn');
        const centerIdInput = document.getElementById('centerIdInput');
        const customTokenInput = document.getElementById('customTokenInput');
        const useTimesInput = document.getElementById('useTimesInput');
        const copyTokenBtn = document.getElementById('copyTokenBtn');
        const newTokenBtn = document.getElementById('newTokenBtn');

        console.log('重新檢查DOM元素:');
        console.log('createTokenBtn:', createTokenBtn);
        console.log('centerIdInput:', centerIdInput);
        console.log('customTokenInput:', customTokenInput);
        console.log('useTimesInput:', useTimesInput);

        // 检查DOM元素是否存在
        if (!createTokenBtn) {
            console.error('createTokenBtn 元素未找到');
            return;
        }
        if (!centerIdInput) {
            console.error('centerIdInput 元素未找到');
            return;
        }

        console.log('所有Token管理DOM元素已找到');

        // 創建Token按鈕事件
        createTokenBtn.addEventListener('click', (e) => {
            console.log('創建Token按鈕被點擊');
            e.preventDefault();
            e.stopPropagation();
            createToken();
        });

        // 複製Token按鈕事件
        if (copyTokenBtn) {
            copyTokenBtn.addEventListener('click', copyToken);
        }

        // 新Token按鈕事件
        if (newTokenBtn) {
            newTokenBtn.addEventListener('click', resetTokenForm);
        }

        // 輸入驗證
        centerIdInput.addEventListener('input', () => {
            console.log('centerIdInput 輸入變化:', centerIdInput.value);
            validateTokenForm();
        });

        if (customTokenInput) {
            customTokenInput.addEventListener('input', () => {
                console.log('customTokenInput 輸入變化:', customTokenInput.value);
                validateTokenForm();
            });
        }

        if (useTimesInput) {
            useTimesInput.addEventListener('input', () => {
                console.log('useTimesInput 輸入變化:', useTimesInput.value);
                validateTokenForm();
            });
        }

        // 初始验证
        validateTokenForm();

        console.log('Token管理功能初始化完成');
    }, 100);
}

/**
 * 驗證Token表單
 */
function validateTokenForm() {
    // 动态获取DOM元素
    const centerIdInput = document.getElementById('centerIdInput');
    const createTokenBtn = document.getElementById('createTokenBtn');
    const customTokenInput = document.getElementById('customTokenInput');
    const useTimesInput = document.getElementById('useTimesInput');

    if (!centerIdInput || !createTokenBtn) {
        console.error('Token表單元素未找到');
        return;
    }

    const centerIdValid = centerIdInput.value.trim() !== '';
    const customTokenValid = !customTokenInput || customTokenInput.value === '' || /^[a-zA-Z0-9]+$/.test(customTokenInput.value);
    const useTimesValid = !useTimesInput || (useTimesInput.value >= 1 && useTimesInput.value <= 1000);

    createTokenBtn.disabled = !(centerIdValid && customTokenValid && useTimesValid);

    console.log('表單驗證:', { centerIdValid, customTokenValid, useTimesValid, disabled: createTokenBtn.disabled });

    // 顯示自定義Token驗證錯誤
    if (customTokenInput && customTokenInput.value && !customTokenValid) {
        customTokenInput.style.borderColor = 'var(--error-color)';
    } else if (customTokenInput) {
        customTokenInput.style.borderColor = '';
    }
}

/**
 * 創建Token
 */
async function createToken() {
    console.log('開始創建Token...');
    console.log('API_BASE_URL:', API_BASE_URL);

    // 动态获取DOM元素
    const centerIdInput = document.getElementById('centerIdInput');
    const customTokenInput = document.getElementById('customTokenInput');
    const useTimesInput = document.getElementById('useTimesInput');
    const tokenResultSection = document.getElementById('tokenResultSection');
    const tokenLoader = document.getElementById('tokenLoader');
    const tokenResultContent = document.getElementById('tokenResultContent');

    if (!centerIdInput || !centerIdInput.value.trim()) {
        showError('請輸入中心ID');
        return;
    }

    if (!API_BASE_URL) {
        showError('API配置未加載，請刷新頁面重試');
        return;
    }

    // 顯示載入狀態
    if (tokenResultSection) {
        tokenResultSection.style.display = 'block';
    }
    if (tokenLoader) {
        tokenLoader.style.display = 'flex';
    }
    if (tokenResultContent) {
        tokenResultContent.style.display = 'none';
    }

    // 滾動到結果區域
    if (tokenResultSection) {
        tokenResultSection.scrollIntoView({ behavior: 'smooth' });
    }

    // 準備請求數據
    const tokenData = {
        center_id: centerIdInput.value.trim(),
        use_times: useTimesInput ? (parseInt(useTimesInput.value) || 10) : 10
    };

    if (customTokenInput && customTokenInput.value.trim()) {
        tokenData.token = customTokenInput.value.trim();
    }

    console.log('請求數據:', tokenData);

    try {
        const url = `${API_BASE_URL}/upload/add_token`;
        console.log('請求URL:', url);

        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(tokenData)
        });

        console.log('響應狀態:', response.status);

        const data = await response.json();
        console.log('響應數據:', data);

        // 隱藏載入動畫
        if (tokenLoader) {
            tokenLoader.style.display = 'none';
        }
        if (tokenResultContent) {
            tokenResultContent.style.display = 'block';
        }

        // 直接顯示後端返回的完整響應
        displayTokenResponse(data);

    } catch (error) {
        console.error('創建Token錯誤:', error);
        if (tokenLoader) {
            tokenLoader.style.display = 'none';
        }
        if (tokenResultContent) {
            tokenResultContent.style.display = 'block';
        }
        displayTokenResponse({
            error: '網路錯誤，請稍後再試',
            message: error.message
        });
    }
}

/**
 * 顯示Token響應結果（直接顯示後端返回的JSON）
 */
function displayTokenResponse(data) {
    const tokenJsonResult = document.getElementById('tokenJsonResult');

    if (tokenJsonResult) {
        // 直接顯示後端返回的完整響應
        tokenJsonResult.textContent = JSON.stringify(data, null, 2);
    }
}

/**
 * 複製Token到剪貼板
 */
async function copyToken() {
    const tokenJsonResult = document.getElementById('tokenJsonResult');

    if (!tokenJsonResult) {
        console.error('Token結果元素未找到');
        return;
    }

    try {
        // 解析JSON並提取token值（適配後端響應格式）
        const resultData = JSON.parse(tokenJsonResult.textContent);
        let tokenValue = null;

        // 嘗試從不同的響應格式中提取token
        if (resultData.data?.token) {
            tokenValue = resultData.data.token;
        } else if (resultData.token) {
            tokenValue = resultData.token;
        }

        if (tokenValue) {
            await navigator.clipboard.writeText(tokenValue);
            showError('Token已複製到剪貼板');
        } else {
            // 如果沒有找到token，複製整個響應
            await navigator.clipboard.writeText(tokenJsonResult.textContent);
            showError('響應內容已複製到剪貼板');
        }

    } catch (error) {
        console.error('複製失敗:', error);
        showError('複製失敗，請手動複製');
    }
}

/**
 * 重置Token表單
 */
function resetTokenForm() {
    const centerIdInput = document.getElementById('centerIdInput');
    const customTokenInput = document.getElementById('customTokenInput');
    const useTimesInput = document.getElementById('useTimesInput');
    const tokenResultSection = document.getElementById('tokenResultSection');

    if (centerIdInput) centerIdInput.value = '';
    if (customTokenInput) customTokenInput.value = '';
    if (useTimesInput) useTimesInput.value = '10';
    if (tokenResultSection) tokenResultSection.style.display = 'none';

    validateTokenForm();
}

/**
 * 初始化上传区域事件监听
 */
function initUploadArea() {
    // 点击上传区域触发文件选择
    dropZone.addEventListener('click', () => {
        fileInput.click();
    });

    // 文件选择改变事件
    fileInput.addEventListener('change', handleFileSelect);

    // 拖放事件
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');

        if (e.dataTransfer.files.length) {
            handleFiles(e.dataTransfer.files);
        }
    });

    // 移除选中图像
    removeImageBtn.addEventListener('click', (e) => {
        e.stopPropagation(); // 阻止事件冒泡
        resetImageSelection();
    });

    // 令牌输入事件
    tokenInput.addEventListener('input', validateForm);

    // 上传按钮点击事件
    uploadButton.addEventListener('click', uploadImage);

    // 新分析按钮点击事件
    newAnalysisBtn.addEventListener('click', resetAnalysis);
}

/**
 * 处理文件选择事件
 */
function handleFileSelect(e) {
    if (e.target.files.length) {
        handleFiles(e.target.files);
    }
}

/**
 * 处理选择的文件
 * @param {FileList} files - 用户选择的文件列表
 */
function handleFiles(files) {
    const file = files[0];

    // 验证文件类型
    if (!file.type.match('image.*')) {
        displayFileError('请选择有效的图像文件（JPG、PNG等）');
        return;
    }

    // 验证文件大小（最大700KB）
    if (file.size > 1000 * 1024) {
        displayFileError('图像文件过大，请选择小于1000KB的文件');
        return;
    }

    selectedFile = file;
    displayImagePreview(file);
    validateForm();
}

/**
 * 显示文件验证错误
 * @param {string} message - 错误消息
 */
function displayFileError(message) {
    // 显示结果区域
    resultSection.style.display = 'block';
    loader.style.display = 'none';
    resultContent.style.display = 'block';

    // 滚动到结果区域
    resultSection.scrollIntoView({ behavior: 'smooth' });

    // 显示错误信息
    const errorData = {
        error: '文件验证失败',
        message: message,
        timestamp: new Date().toISOString()
    };
    displayResults(errorData);
}

/**
 * 显示图像预览
 * @param {File} file - 待预览的图像文件
 */
function displayImagePreview(file) {
    const reader = new FileReader();

    reader.onload = (e) => {
        previewImg.src = e.target.result;
        uploadContent.style.display = 'none';
        imagePreview.style.display = 'flex';

        // 显示文件信息
        const fileSize = (file.size / 1024).toFixed(1) + 'KB';
        console.log(`文件名: ${file.name}, 大小: ${fileSize}, 类型: ${file.type}`);
    };

    reader.readAsDataURL(file);
}

/**
 * 验证表单，确定上传按钮状态
 */
function validateForm() {
    const isTokenValid = tokenInput.value.trim() !== '';
    const isFileSelected = selectedFile !== null;

    uploadButton.disabled = !(isTokenValid && isFileSelected);
}

/**
 * 重置图像选择
 */
function resetImageSelection() {
    selectedFile = null;
    fileInput.value = '';
    uploadContent.style.display = 'block';
    imagePreview.style.display = 'none';
    validateForm();
}

/**
 * 上传并分析图像
 */
function uploadImage() {
    if (!selectedFile || !tokenInput.value.trim()) {
        return;
    }

    // 记录开始时间
    const startTime = Date.now();

    // 显示结果区域和加载动画
    resultSection.style.display = 'block';
    loader.style.display = 'flex';
    resultContent.style.display = 'none';
    
    // 启用分栏布局
    const dashboardGrid = document.querySelector('#analysisTab .dashboard-grid');
    if (dashboardGrid) {
        dashboardGrid.classList.add('split-layout');
    }
    
    // 隐藏耗时显示
    const executionTimeDiv = document.getElementById('executionTime');
    if (executionTimeDiv) {
        executionTimeDiv.style.display = 'none';
    }

    // 滚动到结果区域
    resultSection.scrollIntoView({ behavior: 'smooth' });

        // 准备表单数据（只包含文件）
    const formData = new FormData();
    formData.append('image', selectedFile);

    // 将token作为URL参数
    const token = encodeURIComponent(tokenInput.value.trim());
    const url = `${API_BASE_URL}/upload/image?token=${token}`;

    // 发送请求
    fetch(url, {
        method: 'POST',
        body: formData,
    })
    .then(response => {
        console.log('响应状态:', response.status);

        // 无论成功还是失败，都尝试解析JSON
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            return response.json();
        } else {
            // 如果不是JSON响应，创建错误对象
            return {
                error: `服务器返回非JSON响应 (${response.status})`,
                status: response.status
            };
        }
    })
    .then(data => {
        console.log('接收到响应数据:', data);

        // 计算耗时
        const endTime = Date.now();
        const executionTime = ((endTime - startTime) / 1000).toFixed(2);

        // 隐藏加载动画，显示结果内容
        loader.style.display = 'none';
        resultContent.style.display = 'block';

        // 显示耗时
        const executionTimeDiv = document.getElementById('executionTime');
        const timeValueSpan = document.getElementById('timeValue');
        if (executionTimeDiv && timeValueSpan) {
            timeValueSpan.textContent = executionTime;
            executionTimeDiv.style.display = 'flex';
        }

        // 直接显示完整的响应数据（成功或错误）
        displayResults(data);
    })
    .catch(error => {
        console.error('网络或解析错误:', error);

        // 计算耗时（即使出错也显示）
        const endTime = Date.now();
        const executionTime = ((endTime - startTime) / 1000).toFixed(2);

        // 隐藏加载动画，显示结果内容
        loader.style.display = 'none';
        resultContent.style.display = 'block';

        // 显示耗时
        const executionTimeDiv = document.getElementById('executionTime');
        const timeValueSpan = document.getElementById('timeValue');
        if (executionTimeDiv && timeValueSpan) {
            timeValueSpan.textContent = executionTime;
            executionTimeDiv.style.display = 'flex';
        }

        // 显示网络错误
        const errorData = {
            error: '网络错误或请求失败',
            message: error.message,
            timestamp: new Date().toISOString()
        };
        displayResults(errorData);
    });
}

/**
 * 显示分析结果
 * @param {Object} data - 分析结果数据
 */
function displayResults(data) {
    // 隐藏加载动画，显示结果内容
    loader.style.display = 'none';
    resultContent.style.display = 'block';

    try {
        // 获取JSON显示元素
        const jsonResult = document.getElementById('jsonResult');

        // 格式化显示JSON数据
        jsonResult.textContent = JSON.stringify(data, null, 2);

    } catch (error) {
        console.error('显示结果时出错:', error);
        showError('解析结果时出错');

        // 显示错误信息
        document.getElementById('jsonResult').textContent = JSON.stringify({
            error: error.message || '解析结果时出错'
        }, null, 2);
    }
}

/**
 * 显示错误消息
 * @param {string} message - 错误消息
 */
function showError(message) {
    alert(`错误: ${message}`);
}

/**
 * 重置分析，返回上传新图像
 */
function resetAnalysis() {
    resultSection.style.display = 'none';
    
    // 隐藏耗时显示
    const executionTimeDiv = document.getElementById('executionTime');
    if (executionTimeDiv) {
        executionTimeDiv.style.display = 'none';
    }
    
    // 移除分栏布局，恢复居中布局
    const dashboardGrid = document.querySelector('#analysisTab .dashboard-grid');
    if (dashboardGrid) {
        dashboardGrid.classList.remove('split-layout');
    }
    
    resetImageSelection();
    dropZone.scrollIntoView({ behavior: 'smooth' });
}

/**
 * 页面加载完成后初始化
 */
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM加載完成，開始初始化...');

    // 检查关键DOM元素
    console.log('檢查DOM元素:');
    console.log('createTokenBtn:', document.getElementById('createTokenBtn'));
    console.log('centerIdInput:', document.getElementById('centerIdInput'));
    console.log('customTokenInput:', document.getElementById('customTokenInput'));
    console.log('useTimesInput:', document.getElementById('useTimesInput'));

    initApp();

    // 预先填充一个令牌便于测试
    if (tokenInput) {
        tokenInput.value = '';
    }
});
