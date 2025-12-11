import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import re

# 设置页面配置
st.set_page_config(
    page_title="上市公司数字化转型指数查询系统",
    page_icon="📈",
    layout="wide"
)

# 初始化session state
if 'selected_year' not in st.session_state:
    st.session_state.selected_year = "全部年份"
if 'search_input' not in st.session_state:
    st.session_state.search_input = ""

# 标题部分
st.title("上市公司数字化转型指数查询系统")
st.markdown("### 查询1999-2023年上市公司的数字化转型指数数据")

# 数据来源信息
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("数据总量", "51,152")
with col2:
    st.metric("上市公司数量", "11,817")
with col3:
    st.metric("时间范围", "1999-2023")

st.markdown("---")

# 加载数据 - 修复版本
@st.cache_data
def load_data():
    """加载Excel数据"""
    try:
        # 请修改为您的实际文件路径
        excel_path = r'C:\Users\HUMENGQI\Desktop\1999-2023年数字化转型指数汇总.xlsx'
        
        if not os.path.exists(excel_path):
            st.warning(f"文件不存在: {excel_path}")
            return None
        
        # 读取Excel文件
        df = pd.read_excel(excel_path)
        
        # 显示原始列名用于调试
        with st.sidebar.expander("📊 数据列名信息", expanded=False):
            st.write(f"原始列名: {list(df.columns)}")
            st.write(f"数据形状: {df.shape}")
        
        # 标准化列名 - 去掉空格和特殊字符
        df.columns = [str(col).strip().replace('\n', '').replace('\r', '') for col in df.columns]
        
        # 尝试找到正确的列名 - 更加智能的检测
        column_mapping = {}
        
        # 第一步：尝试常见的列名模式
        common_patterns = {
            '股票代码': ['股票代码', '证券代码', '代码', 'stock_code', 'code', 'ticker'],
            '企业名称': ['企业名称', '公司名称', '名称', 'company_name', 'name'],
            '年份': ['年份', '年', 'year', '年度', '会计年度'],
            '数字化转型指数': ['数字化转型指数', '数字化指数', '转型指数', '数字指数', 'digital_index', 'digital_score'],
            '技术维度': ['技术维度', '技术', 'technology', 'tech'],
            '应用维度': ['应用维度', '应用', 'application', 'app']
        }
        
        for standard_name, possible_names in common_patterns.items():
            found = False
            for col in df.columns:
                col_lower = str(col).lower()
                for pattern in possible_names:
                    if pattern in col_lower or col_lower in pattern:
                        column_mapping[col] = standard_name
                        found = True
                        break
                if found:
                    break
        
        # 如果自动映射不成功，尝试手动检查特定列
        if not column_mapping.get('数字化转型指数'):
            # 寻找可能是数字化转型指数的列
            for col in df.columns:
                col_str = str(col)
                # 检查列名是否包含数字或特定关键词
                if any(keyword in col_str for keyword in ['指数', 'score', 'index', 'value', '数值']):
                    # 检查列数据类型是否为数值型
                    if pd.api.types.is_numeric_dtype(df[col]):
                        column_mapping[col] = '数字化转型指数'
                        break
        
        # 如果仍然没有找到数字化转型指数列，使用第一个数值列
        if not column_mapping.get('数字化转型指数'):
            for col in df.columns:
                try:
                    # 尝试转换为数值型
                    test_series = pd.to_numeric(df[col].head(100), errors='coerce')
                    if test_series.notna().sum() > 0:  # 如果有数值数据
                        column_mapping[col] = '数字化转型指数'
                        break
                except:
                    continue
        
        # 应用列名映射
        if column_mapping:
            df = df.rename(columns=column_mapping)
            with st.sidebar.expander("📊 列名映射结果", expanded=False):
                st.write(f"列名映射: {column_mapping}")
                st.write(f"映射后列名: {list(df.columns)}")
        
        # 确保必要的列存在，如果不存在则创建
        required_columns = ['股票代码', '企业名称', '年份', '数字化转型指数']
        for col in required_columns:
            if col not in df.columns:
                st.warning(f"未找到列: {col}，将创建空列")
                df[col] = ''
        
        # 清理和转换数据
        # 1. 股票代码处理 - 支持所有开头的股票代码
        if '股票代码' in df.columns:
            # 将股票代码转换为字符串并清理
            df['股票代码'] = df['股票代码'].astype(str).str.strip()
            
            # 处理股票代码的函数 - 支持所有开头的代码
            def clean_stock_code(code):
                if pd.isna(code) or code == 'nan':
                    return ''
                # 转换为字符串
                code_str = str(code)
                # 移除非数字字符
                digits = ''.join(filter(str.isdigit, code_str))
                
                # 支持不同长度的股票代码
                if len(digits) == 6:
                    return digits
                elif len(digits) > 6:
                    return digits[:6]  # 取前6位
                elif len(digits) < 6 and len(digits) > 0:
                    # 对于少于6位的代码，前面补0
                    return digits.zfill(6)
                else:
                    return ''
            
            # 应用清理函数
            df['股票代码'] = df['股票代码'].apply(clean_stock_code)
        
        # 2. 企业名称处理
        if '企业名称' in df.columns:
            df['企业名称'] = df['企业名称'].astype(str).str.strip()
        
        # 3. 年份处理 - 更加健壮的方法
        if '年份' in df.columns:
            try:
                # 尝试多种方法转换年份
                df['年份'] = df['年份'].astype(str)
                
                # 提取4位数字年份
                def extract_year(x):
                    if pd.isna(x) or x == 'nan':
                        return 1999
                    x_str = str(x)
                    # 查找4位数字
                    matches = re.findall(r'\d{4}', x_str)
                    if matches:
                        try:
                            year = int(matches[0])
                            if 1900 <= year <= 2100:  # 合理的年份范围
                                return year
                        except:
                            pass
                    
                    # 如果没有找到，尝试2位数字年份
                    matches2 = re.findall(r'\d{2}', x_str)
                    if matches2:
                        try:
                            year2 = int(matches2[0])
                            # 假设是20世纪的年份
                            if 0 <= year2 <= 99:
                                return 1900 + year2
                        except:
                            pass
                    
                    return 1999  # 默认值
                
                df['年份'] = df['年份'].apply(extract_year)
                df['年份'] = df['年份'].astype(int)
                
            except Exception as e:
                st.warning(f"年份处理警告: {str(e)}")
                df['年份'] = 1999
        
        # 4. 数字化转型指数处理 - 关键修复部分
        if '数字化转型指数' in df.columns:
            try:
                # 先尝试直接转换
                original_data = df['数字化转型指数'].copy()
                
                # 方法1: 尝试转换为数值
                df['数字化转型指数'] = pd.to_numeric(df['数字化转型指数'], errors='coerce')
                
                # 如果转换后都是NaN，尝试其他方法
                if df['数字化转型指数'].isna().all():
                    # 方法2: 尝试从字符串提取数字
                    if original_data.dtype == 'object':
                        # 提取所有数字（包括小数）
                        df['数字化转型指数'] = original_data.astype(str).str.extract(r'([-+]?\d*\.\d+|[-+]?\d+)')[0]
                        df['数字化转型指数'] = pd.to_numeric(df['数字化转型指数'], errors='coerce')
                
                # 填充缺失值为0
                df['数字化转型指数'] = df['数字化转型指数'].fillna(0)
                
                # 确保是浮点数类型
                df['数字化转型指数'] = df['数字化转型指数'].astype(float)
                
            except Exception as e:
                st.error(f"数字化转型指数处理错误: {str(e)}")
                # 创建默认的数字化转型指数
                df['数字化转型指数'] = 0.0
        
        # 5. 处理技术维度和应用维度
        for col in ['技术维度', '应用维度']:
            if col in df.columns:
                try:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
                except:
                    df[col] = 0
        
        # 显示数据基本信息
        with st.sidebar.expander("📊 数据统计信息", expanded=False):
            st.write(f"数据总行数: {len(df)}")
            if '年份' in df.columns:
                st.write(f"年份范围: {df['年份'].min()} - {df['年份'].max()}")
                st.write(f"唯一年份数: {len(df['年份'].unique())}")
            if '数字化转型指数' in df.columns:
                # 安全获取最小值和最大值
                try:
                    min_val = float(df['数字化转型指数'].min())
                    max_val = float(df['数字化转型指数'].max())
                    st.write(f"数字化转型指数范围: {min_val:.2f} - {max_val:.2f}")
                except:
                    st.write(f"数字化转型指数范围: 数据异常")
        
        return df
        
    except Exception as e:
        st.error(f"数据加载失败：{str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return None

# 加载数据
df = load_data()

# 如果数据加载失败，使用示例数据
if df is None or df.empty:
    st.warning("📊 使用示例数据进行演示")
    
    # 创建更完整的示例数据 - 包含不同开头的股票代码
    sample_years = list(range(1999, 2024))
    all_data = []
    
    companies = [
        {'股票代码': '600611', '企业名称': '大众交通'},  # 6开头 - 沪市主板
        {'股票代码': '000001', '企业名称': '平安银行'},  # 0开头 - 深市主板
        {'股票代码': '300750', '企业名称': '宁德时代'},  # 3开头 - 创业板
        {'股票代码': '688981', '企业名称': '中芯国际'},  # 688开头 - 科创板
        {'股票代码': '002415', '企业名称': '海康威视'},  # 002开头 - 中小板
    ]
    
    for company in companies:
        for year in sample_years:
            # 模拟逐年增长的数据
            base_index = 2.4 if company['股票代码'] == '600611' else 2.0
            growth = (year - 1999) * 0.1
            index_value = max(0, base_index + growth)
            
            all_data.append({
                '股票代码': company['股票代码'],
                '企业名称': company['企业名称'],
                '年份': year,
                '技术维度': min(10, (year - 1999) // 2),
                '应用维度': min(10, (year - 1999) // 3),
                '数字化转型指数': round(index_value, 2)
            })
    
    df = pd.DataFrame(all_data)

# 创建侧边栏
with st.sidebar:
    st.header("🔍 查询设置")
    
    # 选择搜索方式
    search_type = st.radio(
        "选择搜索方式",
        ["股票代码", "企业名称"],
        help="请选择您要使用的搜索方式"
    )
    
    # 根据搜索方式显示不同的输入框
    if search_type == "股票代码":
        st.session_state.search_input = st.text_input(
            "输入股票代码",
            value=st.session_state.search_input,
            placeholder="例如：600611、000001、300750等",
            help="支持各种开头的股票代码：0开头(深市)、3开头(创业板)、6开头(沪市)、688开头(科创板)等"
        )
    else:
        st.session_state.search_input = st.text_input(
            "输入企业名称",
            value=st.session_state.search_input,
            placeholder="例如：大众交通、平安银行等",
            help="请输入完整的上市公司名称"
        )
    
    # 年份选择 - 基于实际数据
    if df is not None and '年份' in df.columns:
        # 获取所有唯一年份并排序
        all_years = sorted(df['年份'].unique())
        all_years = [int(year) for year in all_years if pd.notna(year)]
        
        # 显示1999-2023年的选项
        display_years = list(range(1999, 2024))
        
        # 创建年份选择列表
        year_options = ["全部年份"] + display_years
        
        # 年份选择框
        st.session_state.selected_year = st.selectbox(
            "选择年份（可选）",
            options=year_options,
            index=0,
            help="选择特定年份进行查询，或选择全部年份查看趋势"
        )
    else:
        # 如果数据中没有年份，使用默认范围
        years = list(range(1999, 2024))
        st.session_state.selected_year = st.selectbox(
            "选择年份（可选）",
            ["全部年份"] + years,
            index=0,
            help="选择特定年份进行查询，或选择全部年份查看趋势"
        )
    
    # 执行查询按钮
    execute_query = st.button(
        "🚀 执行查询",
        type="primary",
        use_container_width=True
    )
    
    st.markdown("---")
    st.markdown("### 使用说明")
    st.markdown("""
    1. 在侧边栏选择搜索方式（股票代码或企业名称）
    2. 输入对应的股票代码或企业名称
    3. 支持所有股票代码：0开头(深市)、3开头(创业板)、6开头(沪市)、688开头(科创板)等
    4. 可选：选择特定年份进行查询
    5. 点击执行查询按钮
    6. 查看企业历年数字化转型指数趋势图和详细数据
    """)
    
    st.markdown("---")
    st.caption("数据来源：1999-2023年数字转型指数总表")
    st.caption("更新时间：2024年")

# 显示数据基本信息
with st.expander("📋 查看数据基本信息", expanded=False):
    st.write(f"数据总行数: {len(df):,}")
    st.write(f"数据列数: {len(df.columns)}")
    st.write(f"数据列名: {list(df.columns)}")
    
    # 显示各列的数据类型
    st.write("数据类型:")
    dtype_info = pd.DataFrame({
        '列名': df.columns,
        '数据类型': df.dtypes.astype(str),
        '非空值数量': df.count().values,
        '缺失值数量': df.isnull().sum().values
    })
    st.dataframe(dtype_info, use_container_width=True)
    
    # 显示前10行数据
    st.write("前10行数据:")
    display_df = df.head(10).copy()
    display_df = display_df.reset_index(drop=True)
    display_df.index = display_df.index + 1
    
    # 格式化显示
    if '年份' in display_df.columns:
        display_df['年份'] = display_df['年份'].astype(int)
    
    # 选择要显示的列
    display_columns = []
    for col in ['年份', '股票代码', '企业名称', '技术维度', '应用维度', '数字化转型指数']:
        if col in display_df.columns:
            display_columns.append(col)
    
    st.dataframe(display_df[display_columns], use_container_width=True)

# 当点击查询按钮时执行
if execute_query:
    search_input = st.session_state.search_input
    
    if not search_input:
        st.warning("请输入搜索内容")
    else:
        search_text = search_input.strip()
        
        # 根据搜索类型进行搜索
        result_df = pd.DataFrame()
        
        if search_type == "股票代码":
            try:
                # 清理输入的数字
                search_code = ''.join(filter(str.isdigit, search_text))
                if len(search_code) > 6:
                    search_code = search_code[:6]
                elif len(search_code) < 6 and len(search_code) > 0:
                    search_code = search_code.zfill(6)
                
                # 搜索匹配的数据
                result_df = df[df['股票代码'].astype(str) == search_code]
                
                # 如果找不到，尝试模糊搜索
                if result_df.empty:
                    result_df = df[df['股票代码'].astype(str).str.contains(search_code, na=False)]
                    
            except Exception as e:
                st.error(f"股票代码搜索出错: {str(e)}")
        
        else:  # 搜索方式为"企业名称"
            # 企业名称模糊搜索
            try:
                result_df = df[df['企业名称'].astype(str).str.contains(search_text, na=False, case=False)]
            except Exception as e:
                st.error(f"企业名称搜索出错: {str(e)}")
        
        if result_df.empty:
            st.warning("未找到匹配的数据，请检查输入是否正确")
            st.info("🔍 输入提示:")
            if search_type == "股票代码":
                st.info("1. 股票代码支持各种开头：0开头(深市)、3开头(创业板)、6开头(沪市)、688开头(科创板)等")
                st.info("2. 请输入正确的6位数字股票代码")
            else:
                st.info("1. 企业名称可以输入部分关键词（如：大众、银行等）")
                st.info("2. 请确保输入的企业名称正确")
            
            # 显示相似的企业名称供参考
            if search_type == "企业名称" and len(search_text) >= 2:
                similar_companies = df[df['企业名称'].astype(str).str.contains(search_text[:2], na=False, case=False)]
                if not similar_companies.empty:
                    st.info("相似的公司名称:")
                    similar_display = similar_companies[['股票代码', '企业名称']].drop_duplicates().head(5)
                    st.dataframe(similar_display, use_container_width=True)
        else:
            # 获取选择的年份
            selected_year = st.session_state.selected_year
            
            # 如果选择了特定年份，则进行筛选
            if selected_year != "全部年份" and '年份' in result_df.columns:
                result_df = result_df[result_df['年份'] == int(selected_year)]
            
            # 显示查询结果
            st.success(f"✅ 找到 {len(result_df)} 条记录")
            
            # 显示公司基本信息
            if not result_df.empty:
                # 获取第一家公司信息
                company_info = result_df.iloc[0]
                
                # 获取股票代码和企业名称
                stock_code = str(company_info['股票代码'])
                company_name = str(company_info['企业名称'])
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("股票代码", stock_code)
                with col2:
                    # 修复缩进和变量定义问题
                    display_name = company_name[:25] + "..." if len(company_name) > 25 else company_name
                    st.metric("企业名称", display_name)
                with col3:
                    if selected_year != "全部年份" and '年份' in result_df.columns:
                        st.metric("查询年份", selected_year)
                    else:
                        if '年份' in result_df.columns:
                            years_range = f"{result_df['年份'].min()}-{result_df['年份'].max()}"
                            st.metric("数据年份范围", years_range)
                        else:
                            st.metric("年份信息", "未知")
            
            # 如果是多年份数据，显示趋势图
            if selected_year == "全部年份" and len(result_df) > 1 and '年份' in result_df.columns:
                # 按年份排序并去重（每个年份只保留一条记录）
                trend_df = result_df.sort_values('年份').drop_duplicates('年份')
                
                if len(trend_df) > 1:
                    st.subheader("📈 数字化转型指数趋势图")
                    
                    # 确保年份为整数
                    trend_df['年份'] = trend_df['年份'].astype(int)
                    
                    # 创建趋势图
                    fig = px.line(
                        trend_df,
                        x='年份',
                        y='数字化转型指数',
                        markers=True,
                        title=f"{company_info['企业名称']} 数字化转型指数趋势",
                        labels={'数字化转型指数': '指数值', '年份': '年份'},
                        line_shape='spline'
                    )
                    
                    # 添加数据点
                    fig.add_trace(go.Scatter(
                        x=trend_df['年份'],
                        y=trend_df['数字化转型指数'],
                        mode='markers+text',
                        text=trend_df['数字化转型指数'].round(2),
                        textposition='top center',
                        marker=dict(size=10, color='red'),
                        showlegend=False
                    ))
                    
                    # 更新图表样式
                    fig.update_layout(
                        plot_bgcolor='rgba(240,240,240,0.8)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(size=12),
                        height=400,
                        xaxis=dict(tickmode='linear', dtick=1)
                    )
                    
                    fig.update_traces(
                        line=dict(color='#1f77b4', width=3),
                        marker=dict(size=8)
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # 添加统计分析
                    if '数字化转型指数' in trend_df.columns:
                        st.subheader("📊 统计分析")
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.metric("最高指数", f"{trend_df['数字化转型指数'].max():.2f}")
                        with col2:
                            st.metric("最低指数", f"{trend_df['数字化转型指数'].min():.2f}")
                        with col3:
                            st.metric("平均指数", f"{trend_df['数字化转型指数'].mean():.2f}")
                        with col4:
                            growth = trend_df['数字化转型指数'].iloc[-1] - trend_df['数字化转型指数'].iloc[0]
                            st.metric("总增长", f"{growth:.2f}")
                
                # 如果数据不够绘制趋势图，显示提示
                elif len(trend_df) == 1:
                    st.info("只有一年数据，无法显示趋势图")
            
            # 显示数据表格
            st.subheader("📋 详细数据")
            
            # 格式化显示
            display_df = result_df.copy()
            if selected_year == "全部年份" and '年份' in display_df.columns:
                display_df = display_df.sort_values('年份', ascending=False)
            
            # 重置索引
            display_df = display_df.reset_index(drop=True)
            display_df.index = display_df.index + 1
            
            # 格式化年份列
            if '年份' in display_df.columns:
                display_df['年份'] = display_df['年份'].astype(int)
            
            # 选择要显示的列
            display_columns = []
            for col in ['年份', '股票代码', '企业名称', '技术维度', '应用维度', '数字化转型指数']:
                if col in display_df.columns:
                    display_columns.append(col)
            
            # 格式化数字化转型指数
            if '数字化转型指数' in display_df.columns:
                display_df['数字化转型指数'] = display_df['数字化转型指数'].round(2)
            
            # 显示表格
            st.dataframe(
                display_df[display_columns],
                use_container_width=True,
                height=min(400, len(display_df) * 35 + 38)
            )
            
            # 提供数据下载
            csv = display_df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="💾 下载查询结果 (CSV)",
                data=csv,
                file_name=f"数字化转型指数_{search_text}_{selected_year}.csv",
                mime="text/csv",
                use_container_width=True
            )

# 如果还没有执行查询，显示数据示例
else:
    st.markdown("### 📌 数据示例")
    
    # 显示示例数据
    example_df = df.head(10).copy()
    example_df = example_df.reset_index(drop=True)
    example_df.index = example_df.index + 1
    
    # 格式化年份列
    if '年份' in example_df.columns:
        example_df['年份'] = example_df['年份'].astype(int)
    
    # 选择要显示的列
    display_columns = []
    for col in ['年份', '股票代码', '企业名称', '技术维度', '应用维度', '数字化转型指数']:
        if col in example_df.columns:
            display_columns.append(col)
    
    # 格式化数字化转型指数
    if '数字化转型指数' in example_df.columns:
        example_df['数字化转型指数'] = example_df['数字化转型指数'].round(2)
    
    st.dataframe(
        example_df[display_columns],
        use_container_width=True
    )
    
    st.markdown("---")
    st.info("🔍 请在侧边栏选择股票代码或企业名称，并点击'执行查询'按钮查看数据")
    st.info("💡 **支持所有股票代码类型**：0开头(深市)、3开头(创业板)、6开头(沪市)、688开头(科创板)等")

# 添加CSS样式
st.markdown("""
<style>
    /* 主标题样式 */
    .stTitle {
        color: #1E3A8A;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #1E3A8A;
    }
    
    /* 侧边栏样式 */
    section[data-testid="stSidebar"] {
        background-color: #f8f9fa;
        padding: 1rem;
        border-right: 1px solid #e0e0e0;
    }
    
    /* 指标卡片样式 */
    .stMetric {
        background-color: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #1E3A8A;
    }
    
    /* 按钮样式 */
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        font-weight: bold;
        transition: all 0.3s ease;
        background: linear-gradient(135deg, #1E3A8A, #3B82F6);
        border: none;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(30, 58, 138, 0.3);
    }
    
    /* 数据框样式 */
    .dataframe {
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    .dataframe thead th {
        background-color: #1E3A8A;
        color: white;
        font-weight: bold;
        text-align: center;
    }
    
    .dataframe tbody tr:nth-child(even) {
        background-color: #f8f9fa;
    }
    
    .dataframe tbody tr:hover {
        background-color: #e8f4ff;
    }
    
    /* 表格中的数字对齐 */
    .dataframe td {
        text-align: center !important;
    }
    
    /* 年份选择框的逗号格式化 */
    .stSelectbox option {
        font-family: monospace;
    }
</style>
""", unsafe_allow_html=True)