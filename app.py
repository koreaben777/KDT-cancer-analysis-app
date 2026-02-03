'''
Project.app의 Docstring
'''

import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import platform
import os

# -----------------------------------------------------------
# 0. [설정] 분석할 공통 암종 리스트 (표준 명칭 정의)
# -----------------------------------------------------------
COMMON_CANCERS = [
    "위암", "대장암", "폐암", "간암", "유방암", 
    "자궁경부암", "전립선암", "췌장암", "백혈병", 
    "방광암", "난소암"
]
TARGET_YEARS = list(range(1999, 2024))

# -----------------------------------------------------------
# 1. 한글 폰트 설정
# -----------------------------------------------------------
def set_korean_font():
    font_path = 'NanumGothic.ttf'
    if os.path.exists(font_path):
        fm.fontManager.addfont(font_path)
        font_name = fm.FontProperties(fname=font_path).get_name()
        plt.rcParams['font.family'] = font_name
    else:
        system_name = platform.system()
        if system_name == 'Darwin': 
            plt.rcParams['font.family'] = 'AppleGothic'
        elif system_name == 'Windows': 
            plt.rcParams['font.family'] = 'Malgun Gothic'
        else: 
            plt.rcParams['font.family'] = 'NanumGothic'
            
    plt.rcParams['axes.unicode_minus'] = False

set_korean_font()

# -----------------------------------------------------------
# 2. 데이터 불러오기 및 전처리 함수
# -----------------------------------------------------------
def read_csv_safe(filename):
    if not os.path.exists(filename):
        return None
    try:
        return pd.read_csv(filename, encoding='utf-8', engine='python')
    except:
        pass
    try:
        return pd.read_csv(filename, encoding='euc-kr', engine='python')
    except:
        pass
    try:
        return pd.read_csv(filename, encoding='cp949', engine='python')
    except:
        return None

# (1) 조발생률 데이터 로드
@st.cache_data
def load_incidence_data():
    filename = 'data_incidence.csv'
    df = read_csv_safe(filename)
    
    if df is None:
        return None

    df = df[df['발생연도'].astype(str).str.isnumeric()]
    df['발생연도'] = df['발생연도'].astype(int)
    
    mapping_inc = {
        '위': '위암', '대장': '대장암', '폐': '폐암', '간': '간암',
        '유방': '유방암', '자궁경부': '자궁경부암', '전립선': '전립선암',
        '췌장': '췌장암', '백혈병': '백혈병', '방광': '방광암',
        '난소': '난소암', '갑상선': '갑상선암'
    }
    
    df['암종_표준'] = df['암종'].map(mapping_inc)
    df = df.dropna(subset=['암종_표준'])
    df = df[df['연령군'] == '연령전체'] 
    
    return df

# (2) 사망률 데이터 로드
@st.cache_data
def load_death_data():
    filename = 'data_death.csv'
    df = read_csv_safe(filename)
    
    if df is None:
        return None

    if '국가' in df.columns:
        df = df[df['국가'].str.contains('한국|대한민국', na=False)]

    mapping_death = {
        '위암': '위암', '대장·직장·항문암': '대장암', '기관·기관지·폐암': '폐암',
        '간암': '간암', '여성 유방암': '유방암', '자궁경부암': '자궁경부암',
        '전립선암': '전립선암', '췌장암': '췌장암', '백혈병': '백혈병',
        '방광암': '방광암', '난소암': '난소암'
    }

    df['암종_표준'] = df['항목'].map(mapping_death)
    df = df.dropna(subset=['암종_표준'])

    id_vars = ['성별', '암종_표준']
    year_cols = [c for c in df.columns if '년' in str(c) or str(c).strip().isdigit()]
    
    df_melted = df.melt(id_vars=id_vars, value_vars=year_cols, 
                        var_name='발생연도', value_name='사망률')
    
    df_melted['발생연도'] = df_melted['발생연도'].astype(str).str.replace(' 년', '').str.strip()
    df_melted = df_melted[df_melted['발생연도'].str.isnumeric()]
    df_melted['발생연도'] = df_melted['발생연도'].astype(int)
    
    df_melted = df_melted.rename(columns={'암종_표준': '암종'})
    df_melted['사망률'] = pd.to_numeric(df_melted['사망률'], errors='coerce').fillna(0)
    
    df_final = df_melted.groupby(['발생연도', '성별', '암종'], as_index=False)['사망률'].sum()

    return df_final

# -----------------------------------------------------------
# 3. 데이터 로딩 및 사이드바
# -----------------------------------------------------------
if st.sidebar.button("캐시 데이터 지우기"):
    st.cache_data.clear()
    st.rerun()

df_inc = load_incidence_data()
df_death = load_death_data()

# -----------------------------------------------------------
# 4. 메인 화면 및 옵션
# -----------------------------------------------------------
st.title('📊 암 발생 및 사망률 히트맵 분석')
st.markdown("드롭다운을 변경해도 **X축(연도)**과 **Y축(암종)**은 고정됩니다.")

if df_inc is None or df_death is None:
    st.error("❌ 데이터 파일을 읽을 수 없습니다. (Reboot App을 시도해보세요)")
    st.stop()

data_option = st.selectbox(
    "확인할 지표를 선택하세요:",
    ["조발생률 (Incidence Rate)", "사망률 (Death Rate)"]
)

if data_option.startswith("조발생률"):
    target_df = df_inc
    value_col = '조발생률'
    target_df['암종'] = target_df['암종_표준']
    df_male = target_df[target_df['성별'] == '남자']
    df_female = target_df[target_df['성별'] == '여자']
    
elif data_option.startswith("사망률"):
    target_df = df_death
    value_col = '사망률'
    df_male = target_df[target_df['성별'].str.contains('남')]
    df_female = target_df[target_df['성별'].str.contains('여')]

# -----------------------------------------------------------
# 5. 히트맵 그리기 함수 (상하 배치에 맞춰 사이즈 조절)
# -----------------------------------------------------------
def draw_heatmap(data, title, cmap):
    df_pivot = data.pivot_table(index='암종', columns='발생연도', values=value_col)
    df_pivot = df_pivot.reindex(index=COMMON_CANCERS, columns=TARGET_YEARS, fill_value=0)

    # [핵심] 상하 배치를 위해 그래프의 가로 길이를 대폭 늘립니다 (10 -> 14)
    # 세로 길이도 데이터 양에 맞춰 적절히 조절 (8 -> 6)
    fig, ax = plt.subplots(figsize=(14, 6)) 
    sns.heatmap(df_pivot, cmap=cmap, linewidths=.5, ax=ax, cbar_kws={'label': value_col})
    
    ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel("연도", fontsize=12)
    ax.set_ylabel("암종", fontsize=12)
    
    return fig

# -----------------------------------------------------------
# 6. 화면 출력 (상하 배치 적용)
# -----------------------------------------------------------
# col1, col2 = st.columns(2) 코드를 삭제하고 순차적으로 그립니다.

st.write("---") # 구분선
st.subheader(f"👨 남성 {value_col}")
fig_male = draw_heatmap(df_male, f"남성 {data_option.split()[0]} 추이", "Blues")
st.pyplot(fig_male)

st.write("---") # 구분선
st.subheader(f"👩 여성 {value_col}")
fig_female = draw_heatmap(df_female, f"여성 {data_option.split()[0]} 추이", "Reds")
st.pyplot(fig_female)

st.caption("데이터 출처: 국립암센터 암발생 통계 정보, 국가별 암종별 사망률 통계")