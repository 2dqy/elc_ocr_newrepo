/**
 * 医疗图像分析系统前端JavaScript
 * 处理图像上传、预览、处理与分析结果显示
 */

const API_BASE_URL = 'http://localhost:8000';

// DOM元素
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

// 状态变量
let selectedFile = null;

// API配置

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
        showError('请选择有效的图像文件（JPG、PNG等）');
        return;
    }

    // 验证文件大小（最大500KB）
    if (file.size > 500 * 1024) {
        showError('图像文件过大，请选择小于500KB的文件');
        return;
    }

    selectedFile = file;
    displayImagePreview(file);
    validateForm();
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

    // 显示结果区域和加载动画
    resultSection.style.display = 'block';
    loader.style.display = 'flex';
    resultContent.style.display = 'none';

    // 滚动到结果区域
    resultSection.scrollIntoView({ behavior: 'smooth' });

    // 准备表单数据
    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('token', tokenInput.value.trim());

    // 修改请求URL
    fetch(`${API_BASE_URL}/upload/image`, {
        method: 'POST',
        body: formData,
    })
    .then(response => {
        // 检查Content-Type
        const contentType = response.headers.get('content-type');
        if (!response.ok) {
            if (contentType && contentType.includes('application/json')) {
                return response.json().then(err => {
                    throw new Error(err.detail || `请求失败 (${response.status})`);
                });
            } else {
                // 如果不是JSON响应，返回状态码错误
                throw new Error(`服务器错误 (${response.status})`);
            }
        }
        if (!contentType || !contentType.includes('application/json')) {
            throw new Error('服务器返回了非JSON格式的响应');
        }
        return response.json();
    })
    .then(data => {
        console.log('成功接收到响应:', data);
        displayResults(data);
    })
    .catch(error => {
        console.error('上传或处理错误:', error);
        showError(error.message || '处理请求时发生未知错误');
        loader.style.display = 'none';

        // 显示错误结果
        resultCategory.textContent = '错误';
        resultBrand.textContent = '--';
        resultTime.textContent = '--';
        resultValues.textContent = '--';
        resultAnalysis.textContent = error.message || '处理请求时发生未知错误';
        confidenceBar.style.width = '0%';
        confidenceValue.textContent = '0%';
        rawData.textContent = JSON.stringify({error: error.message}, null, 2);

        resultContent.style.display = 'block';
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
    resetImageSelection();
    dropZone.scrollIntoView({ behavior: 'smooth' });
}

/**
 * 页面加载完成后初始化
 */
document.addEventListener('DOMContentLoaded', () => {
    initUploadArea();

    // 预先填充一个令牌便于测试
    tokenInput.value = 'bobtest';
});