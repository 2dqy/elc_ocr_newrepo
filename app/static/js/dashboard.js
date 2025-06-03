let centerSuccessChart, deviceAnalysisChart, errorAnalysisChart;
let centerRankingTable, deviceAnalysisTable, errorAnalysisTable, rawDataTable;
let currentMonth = '';

// 页面加载完成后初始化
$(document).ready(function () {
    initializePage();
});

async function initializePage() {
    try {
        // 加载可用月份信息
        await loadAvailableMonths();

        // 绑定月份输入事件
        $('#monthInput').on('change', function () {
            const selectedMonth = $(this).val();
            if (selectedMonth) {
                loadDashboardData(selectedMonth);
            }
        });

        // 绑定当月按钮事件
        $('#currentMonthBtn').on('click', function () {
            $('#monthInput').val(currentMonth);
            loadDashboardData(currentMonth);
        });

    } catch (error) {
        showError('初始化失败: ' + error.message);
    }
}

async function loadAvailableMonths() {
    try {
        const response = await fetch('/dashboard/months');
        const result = await response.json();

        if (result.success) {
            const months = result.data.months;
            currentMonth = result.data.current_month;

            // 设置当月指示器
            $('#currentMonthIndicator').html(`当前月份: ${currentMonth} <span class="current-month-badge">当月</span>`);

            // 默认设置为当月并加载数据
            $('#monthInput').val(currentMonth);
            loadDashboardData(currentMonth);

        } else {
            throw new Error('获取月份数据失败');
        }
    } catch (error) {
        showError('加载可用月份失败: ' + error.message);
    }
}

async function loadDashboardData(yearMonth) {
    showLoading();

    try {
        const response = await fetch(`/dashboard/data?year_month=${yearMonth}`);
        const result = await response.json();

        if (result.success) {
            updateDashboard(result.data);
            hideLoading();
            showDashboard();
        } else {
            throw new Error('获取数据失败');
        }
    } catch (error) {
        hideLoading();
        showError('加载数据失败: ' + error.message);
    }
}

function updateDashboard(data) {
    // 更新统计卡片
    $('#totalRequests').text(data.total_requests.toLocaleString());
    $('#successRate').text(data.success_rate_overall + '%');
    $('#avgProcessingTime').text(data.avg_processing_time + 's');
    $('#totalCenters').text(data.center_stats.length);

    // 更新图表
    updateCenterSuccessChart(data.center_stats);
    updateDeviceAnalysisChart(data.device_analysis);
    updateErrorAnalysisChart(data.error_analysis);

    // 更新数据表格
    updateCenterRankingTable(data.center_ranking, data.center_stats);
    updateDeviceAnalysisTable(data.device_analysis);
    updateErrorAnalysisTable(data.error_analysis);
    updateRawDataTable(data.raw_data);
}

function updateCenterSuccessChart(centerStats) {
    const ctx = document.getElementById('centerSuccessChart').getContext('2d');

    if (centerSuccessChart) {
        centerSuccessChart.destroy();
    }

    centerSuccessChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: centerStats.map(center => center.center_id),
            datasets: [{
                label: '成功率 (%)',
                data: centerStats.map(center => center.success_rate),
                backgroundColor: 'rgba(102, 126, 234, 0.6)',
                borderColor: 'rgba(102, 126, 234, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100
                }
            }
        }
    });
}

function updateDeviceAnalysisChart(deviceAnalysis) {
    const ctx = document.getElementById('deviceAnalysisChart').getContext('2d');

    if (deviceAnalysisChart) {
        deviceAnalysisChart.destroy();
    }

    if (deviceAnalysis.length === 0) {
        ctx.fillText('暂无设备数据', 10, 50);
        return;
    }

    deviceAnalysisChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: deviceAnalysis.map(device => device.device_type || 'Unknown'),
            datasets: [{
                data: deviceAnalysis.map(device => device.total_requests),
                backgroundColor: [
                    '#FF6384',
                    '#36A2EB',
                    '#FFCE56',
                    '#4BC0C0',
                    '#9966FF',
                    '#FF9F40'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

function updateErrorAnalysisChart(errorAnalysis) {
    const ctx = document.getElementById('errorAnalysisChart').getContext('2d');

    if (errorAnalysisChart) {
        errorAnalysisChart.destroy();
    }

    if (errorAnalysis.length === 0) {
        ctx.fillText('暂无失败数据', 10, 50);
        return;
    }

    errorAnalysisChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: errorAnalysis.map(error => error.error_message.substring(0, 20) + '...'),
            datasets: [{
                data: errorAnalysis.map(error => error.count),
                backgroundColor: [
                    '#FF6384',
                    '#36A2EB',
                    '#FFCE56',
                    '#4BC0C0',
                    '#9966FF',
                    '#FF9F40'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false
        }
    });
}

function updateCenterRankingTable(rankings, centerStats) {
    if (centerRankingTable) {
        centerRankingTable.destroy();
    }

    // 合并排名和统计数据
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

    $('#centerRankingTable tbody').empty();
    mergedData.forEach(item => {
        $('#centerRankingTable tbody').append(`
            <tr>
                <td>${item.rank}</td>
                <td>${item.center_id}</td>
                <td>${item.success_count}</td>
                <td>${item.total_requests}</td>
                <td>${item.success_rate}%</td>
            </tr>
        `);
    });

    centerRankingTable = $('#centerRankingTable').DataTable({
        pageLength: 10,
        order: [[0, 'asc']],
        language: {
            url: 'https://cdn.datatables.net/plug-ins/1.13.1/i18n/zh.json'
        }
    });
}

function updateDeviceAnalysisTable(deviceAnalysis) {
    if (deviceAnalysisTable) {
        deviceAnalysisTable.destroy();
    }

    $('#deviceAnalysisTable tbody').empty();
    deviceAnalysis.forEach(device => {
        $('#deviceAnalysisTable tbody').append(`
            <tr>
                <td>${device.device_type || 'Unknown'}</td>
                <td>${device.total_requests}</td>
                <td>${device.success_count}</td>
                <td>${device.success_rate}%</td>
                <td>${device.avg_processing_time}</td>
            </tr>
        `);
    });

    deviceAnalysisTable = $('#deviceAnalysisTable').DataTable({
        pageLength: 10,
        order: [[1, 'desc']],
        language: {
            url: 'https://cdn.datatables.net/plug-ins/1.13.1/i18n/zh.json'
        }
    });
}

function updateErrorAnalysisTable(errorAnalysis) {
    if (errorAnalysisTable) {
        errorAnalysisTable.destroy();
    }

    $('#errorAnalysisTable tbody').empty();
    errorAnalysis.forEach(error => {
        $('#errorAnalysisTable tbody').append(`
            <tr>
                <td>${error.error_message}</td>
                <td>${error.count}</td>
                <td>${error.percentage}%</td>
            </tr>
        `);
    });

    errorAnalysisTable = $('#errorAnalysisTable').DataTable({
        pageLength: 10,
        order: [[1, 'desc']],
        language: {
            url: 'https://cdn.datatables.net/plug-ins/1.13.1/i18n/zh.json'
        }
    });
}

function updateRawDataTable(rawData) {
    if (rawDataTable) {
        rawDataTable.destroy();
    }

    $('#rawDataTable tbody').empty();
    rawData.forEach(item => {
        $('#rawDataTable tbody').append(`
            <tr>
                <td>${new Date(item.timestamp).toLocaleString()}</td>
                <td>${item.token}</td>
                <td>${item.center_id || 'N/A'}</td>
                <td>${item.device_type || 'N/A'}</td>
                <td>${item.file_name || 'N/A'}</td>
                <td><span class="badge ${getStatusBadgeClass(item.status)}">${item.status}</span></td>
                <td>${item.processing_time || 'N/A'}</td>
                <td>${item.ai_usage || 0}</td>
                <td>${item.remaining_times || 0}</td>
            </tr>
        `);
    });

    rawDataTable = $('#rawDataTable').DataTable({
        pageLength: 10,
        order: [[0, 'desc']],
        language: {
            url: 'https://cdn.datatables.net/plug-ins/1.13.1/i18n/zh.json'
        }
    });
}

function getStatusBadgeClass(status) {
    switch (status) {
        case 'success':
            return 'bg-success';
        case 'failed':
            return 'bg-danger';
        case 'not_relevant':
            return 'bg-warning';
        default:
            return 'bg-secondary';
    }
}

function showLoading() {
    $('#loadingSpinner').show();
    $('#dashboardContent').hide();
    $('#errorMessage').hide();
}

function hideLoading() {
    $('#loadingSpinner').hide();
}

function showDashboard() {
    $('#dashboardContent').show();
    $('#errorMessage').hide();
}

function showError(message) {
    $('#errorText').text(message);
    $('#errorMessage').show();
    $('#dashboardContent').hide();
}

// 密码验证功能
document.addEventListener('DOMContentLoaded', function () {
    const correctPassword = '3426';
    const passwordOverlay = document.getElementById('passwordOverlay');
    const mainContent = document.getElementById('mainContent');
    const passwordForm = document.getElementById('passwordForm');
    const passwordInput = document.getElementById('passwordInput');
    const passwordError = document.getElementById('passwordError');

    // 检查是否已经验证过（在当前会话中）
    if (sessionStorage.getItem('dashboard_authenticated') === 'true') {
        showMainContent();
    }

    // 密码表单提交事件
    passwordForm.addEventListener('submit', function (e) {
        e.preventDefault();

        const enteredPassword = passwordInput.value.trim();

        if (enteredPassword === correctPassword) {
            // 密码正确，保存验证状态并显示主内容
            sessionStorage.setItem('dashboard_authenticated', 'true');
            showMainContent();
        } else {
            // 密码错误，显示错误信息
            showError('密码错误，请重新输入');
            passwordInput.value = '';
            passwordInput.focus();
        }
    });

    // 回车键提交
    passwordInput.addEventListener('keypress', function (e) {
        if (e.key === 'Enter') {
            passwordForm.dispatchEvent(new Event('submit'));
        }
    });

    function showMainContent() {
        passwordOverlay.style.display = 'none';
        mainContent.style.display = 'block';

        // 加载原有的 dashboard.js 功能
        if (typeof loadDashboard === 'function') {
            loadDashboard();
        }
    }

    function showError(message) {
        passwordError.textContent = message;
        passwordError.style.display = 'block';

        // 3秒后隐藏错误信息
        setTimeout(() => {
            passwordError.style.display = 'none';
        }, 3000);
    }

    // 自动聚焦到密码输入框
    passwordInput.focus();
});