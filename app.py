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
# 0. [핵심] 분석할 암종 리스트와 연도 범위 고정
# -----------------------------------------------------------
# 그래프의 Y축과 X축을 이 기준대로 '강제'로 맞춥니다.
TARGET_CANCERS = [
    "위암", "대장암", "폐암", "간암", "유방암", 
    "자궁경부암", "전립선암", "췌장암", "갑상선암", "백혈병"
]
TARGET_YEARS = list(range(1999, 2024)) # 1999년부터 2023년까지

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

# (1) 조발생률 데이터 로드
@st.cache_data
def load_incidence_data():
    filename = 'data_incidence.csv' # 영어 파일명 사용
    if not os.path.exists(filename):
        return None

    try:
        df = pd.read_csv(filename, encoding='euc-kr')
    except:
        df = pd.read_csv(filename, encoding='utf-8')

    # 연도 숫자 변환
    df = df[df['발생연도'].astype(str).str.isnumeric()]
    df['발생연도'] = df['발생연도'].astype(int)
    
    # 조발생률 데이터는 이미 이름이 짧으므로 필터링만 수행
    df = df[df['암종'].isin(TARGET_CANCERS)]
    df = df[df['연령군'] == '연령전체'] 

    return df

# (2) 사망률 데이터 로드 및 이름 매핑 (가장 중요!)
@st.cache_data
def load_death_data():
    filename = 'data_death.csv' # 영어 파일명 사용
    if not os.path.exists(filename):
        return None

    try:
        df = pd.read_csv(filename, encoding='euc-kr')
    except:
        df = pd.read_csv(filename, encoding='utf-8')

    # 한국 데이터만 필터링
    if '국가' in df.columns:
        df = df[df['국가'].str.contains('한국|대한민국', na=False)]

    # [핵심] 사망률 데이터의 긴 이름을 짧은 이름으로 변경하는 사전
    rename_map = {
        '위의 악성 신생물': '위암',
        '대장·직장·항문암': '대장암', # 또는 '대장암'이 데이터에 따라 다를 수 있음
        '기관·기관지·폐암': '폐암',
        '간 및 간내 담관암': '간암',
        '유방의 악성 신생물': '유방암',
        '자궁경부암': '자궁경부암',
        '전립선암': '전립선암', # 데이터 원본에 따라 '전립선의 악성 신생물'일 수도 있음. 확인 필요.
        '췌장암': '췌장암',     # '췌장의 악성 신생물' 등
        '갑상선암': '갑상선암',
        '백혈병': '백혈병',
        # 혹시 모를 변수 대응 (데이터 파일 내부 확인 결과 반영)
        '간암': '간암',
        '대장암': '대장암',
        '폐암': '폐암'
    }
    
    # '항목' 컬럼의 값을 위의 규칙대로 바꿈
    df['항목'] = df['항목'].replace(rename_map)

    # Wide -> Long 변환
    id_vars = ['성별', '항목'] 
    year_cols = [c for c in df.columns if '년' in str(c) or str(c).strip().isdigit()]
    
    df_melted = df.melt(id_vars=['성별', '항목'], value_vars=year_cols, 
                        var_name='발생연도', value_name='사망률')
    
    df_melted['발생연도'] = df_melted['발생연도'].astype(str).str.replace(' 년', '').str.strip()
    df_melted = df_melted[df_melted['발생연도'].str.isnumeric()]
    df_melted['발생연도'] = df_melted['발생연도'].astype(int)
    
    df_melted = df_melted.rename(columns={'항목': '암종'})
    df_melted['사망률'] = pd.to_numeric(df_melted['사망률'], errors='coerce').fillna(0)

    # 이름이 변경된 후, 우리가 원하는 암종만 남김
    df_melted = df_melted[df_melted['암종'].isin(TARGET_CANCERS)]

    return df_melted

# -----------------------------------------------------------
# 3. 데이터 로딩
# -----------------------------------------------------------
df_inc = load_incidence_data()
df_death = load_death_data()

# -----------------------------------------------------------
# 4. Streamlit 앱 레이아웃
# -----------------------------------------------------------
st.title('📊 암 발생 및 사망률 히트맵 분석')
st.markdown("데이터 종류를 변경해도 **X축(연도)**과 **Y축(암종)**은 고정됩니다.")

# 데이터 선택
data_option = st.selectbox(
    "확인할 지표를 선택하세요:",
    ["조발생률 (Incidence Rate)", "사망률 (Death Rate)"]
)

# 데이터 준비
if data_option.startswith("조발생률") and df_inc is not None:
    target_df = df_inc
    value_col = '조발생률'
    df_male = target_df[target_df['성별'] == '남자']
    df_female = target_df[target_df['성별'] == '여자']
    
elif data_option.startswith("사망률") and df_death is not None:
    target_df = df_death
    value_col = '사망률'
    df_male = target_df[target_df['성별'].str.contains('남')]
    df_female = target_df[target_df['성별'].str.contains('여')]
    
else:
    st.error("데이터 파일을 불러올 수 없습니다. (data_incidence.csv 또는 data_death.csv 확인 필요)")
    st.stop()

# -----------------------------------------------------------
# 5. 히트맵 그리기 함수 (완전 고정형)
# -----------------------------------------------------------
def draw_heatmap(data, title, cmap):
    # 피벗 테이블 생성
    df_pivot = data.pivot_table(index='암종', columns='발생연도', values=value_col)
    
    # [핵심] reindex를 사용하여 X축과 Y축을 강제로 고정
    # 데이터가 없으면 NaN이 되는데, 이를 0으로 채움
    df_pivot = df_pivot.reindex(index=TARGET_CANCERS, columns=TARGET_YEARS, fill_value=0)

    # 그래프 그리기
    fig, ax = plt.subplots(figsize=(10, 8)) # 가로세로 비율 조정
    sns.heatmap(df_pivot, cmap=cmap, linewidths=.5, ax=ax, cbar_kws={'label': value_col})
    
    ax.set_title(title, fontsize=15, fontweight='bold')
    ax.set_xlabel("연도", fontsize=12)
    ax.set_ylabel("암종", fontsize=12)
    
    return fig

# -----------------------------------------------------------
# 6. 화면 분할 및 그래프 출력
# -----------------------------------------------------------
col1, col2 = st.columns(2)

with col1:
    st.subheader(f"👨 남성 {value_col}")
    if not df_male.empty:
        fig_male = draw_heatmap(df_male, f"남성 {data_option.split()[0]} 추이", "Blues")
        st.pyplot(fig_male)
    else:
        st.warning("남성 데이터가 없습니다.")

with col2:
    st.subheader(f"👩 여성 {value_col}")
    if not df_female.empty:
        fig_female = draw_heatmap(df_female, f"여성 {data_option.split()[0]} 추이", "Reds")
        st.pyplot(fig_female)
    else:
        st.warning("여성 데이터가 없습니다.")

st.caption("데이터 출처: 국립암센터 암발생 통계 정보, 국가별 암종별 사망률 통계")