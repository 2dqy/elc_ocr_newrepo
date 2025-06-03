// 定义图表和表格变量
let centerSuccessChart, deviceAnalysisChart, errorAnalysisChart;
let centerRankingTable, deviceAnalysisTable, errorAnalysisTable, rawDataTable;
let currentMonth = '';
let currentRawData = []; // 存储当前的原始数据

// 页面加载完成后初始化
$(document).ready(function () {
    initializePage();
});

/**
 * 初始化页面，包括加载可用月份和绑定事件。
 */
async function initializePage() {
    try {
        // 加载可用月份信息
        await loadAvailableMonths();

        // 绑定月份输入框的change事件，当选择月份变化时加载数据
        $('#monthInput').on('change', function () {
            const selectedMonth = $(this).val();
            if (selectedMonth) {
                loadDashboardData(selectedMonth);
            }
        });

        // 绑定"当月"按钮的点击事件，点击时加载当前月份数据
        $('#currentMonthBtn').on('click', function () {
            $('#monthInput').val(currentMonth);
            loadDashboardData(currentMonth);
        });

    } catch (error) {
        // 初始化失败时显示错误信息
        showError('初始化失败: ' + error.message);
    }
}

/**
 * 从后端加载可用月份数据。
 */
async function loadAvailableMonths() {
    try {
        const response = await fetch('/dashboard/months');
        const result = await response.json();

        if (result.success) {
            // 获取月份列表和当前月份
            const months = result.data.months;
            currentMonth = result.data.current_month;

            // 更新页面上的当前月份指示器
            $('#currentMonthIndicator').html(`当前月份: ${currentMonth} <span class="current-month-badge">当月</span>`);

            // 默认设置月份输入框为当前月份并加载对应数据
            $('#monthInput').val(currentMonth);
            loadDashboardData(currentMonth);

        } else {
            // 如果获取月份数据失败，抛出错误
            throw new Error('获取月份数据失败');
        }
    } catch (error) {
        // 加载可用月份失败时显示错误信息
        showError('加载可用月份失败: ' + error.message);
    }
}

/**
 * 根据指定的年月加载仪表盘数据。
 * @param {string} yearMonth - 年月字符串，格式为YYYY-MM。
 */
async function loadDashboardData(yearMonth) {
    showLoading(); // 显示加载动画

    try {
        // 发送请求获取仪表盘数据
        const response = await fetch(`/dashboard/data?year_month=${yearMonth}`);
        const result = await response.json();

        if (result.success) {
            // 数据获取成功，更新仪表盘并隐藏加载动画
            updateDashboard(result.data);
            hideLoading();
            showDashboard();
        } else {
            // 数据获取失败，抛出错误
            throw new Error('获取数据失败');
        }
    } catch (error) {
        // 加载数据失败时隐藏加载动画并显示错误信息
        hideLoading();
        showError('加载数据失败: ' + error.message);
    }
}

/**
 * 更新仪表盘上的所有数据，包括统计卡片、图表和表格。
 * @param {object} data - 仪表盘数据对象。
 */
function updateDashboard(data) {
    // 更新统计卡片数据
    $('#totalRequests').text(data.total_requests.toLocaleString()); // 总请求数
    $('#successRate').text(data.success_rate_overall + '%'); // 总体成功率
    $('#avgProcessingTime').text(data.avg_processing_time + 's'); // 平均处理时间
    $('#totalCenters').text(data.center_stats.length); // 中心总数

    // 更新图表
    updateCenterSuccessChart(data.center_stats); // 更新中心成功率图表
    updateDeviceAnalysisChart(data.device_analysis); // 更新设备分析图表
    updateErrorAnalysisChart(data.error_analysis); // 更新错误分析图表

    // 更新数据表格
    updateCenterRankingTable(data.center_ranking, data.center_stats); // 更新中心排名表格
    updateDeviceAnalysisTable(data.device_analysis); // 更新设备分析表格
    updateErrorAnalysisTable(data.error_analysis); // 更新错误分析表格
    updateRawDataTable(data.raw_data); // 更新原始数据表格
}

/**
 * 更新中心成功率柱状图。
 * @param {Array} centerStats - 中心统计数据数组。
 */
function updateCenterSuccessChart(centerStats) {
    const ctx = document.getElementById('centerSuccessChart').getContext('2d');

    // 如果图表已存在，则销毁它以避免重复渲染
    if (centerSuccessChart) {
        centerSuccessChart.destroy();
    }

    // 创建新的柱状图
    centerSuccessChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: centerStats.map(center => center.center_id), // X轴标签为中心ID
            datasets: [{
                label: '成功率 (%)', // 数据集标签
                data: centerStats.map(center => center.success_rate), // 数据为成功率
                backgroundColor: 'rgba(102, 126, 234, 0.6)', // 背景颜色
                borderColor: 'rgba(102, 126, 234, 1)', // 边框颜色
                borderWidth: 1 // 边框宽度
            }]
        },
        options: {
            responsive: true, // 响应式布局
            maintainAspectRatio: false, // 不保持纵横比
            scales: {
                y: {
                    beginAtZero: true, // Y轴从0开始
                    max: 100 // Y轴最大值为100
                }
            }
        }
    });
}

/**
 * 更新设备分析甜甜圈图。
 * @param {Array} deviceAnalysis - 设备分析数据数组。
 */
function updateDeviceAnalysisChart(deviceAnalysis) {
    const ctx = document.getElementById('deviceAnalysisChart').getContext('2d');

    // 如果图表已存在，则销毁它
    if (deviceAnalysisChart) {
        deviceAnalysisChart.destroy();
    }

    // 如果没有设备数据，则显示提示信息并返回
    if (deviceAnalysis.length === 0) {
        ctx.fillText('暂无设备数据', 10, 50);
        return;
    }

    // 创建新的甜甜圈图
    deviceAnalysisChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: deviceAnalysis.map(device => device.device_type || 'Unknown'), // 标签为设备类型
            datasets: [{
                data: deviceAnalysis.map(device => device.total_requests), // 数据为总请求数
                backgroundColor: [
                    '#FF6384',
                    '#36A2EB',
                    '#FFCE56',
                    '#4BC0C0',
                    '#9966FF',
                    '#FF9F40'
                ] // 背景颜色数组
            }]
        },
        options: {
            responsive: true, // 响应式布局
            maintainAspectRatio: false, // 不保持纵横比
            plugins: {
                legend: {
                    position: 'bottom' // 图例位置在底部
                }
            }
        }
    });
}

/**
 * 更新错误分析饼图。
 * @param {Array} errorAnalysis - 错误分析数据数组。
 */
function updateErrorAnalysisChart(errorAnalysis) {
    const ctx = document.getElementById('errorAnalysisChart').getContext('2d');

    // 如果图表已存在，则销毁它
    if (errorAnalysisChart) {
        errorAnalysisChart.destroy();
    }

    // 如果没有错误数据，则显示提示信息并返回
    if (errorAnalysis.length === 0) {
        ctx.fillText('暂无失败数据', 10, 50);
        return;
    }

    // 创建新的饼图
    errorAnalysisChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: errorAnalysis.map(error => error.error_message.substring(0, 20) + '...'), // 标签为错误信息（截断）
            datasets: [{
                data: errorAnalysis.map(error => error.count), // 数据为错误计数
                backgroundColor: [
                    '#FF6384',
                    '#36A2EB',
                    '#FFCE56',
                    '#4BC0C0',
                    '#9966FF',
                    '#FF9F40'
                ] // 背景颜色数组
            }]
        },
        options: {
            responsive: true, // 响应式布局
            maintainAspectRatio: false // 不保持纵横比
        }
    });
}

/**
 * 更新中心排名表格。
 * @param {Array} rankings - 排名数据数组。
 * @param {Array} centerStats - 中心统计数据数组。
 */
function updateCenterRankingTable(rankings, centerStats) {
    // 如果表格已存在，则销毁它
    if (centerRankingTable) {
        centerRankingTable.destroy();
    }

    // 合并排名和统计数据，以便在表格中显示完整信息
    const mergedData = rankings.map(ranking => {
        const stats = centerStats.find(stat => stat.center_id === ranking.center_id);
        return {
            rank: ranking.rank,
            center_id: ranking.center_id,
            success_count: ranking.success_count,
            total_requests: stats ? stats.total_requests : 0,
            success_rate: stats ? stats.success_rate : 0
        };
    });

    $('#centerRankingTable tbody').empty(); // 清空表格体
    // 遍历合并后的数据，并添加到表格中
    mergedData.forEach(item => {
        $('#centerRankingTable tbody').append(`
            <tr>
                <td class="number-cell">${item.rank}</td>
                <td>${item.center_id}</td>
                <td class="number-cell">${item.success_count}</td>
                <td class="number-cell">${item.total_requests}</td>
                <td class="number-cell">${item.success_rate}%</td>
            </tr>
        `);
    });

    // 初始化或重新初始化DataTable
    centerRankingTable = $('#centerRankingTable').DataTable({
        pageLength: 10, // 每页显示10条记录
        order: [[0, 'asc']], // 默认按第一列升序排序
        language: {
            url: 'https://cdn.datatables.net/plug-ins/1.13.1/i18n/zh.json' // 设置中文语言包
        },
        columnDefs: [
            { targets: [0, 2, 3, 4], className: 'number-cell' } // 数字列右对齐
        ]
    });
}

/**
 * 更新设备分析表格。
 * @param {Array} deviceAnalysis - 设备分析数据数组。
 */
function updateDeviceAnalysisTable(deviceAnalysis) {
    // 如果表格已存在，则销毁它
    if (deviceAnalysisTable) {
        deviceAnalysisTable.destroy();
    }

    $('#deviceAnalysisTable tbody').empty(); // 清空表格体
    // 遍历设备分析数据，并添加到表格中
    deviceAnalysis.forEach(device => {
        $('#deviceAnalysisTable tbody').append(`
            <tr>
                <td>${device.device_type || 'Unknown'}</td>
                <td class="number-cell">${device.total_requests}</td>
                <td class="number-cell">${device.success_count}</td>
                <td class="number-cell">${device.success_rate}%</td>
                <td class="number-cell">${device.avg_processing_time}</td>
            </tr>
        `);
    });

    // 初始化或重新初始化DataTable
    deviceAnalysisTable = $('#deviceAnalysisTable').DataTable({
        pageLength: 10, // 每页显示10条记录
        order: [[1, 'desc']], // 默认按第二列降序排序
        language: {
            url: 'https://cdn.datatables.net/plug-ins/1.13.1/i18n/zh.json' // 设置中文语言包
        },
        columnDefs: [
            { targets: [1, 2, 3, 4], className: 'number-cell' } // 数字列右对齐
        ]
    });
}

/**
 * 更新错误分析表格。
 * @param {Array} errorAnalysis - 错误分析数据数组。
 */
function updateErrorAnalysisTable(errorAnalysis) {
    // 如果表格已存在，则销毁它
    if (errorAnalysisTable) {
        errorAnalysisTable.destroy();
    }

    $('#errorAnalysisTable tbody').empty(); // 清空表格体
    // 遍历错误分析数据，并添加到表格中
    errorAnalysis.forEach(error => {
        $('#errorAnalysisTable tbody').append(`
            <tr>
                <td>${error.error_message}</td>
                <td class="number-cell">${error.count}</td>
                <td class="number-cell">${error.percentage}%</td>
            </tr>
        `);
    });

    // 初始化或重新初始化DataTable
    errorAnalysisTable = $('#errorAnalysisTable').DataTable({
        pageLength: 10, // 每页显示10条记录
        order: [[1, 'desc']], // 默认按第二列降序排序
        language: {
            url: 'https://cdn.datatables.net/plug-ins/1.13.1/i18n/zh.json' // 设置中文语言包
        },
        columnDefs: [
            { targets: [1, 2], className: 'number-cell' } // 数字列右对齐
        ]
    });
}

/**
 * 更新原始数据表格。
 * @param {Array} rawData - 原始数据数组。
 */
function updateRawDataTable(rawData) {
    // 存储原始数据到全局变量
    currentRawData = rawData;
    
    // 如果表格已存在，则销毁它
    if (rawDataTable) {
        rawDataTable.destroy();
    }

    $('#rawDataTable tbody').empty(); // 清空表格体
    // 遍历原始数据，并添加到表格中
    rawData.forEach(item => {
        $('#rawDataTable tbody').append(`
            <tr>
                <td class="number-cell">${item.id || 'N/A'}</td>
                <td>${new Date(item.timestamp).toLocaleString()}</td>
                <td>${item.client_ip || 'N/A'}</td>
                <td>${item.token || 'N/A'}</td>
                <td>${item.api_endpoint || 'N/A'}</td>
                <td>${item.center_id || 'N/A'}</td>
                <td>${item.device_type || 'N/A'}</td>
                <td>${item.file_upload_id || 'N/A'}</td>
                <td>${item.file_name || 'N/A'}</td>
                <td class="number-cell">${item.file_size ? item.file_size.toLocaleString() : 'N/A'}</td>
                <td><span class="badge ${getStatusBadgeClass(item.status)}">${item.status}</span></td>
                <td class="number-cell">${item.processing_time || 'N/A'}</td>
                <td class="number-cell">${item.ai_usage || 0}</td>
                <td class="number-cell">${item.remaining_times || 0}</td>
                <td class="number-cell">${item.original_times || 0}</td>
                <td>${item.error_message ? item.error_message.substring(0, 50) + (item.error_message.length > 50 ? '...' : '') : 'N/A'}</td>
                <td>${item.error_code || 'N/A'}</td>
            </tr>
        `);
    });

    // 初始化或重新初始化DataTable
    rawDataTable = $('#rawDataTable').DataTable({
        pageLength: 10, // 每页显示10条记录
        order: [[1, 'desc']], // 默认按时间列降序排序
        scrollX: true, // 启用水平滚动
        language: {
            url: 'https://cdn.datatables.net/plug-ins/1.13.1/i18n/zh.json' // 设置中文语言包
        },
        columnDefs: [
            { targets: [0], width: '60px', className: 'number-cell' },        // ID列
            { targets: [1], width: '150px' },       // 时间列
            { targets: [2], width: '120px' },       // 客户端IP列
            { targets: [3], width: '100px' },       // Token列
            { targets: [4], width: '120px' },       // API端点列
            { targets: [5], width: '80px' },        // 中心ID列
            { targets: [6], width: '100px' },       // 设备类型列
            { targets: [7], width: '120px' },       // 文件上传ID列
            { targets: [8], width: '150px' },       // 文件名列
            { targets: [9], width: '120px', className: 'number-cell' },       // 文件大小列
            { targets: [10], width: '80px' },       // 状态列
            { targets: [11], width: '120px', className: 'number-cell' },      // 处理时间列
            { targets: [12], width: '100px', className: 'number-cell' },       // AI使用量列
            { targets: [13], width: '80px', className: 'number-cell' },       // 剩余次数列
            { targets: [14], width: '80px', className: 'number-cell' },       // 原始次数列
            { targets: [15], width: '200px' },      // 错误信息列
            { targets: [16], width: '100px' },      // 错误代码列
            {
                targets: [15], // 错误信息列
                render: function(data, type, row) {
                    if (type === 'display' && data && data !== 'N/A') {
                        return `<span title="${data}">${data.substring(0, 30)}${data.length > 30 ? '...' : ''}</span>`;
                    }
                    return data;
                }
            }
        ]
    });

    // 绑定自定义导出按钮事件
    $('#exportCsvBtn').off('click').on('click', function() {
        exportTableToCSV(currentRawData, 'OCR_原始数据');
    });
}

/**
 * 自定义CSV导出函数
 * @param {Array} data - 要导出的数据
 * @param {String} filename - 文件名
 */
function exportTableToCSV(data, filename) {
    // CSV头部
    const csvHeaders = [
        'ID', '时间', '客户端IP', 'Token', 'API端点', '中心ID', 
        '设备类型', '文件上传ID', '文件名', '文件大小(B)', '状态', 
        '处理时间(s)', 'AI使用量', '剩余次数', '原始次数', '错误信息', '错误代码'
    ];
    
    // 构建CSV内容
    let csvContent = csvHeaders.join(',') + '\n';
    
    data.forEach(item => {
        const row = [
            item.id || '',
            new Date(item.timestamp).toLocaleString(),
            item.client_ip || '',
            item.token || '',
            item.api_endpoint || '',
            item.center_id || '',
            item.device_type || '',
            item.file_upload_id || '',
            item.file_name || '',
            item.file_size || '',
            item.status || '',
            item.processing_time || '',
            item.ai_usage || 0,
            item.remaining_times || 0,
            item.original_times || 0,
            item.error_message ? `"${item.error_message.replace(/"/g, '""')}"` : '',
            item.error_code || ''
        ];
        csvContent += row.join(',') + '\n';
    });
    
    // 创建下载链接
    const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `${filename}_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

/**
 * 根据状态获取对应的徽章CSS类。
 * @param {string} status - 状态字符串（success, failed, not_relevant等）。
 * @returns {string} 对应的CSS类名。
 */
function getStatusBadgeClass(status) {
    switch (status) {
        case 'success':
            return 'bg-success'; // 成功状态的绿色徽章
        case 'failed':
            return 'bg-danger'; // 失败状态的红色徽章
        case 'not_relevant':
            return 'bg-warning'; // 不相关状态的黄色徽章
        default:
            return 'bg-secondary'; // 默认状态的灰色徽章
    }
}

/**
 * 显示加载动画并隐藏仪表盘内容和错误信息。
 */
function showLoading() {
    $('#loadingSpinner').show(); // 显示加载动画
    $('#dashboardContent').hide(); // 隐藏仪表盘内容
    $('#errorMessage').hide(); // 隐藏错误信息
}

/**
 * 隐藏加载动画。
 */
function hideLoading() {
    $('#loadingSpinner').hide(); // 隐藏加载动画
}

/**
 * 显示仪表盘内容并隐藏错误信息。
 */
function showDashboard() {
    $('#dashboardContent').show(); // 显示仪表盘内容
    $('#errorMessage').hide(); // 隐藏错误信息
}

/**
 * 显示错误信息。
 * @param {string} message - 要显示的错误消息。
 */
function showError(message) {
    $('#errorText').text(message); // 设置错误文本
    $('#errorMessage').show(); // 显示错误信息区域
    $('#dashboardContent').hide(); // 隐藏仪表盘内容
}

// 密码验证功能
document.addEventListener('DOMContentLoaded', function () {
    const correctPassword = '3426'; // 正确的密码
    const passwordOverlay = document.getElementById('passwordOverlay'); // 密码覆盖层
    const mainContent = document.getElementById('mainContent'); // 主内容区域
    const passwordForm = document.getElementById('passwordForm'); // 密码表单
    const passwordInput = document.getElementById('passwordInput'); // 密码输入框
    const passwordError = document.getElementById('passwordError'); // 密码错误信息显示区域

    // 检查是否已经验证过（在当前会话中），如果已验证则直接显示主内容
    if (sessionStorage.getItem('dashboard_authenticated') === 'true') {
        showMainContent();
    }

    // 密码表单提交事件监听器
    passwordForm.addEventListener('submit', function (e) {
        e.preventDefault(); // 阻止表单默认提交行为

        const enteredPassword = passwordInput.value.trim(); // 获取用户输入的密码并去除空格

        if (enteredPassword === correctPassword) {
            // 密码正确，保存验证状态到sessionStorage并显示主内容
            sessionStorage.setItem('dashboard_authenticated', 'true');
            showMainContent();
        } else {
            // 密码错误，显示错误信息并清空输入框，重新聚焦
            showError('密码错误，请重新输入');
            passwordInput.value = '';
            passwordInput.focus();
        }
    });

    // 密码输入框的回车键提交事件
    passwordInput.addEventListener('keypress', function (e) {
        if (e.key === 'Enter') {
            passwordForm.dispatchEvent(new Event('submit')); // 触发表单提交事件
        }
    });

    /**
     * 显示主内容区域并隐藏密码覆盖层。
     */
    function showMainContent() {
        passwordOverlay.style.display = 'none'; // 隐藏密码覆盖层
        mainContent.style.display = 'block'; // 显示主内容区域

        // 初始化仪表盘功能
        initializePage();
    }

    /**
     * 显示密码错误信息。
     * @param {string} message - 要显示的错误消息。
     */
    function showError(message) {
        passwordError.textContent = message; // 设置错误文本
        passwordError.style.display = 'block'; // 显示错误信息

        // 3秒后自动隐藏错误信息
        setTimeout(() => {
            passwordError.style.display = 'none';
        }, 3000);
    }

    // 页面加载后自动聚焦到密码输入框
    passwordInput.focus();
});