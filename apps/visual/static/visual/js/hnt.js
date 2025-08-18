// 全局变量
let priceChart = null;
const referencePriceColor = '#FF4D4F'; // 信息价线颜色
const CHART_HEIGHT = 800; // 图表高度
let selectedRegions = []; // 存储选中地区的拼音字段名

// 初始化函数
document.addEventListener('DOMContentLoaded', function() {
    // 初始化地区选择下拉框
    initRegionSelect();

    // 初始化日期选择器 - 默认最近3个月
    initDateRange();

    // 初始化图表
    updateChart();

    // 绑定事件监听
    document.getElementById('apply-filters').addEventListener('click', updateChart);
    document.getElementById('reset-filters').addEventListener('click', resetFilters);

    // 点击页面其他地方关闭下拉框
    document.addEventListener('click', function(event) {
        const container = document.getElementById('region-select-container');
        if (!container.contains(event.target)) {
            document.getElementById('region-dropdown').classList.add('d-none');
        }
    });
});

// 初始化地区选择下拉框
function initRegionSelect() {
    const dropdown = document.getElementById('region-dropdown');
    const displayInput = document.getElementById('region-display');
    const regionItems = dropdown.querySelectorAll('.multi-select-item');

    // 为每个地区项添加点击事件
    regionItems.forEach(item => {
        item.addEventListener('click', function(e) {
            e.stopPropagation();
            item.classList.toggle('selected');

            const field = item.dataset.field;
            const regionName = item.dataset.regionName;

            if (item.classList.contains('selected')) {
                item.innerHTML = `
                    <i class="fa fa-check-circle me-2"></i>
                    <span>${regionName}</span>
                `;
                if (!selectedRegions.includes(field)) {
                    selectedRegions.push(field);
                }
            } else {
                item.innerHTML = `
                    <i class="fa fa-check-circle-o me-2"></i>
                    <span>${regionName}</span>
                `;
                selectedRegions = selectedRegions.filter(r => r !== field);
            }

            updateRegionDisplay();
        });
    });

    // 点击输入框显示/隐藏下拉框
    displayInput.addEventListener('click', function(e) {
        e.stopPropagation();
        dropdown.classList.toggle('d-none');
    });

    // 默认全选
    selectedRegions = [];
    regionItems.forEach(item => {
        const field = item.dataset.field;
        item.classList.add('selected');
        item.innerHTML = `
            <i class="fa fa-check-circle me-2"></i>
            <span>${item.dataset.regionName}</span>
        `;
        selectedRegions.push(field);
    });
    updateRegionDisplay();
}

// 更新地区选择显示
function updateRegionDisplay() {
    const displayInput = document.getElementById('region-display');
    const regionItems = document.querySelectorAll('.multi-select-item.selected');
    const regionNames = Array.from(regionItems).map(item => item.dataset.regionName);

    if (regionNames.length === 0) {
        displayInput.placeholder = '选择地区';
        displayInput.value = '';
    } else if (regionNames.length <= 2) {
        displayInput.value = regionNames.join(', ');
    } else {
        displayInput.value = `${regionNames[0]}, ${regionNames[1]} 等 ${regionNames.length} 个地区`;
    }
}

// 初始化日期范围选择器 - 默认最近3个月
function initDateRange() {
    const today = new Date();
    const threeMonthsAgo = new Date();
    threeMonthsAgo.setMonth(today.getMonth() - 3);

    const formatDate = (date) => {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        return `${year}-${month}`;
    };

    const endDateInput = document.getElementById('end-date');
    const startDateInput = document.getElementById('start-date');

    endDateInput.value = formatDate(today);
    startDateInput.value = formatDate(threeMonthsAgo);

    // 设置最小和最大日期限制
    const minDate = new Date(2020, 0, 1); // 最小日期为2020年
    const maxDate = new Date(today.getFullYear() + 1, 11, 31); // 最大日期为明年12月

    const formatMin = (date) => {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        return `${year}-${month}`;
    };

    startDateInput.min = formatMin(minDate);
    startDateInput.max = formatDate(today);
    endDateInput.min = formatMin(minDate);
    endDateInput.max = formatMin(maxDate);
}

// 获取选中的筛选条件
function getSelectedFilters() {
    const startDate = document.getElementById('start-date').value;
    const endDate = document.getElementById('end-date').value;

    return {
        regions: selectedRegions,
        startDate: startDate,
        endDate: endDate
    };
}

// 重置筛选条件
function resetFilters() {
    const regionItems = document.querySelectorAll('.multi-select-item');
    selectedRegions = [];

    regionItems.forEach(item => {
        const field = item.dataset.field;
        item.classList.add('selected');
        item.innerHTML = `
            <i class="fa fa-check-circle me-2"></i>
            <span>${item.dataset.regionName}</span>
        `;
        selectedRegions.push(field);
    });
    updateRegionDisplay();
    initDateRange();
    updateChart();
}

// 更新图表
function updateChart() {
    const filters = getSelectedFilters();
    updateChartInfo(filters);
    fetchChartData(filters);
}

// 渲染图表
function renderChart(chartData, filters) {
    try {
        const projectData = chartData.project_data || [];
        const referencePriceData = chartData.reference_price_data || [];

        // 获取所有月份并按时间排序
        const allMonths = [...new Set([
            ...projectData.map(item => item.date),
            ...referencePriceData.map(item => item.date)
        ])].sort((a, b) => new Date(a) - new Date(b));

        if (allMonths.length === 0) {
            document.getElementById('chart-wrapper').innerHTML =
                '<div class="text-center py-10 text-secondary">没有找到符合条件的数据</div>';
            if (priceChart) priceChart.destroy();
            return;
        }

        const isSingleMonth = allMonths.length === 1;

        // 更新图表标题
        document.getElementById('chart-title').innerHTML = isSingleMonth
            ? '<i class="fa fa-bar-chart text-primary me-2"></i>项目月均单价与信息价'
            : '<i class="fa fa-line-chart text-primary me-2"></i>价格趋势对比';

        // 准备图表配置
        const chartConfig = isSingleMonth
            ? prepareSingleMonthChart(projectData, referencePriceData, allMonths[0])
            : prepareMultipleMonthsChart(projectData, referencePriceData, allMonths);

        // 确保canvas元素存在
        const canvas = document.getElementById('price-chart');
        if (!canvas) {
            throw new Error('未找到图表容器');
        }

        // 销毁旧图表
        if (priceChart) priceChart.destroy();

        // 渲染新图表
        const ctx = canvas.getContext('2d');
        priceChart = new Chart(ctx, chartConfig);
    } catch (error) {
        console.error('图表渲染失败:', error);
        document.getElementById('chart-wrapper').innerHTML =
            `<div class="text-center py-10 text-danger">图表加载失败: ${error.message}</div>`;
    }
}

// 调整颜色明暗度和透明度的辅助函数
function adjustColor(color, percent, alpha = 1) {
    let R = parseInt(color.substring(1, 3), 16);
    let G = parseInt(color.substring(3, 5), 16);
    let B = parseInt(color.substring(5, 7), 16);

    // 调整颜色明暗度
    R = parseInt(R * (100 + percent) / 100);
    G = parseInt(G * (100 + percent) / 100);
    B = parseInt(B * (100 + percent) / 100);

    // 确保颜色值在有效范围内
    R = Math.min(255, Math.max(0, R));
    G = Math.min(255, Math.max(0, G));
    B = Math.min(255, Math.max(0, B));

    R = Math.round(R);
    G = Math.round(G);
    B = Math.round(B);

    // 转换为带透明度的RGBA格式
    return `rgba(${R}, ${G}, ${B}, ${alpha})`;
}

// 单月图表配置（柱状图+折线图）
function prepareSingleMonthChart(projectData, referenceData, month) {
    // 筛选当月数据
    const monthlyProjects = projectData.filter(item => item.date === month);

    // 生成包含地区的标签（项目名称 + 地区）
    const projectLabels = monthlyProjects.map(item => `${item.name} (${item.region})`);
    const colors = getDistinctColors(monthlyProjects.length);

    // 项目单价柱状图
    const datasets = [{
        type: 'bar',
        label: '项目月均单价',
        data: monthlyProjects.map(item => item.price),
        backgroundColor: colors.map(c => adjustColor(c, 20, 0.6)),
        borderColor: colors.map(c => adjustColor(c, -10, 0.8)),
        borderWidth: 1
    }];

    // 合并所有项目的信息价为一条折线
    const refPrice = referenceData.find(r => r.date === month);
    if (refPrice) {
        datasets.push({
            type: 'line',
            label: '信息价',
            data: monthlyProjects.map(item => {
                return refPrice[item.region] ? refPrice[item.region] : null;
            }),
            borderColor: referencePriceColor,
            backgroundColor: referencePriceColor,
            borderWidth: 2,
            pointRadius: 6,
            fill: false,
            tension: 0.1,
            spanGaps: false // 缺失数据保持空白
        });
    }

    return {
        data: { labels: projectLabels, datasets },
        options: getSingleMonthOptions()
    };
}

// 多月图表配置函数
function prepareMultipleMonthsChart(projectData, referenceData, months) {
    const projectNames = [...new Set(projectData.map(item => item.name))];
    const colors = getDistinctColors(projectNames.length);
    const datasets = [];

    // 项目价格折线
    projectNames.forEach((name, index) => {
        datasets.push({
            type: 'line',
            label: name,
            data: months.map(month => {
                const item = projectData.find(p => p.name === name && p.date === month);
                return item ? item.price : null;
            }),
            borderColor: colors[index],
            backgroundColor: colors[index],
            borderWidth: 2,
            fill: false,
            spanGaps: false
        });
    });

    // 地区信息价折线
    const regions = [...new Set(projectData.map(item => item.region))];
    regions.forEach(region => {
        datasets.push({
            type: 'line',
            label: `${region} 信息价`,
            data: months.map(month => {
                const item = referenceData.find(r => r.date === month);
                return item ? item[region] || null : null;
            }),
            borderColor: referencePriceColor,
            borderWidth: 3,
            borderDash: [5, 5],
            fill: false,
            pointRadius: 5,
            spanGaps: false
        });
    });

    return {
        data: { labels: months, datasets },
        options: getMultipleMonthsOptions()
    }
}

// 图表配置项
function getSingleMonthOptions() {
    return {
        responsive: true,
        maintainAspectRatio: false,
        height: CHART_HEIGHT,
        scales: {
            y: { title: { display: true, text: '单价' } }
        }
    };
}

function getMultipleMonthsOptions() {
    return {
        responsive: true,
        maintainAspectRatio: false,
        height: CHART_HEIGHT,
        scales: {
            x: { title: { display: true, text: '月份' } },
            y: { title: { display: true, text: '单价' } }
        }
    };
}

// 更新图表信息显示
function updateChartInfo(filters) {
    const regionItems = document.querySelectorAll('.multi-select-item.selected');
    const regionNames = Array.from(regionItems).map(item => item.dataset.regionName);

    const regionText = regionNames.length > 3
        ? `${regionNames.slice(0, 3).join(', ')} 等 ${regionNames.length} 个地区`
        : regionNames.join(', ');

    const startDate = document.getElementById('start-date').value;
    const endDate = document.getElementById('end-date').value;
    const monthText = startDate && endDate ? `${startDate} 至 ${endDate}` : '所有时间';

    document.getElementById('display-details').textContent = `${regionText}，${monthText}`;
}

// 生成不同的颜色
function getDistinctColors(count) {
    const colors = [
        '#0d6efd', '#198754', '#6610f2', '#fd7e14', '#dc3545', '#f8f9fa',
        '#20c997', '#0dcaf0', '#7b61ff', '#ff5722', '#eb2f96', '#00b42a',
        '#8B4513', '#20B2AA', '#FF6347', '#4682B4', '#BA55D3', '#F0E68C'
    ];

    // 如果需要的颜色超过预定义的，循环使用
    const result = [];
    for (let i = 0; i < count; i++) {
        result.push(colors[i % colors.length]);
    }

    return result;
}
