import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.arima.model import ARIMA
from sklearn.metrics import mean_squared_error
from math import sqrt

from .models import ConcretePrice

# 所有城市的字段名（与 models.py 中一致）
CITY_FIELDS = [
    'wuhan', 'huanggang', 'xiangyang', 'shiyan', 'jingzhou', 'yichang',
    'enshi', 'suizhou', 'jingmen', 'ezhou', 'xiantao', 'qianjiang',
    'tianmen', 'shennongjia', 'xianning', 'huangshi', 'xiaogan'
]

# 城市中英文映射（用于日志和提示）
CITY_NAME_MAP = {
    'wuhan': '武汉市',
    'huanggang': '黄冈市',
    'xiangyang': '襄阳市',
    'shiyan': '十堰市',
    'jingzhou': '荆州市',
    'yichang': '宜昌市',
    'enshi': '恩施市',
    'suizhou': '随州市',
    'jingmen': '荆门市',
    'ezhou': '鄂州市',
    'xiantao': '仙桃市',
    'qianjiang': '潜江市',
    'tianmen': '天门市',
    'shennongjia': '神农架',
    'xianning': '咸宁市',
    'huangshi': '黄石市',
    'xiaogan': '孝感市'
}


@login_required
def price_predict_page(request):
    """渲染预测页面"""
    print(f"🟢 [用户访问] 用户 '{request.user.username}' 访问了价格预测页面")
    return render(request, 'price_predict.html')


@login_required
def price_predict_api(request):
    """
    API 接口：为用户选择的特定城市生成混凝土价格预测
    核心优化：拆分两次模型训练
    1. 第一次训练（训练集）：仅用于检验模型效果（计算RMSE）
    2. 第二次训练（全量数据）：用于最终未来预测（最大化数据利用率）
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持 POST 请求'})

    try:
        # 解析请求数据，获取用户选择的城市
        request_data = json.loads(request.body)
        selected_city = request_data.get('city')

        # 验证城市选择
        if not selected_city or selected_city not in CITY_FIELDS:
            return JsonResponse({
                'success': False,
                'error': f'请选择有效的城市，可选城市：{list(CITY_NAME_MAP.values())}'
            })

        print(f"🔵 [开始预测] 用户: {request.user.username} | 城市: {CITY_NAME_MAP.get(selected_city, selected_city)}")

        # 1. 从数据库加载数据并清洗（仅加载需要的字段）
        qs = ConcretePrice.objects.all().order_by('date')
        if not qs.exists():
            return JsonResponse({'success': False, 'error': '数据库中无价格数据'})

        # 转换为DataFrame并处理数据类型
        df = pd.DataFrame(list(qs.values('date', selected_city)))
        df['date'] = pd.to_datetime(df['date'])
        # 将Decimal类型转换为float（避免计算冲突）
        df[selected_city] = df[selected_city].apply(lambda x: float(x) if x is not None else None)

        # 数据清洗：移除空值、0值、异常值（3σ原则）
        df = df.dropna(subset=[selected_city])  # 移除空值
        df = df[df[selected_city] > 0]  # 移除0值
        price_mean = df[selected_city].mean()
        price_std = df[selected_city].std()
        df = df[
            (df[selected_city] >= price_mean - 3 * price_std) &
            (df[selected_city] <= price_mean + 3 * price_std)
            ]  # 移除异常值
        df = df.sort_values('date').drop_duplicates(subset=['date'], keep='last').reset_index(drop=True)  # 去重排序

        print(f"📊 [数据加载] 加载 {selected_city} 价格数据 | 原始记录: {len(qs)} | 清洗后: {len(df)}")

        # 验证数据量（至少3个点：满足训练集+测试集拆分）
        if len(df) < 3:
            return JsonResponse({
                'success': False,
                'error': f'{CITY_NAME_MAP.get(selected_city, selected_city)} 有效数据不足（需至少3个月数据），当前仅 {len(df)} 个月数据'
            })

        # 2. 准备时间序列数据（清洗后的全量数据）
        df[selected_city] = df[selected_city].astype('float64')  # 确保价格为float类型
        prices = df[selected_city].values  # 全量价格数据
        dates = df['date'].values  # 全量日期数据
        total_points = len(prices)

        # 3. 拆分训练集/测试集（仅用于模型效果检验）
        test_size = min(3, max(1, total_points // 5))  # 测试集大小：1-3个点（最多总数据的1/5）
        train_size = total_points - test_size
        if train_size < 2:  # 训练集至少2个点才能拟合模型
            return JsonResponse({
                'success': False,
                'error': f'{CITY_NAME_MAP.get(selected_city, selected_city)} 训练数据不足，需至少2个训练点'
            })

        # 分割数据（训练集用于检验模型，全量数据后续用于最终预测）
        train_prices = prices[:train_size]
        test_prices = prices[train_size:]
        train_dates = dates[:train_size]
        test_dates = dates[train_size:]
        print(f"  📈 数据分割 | 训练集: {train_size} 个点 | 测试集: {test_size} 个点 | 全量数据: {total_points} 个点")

        # 4. 第一次训练：用训练集拟合模型（仅用于检验效果）
        model_train, fitted_model_train = None, None
        model_type = 'ARIMA' if total_points < 12 else 'SARIMAX'  # 统一模型类型（两次训练保持一致）
        try:
            if model_type == 'ARIMA':
                model_train = ARIMA(
                    train_prices,
                    order=(1, 1, 0),
                    enforce_stationarity=False
                )
            else:  # SARIMAX（数据量充足，捕捉季节性）
                model_train = SARIMAX(
                    train_prices,
                    order=(1, 1, 0),
                    seasonal_order=(1, 1, 0, 6),  # 6个月季节性周期（符合建材价格规律）
                    enforce_stationarity=False,
                    enforce_invertibility=False
                )
            fitted_model_train = model_train.fit()
            print(f"  ✅ 第一次训练完成（{model_type}，训练集）")
        except Exception as model_err:
            # 降级为简单ARIMA模型重试
            print(f"  ⚠️  第一次训练失败: {str(model_err)}，降级为简单ARIMA模型")
            model_type = 'ARIMA'  # 强制切换为ARIMA
            model_train = ARIMA(train_prices, order=(1, 1, 0), enforce_stationarity=False)
            fitted_model_train = model_train.fit()
            print(f"  ✅ 第一次训练完成（降级ARIMA，训练集）")

        # 5. 模型效果检验：用训练集模型预测测试集，计算RMSE
        test_pred = fitted_model_train.predict(
            start=len(train_prices),
            end=len(train_prices) + len(test_prices) - 1
        )

        # 平滑测试集预测结果（避免异常波动）
        def smooth_predictions(actuals, predictions, max_change_rate=0.15):
            """平滑预测值：变化率不超过15%（符合建材价格稳定性）"""
            if len(predictions) == 0:
                return predictions
            smoothed = []
            last_actual = actuals[-1] if len(actuals) > 0 else predictions[0]
            for pred in predictions:
                max_increase = last_actual * (1 + max_change_rate)
                max_decrease = last_actual * (1 - max_change_rate)
                smoothed_pred = max(max_decrease, min(max_increase, pred))
                smoothed.append(smoothed_pred)
                last_actual = smoothed_pred
            return np.array(smoothed)

        test_pred_smoothed = smooth_predictions(train_prices, test_pred)
        rmse = sqrt(mean_squared_error(test_prices, test_pred_smoothed))

        # 计算趋势吻合度
        def calculate_trend_accuracy(actual_values, predicted_values):
            """
            计算趋势吻合度
            通过比较实际值和预测值的变化方向来计算趋势准确性
            """
            if len(actual_values) < 2 or len(predicted_values) < 2:
                return 0

            actual_directions = []
            predicted_directions = []

            for i in range(1, min(len(actual_values), len(predicted_values))):
                actual_directions.append(1 if actual_values[i] > actual_values[i - 1] else
                                         -1 if actual_values[i] < actual_values[i - 1] else 0)
                predicted_directions.append(1 if predicted_values[i] > predicted_values[i - 1] else
                                            -1 if predicted_values[i] < predicted_values[i - 1] else 0)

            # 计算方向匹配的比例
            matches = sum(1 for a, p in zip(actual_directions, predicted_directions) if a == p)
            trend_accuracy = matches / len(actual_directions) * 100 if actual_directions else 0

            return round(trend_accuracy, 2)

        trend_accuracy = calculate_trend_accuracy(test_prices, test_pred_smoothed)
        print(f"  📊 模型检验 | RMSE: {rmse:.2f} | 趋势吻合度: {trend_accuracy:.2f}% | 平均价格: {np.mean(prices):.2f}")

        # 6. 第二次训练：用全量数据拟合模型（用于最终未来预测）
        fitted_model_full = None
        try:
            if model_type == 'ARIMA':
                model_full = ARIMA(
                    prices,  # 用全量数据训练
                    order=(1, 1, 0),
                    enforce_stationarity=False
                )
            else:
                model_full = SARIMAX(
                    prices,  # 用全量数据训练
                    order=(1, 1, 0),
                    seasonal_order=(1, 1, 0, 6),
                    enforce_stationarity=False,
                    enforce_invertibility=False
                )
            fitted_model_full = model_full.fit(disp=False)
            print(f"  ✅ 第二次训练完成（{model_type}，全量数据）")
        except Exception as full_model_err:
            return JsonResponse({
                'success': False,
                'error': f'全量数据模型拟合失败: {str(full_model_err)}'
            })

        # 7. 最终预测：用全量数据模型预测未来3个月
        forecast = fitted_model_full.forecast(steps=3)
        # 基于全量数据平滑未来预测结果（更贴合实际趋势）
        forecast_smoothed = smooth_predictions(prices, forecast)
        print(f"  🔧 未来预测结果平滑处理完成")

        # 8. 准备返回数据格式
        # 8.1 历史数据（全量清洗后的数据）
        history_data = [
            {'date': pd.to_datetime(date).strftime('%Y-%m-%d'), 'value': float(price)}
            for date, price in zip(dates, prices)
        ]

        # 8.2 测试集预测数据（用于前端展示模型检验效果）
        test_pred_data = [
            {'date': pd.to_datetime(date).strftime('%Y-%m-%d'), 'value': float(pred)}
            for date, pred in zip(test_dates, test_pred_smoothed)
        ]

        # 8.3 未来预测数据（生成合理日期：基于最后一个实际日期的下月同日）
        last_date = pd.to_datetime(df['date'].max())
        forecast_dates = []
        for i in range(1, 4):
            next_month = last_date + pd.DateOffset(months=i)
            # 处理月份天数差异（如2月没有31日，自动取当月最后一天）
            try:
                forecast_date = next_month.replace(day=last_date.day)
            except ValueError:
                forecast_date = next_month + pd.DateOffset(months=1) - pd.DateOffset(days=1)
            forecast_dates.append(forecast_date.strftime('%Y-%m-%d'))

        forecast_data = [
            {'date': date, 'value': float(price)}
            for date, price in zip(forecast_dates, forecast_smoothed)
        ]

        # 9. 构建最终返回结果
        result = {
            selected_city: {
                'history': history_data,
                'test_pred': test_pred_data,  # 模型检验用的测试预测
                'forecast': forecast_data,  # 全量模型生成的最终预测
                'rmse': round(rmse, 2),  # 模型检验的RMSE
                'trend_accuracy': trend_accuracy,  # 趋势吻合度
                'avg_price': round(np.mean(prices), 2),
                'data_points': total_points,
                'model_used': model_type  # 两次训练统一的模型类型
            }
        }

        print(
            f"🎯 [预测完成] {CITY_NAME_MAP.get(selected_city, selected_city)} 预测成功 | 模型: {model_type} | RMSE: {rmse:.2f} | 趋势吻合度: {trend_accuracy:.2f}%")

        return JsonResponse({
            'success': True,
            'data': result,
            'city_name': CITY_NAME_MAP.get(selected_city, selected_city),
            'avg_rmse': round(rmse, 2),
            'trend_accuracy': trend_accuracy
        })

    except Exception as e:
        print(f"❌ 预测过程异常: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'预测过程发生错误: {str(e)}'
        })
