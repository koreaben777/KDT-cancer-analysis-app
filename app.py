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
# 0. 설정: 분석할 공통 암종 리스트 정의 (순서 고정)
# -----------------------------------------------------------
# 이 리스트에 있는 암만 분석하며, 그래프 Y축 순서도 이대로 고정됩니다.
TARGET_CANCERS = [
    "모든암", "위암", "대장암", "폐암", "간암", 
    "유방암", "자궁경부암", "전립선암", "췌장암", 
    "갑상선암", "백혈병"
]

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
    filename = '국립암센터_암발생 통계 정보_20260120.csv'
    if not os.path.exists(filename):
        return None

    try:
        df = pd.read_csv(filename, encoding='euc-kr')
    except:
        df = pd.read_csv(filename, encoding='utf-8')

    df = df[df['발생연도'].astype(str).str.isnumeric()]
    df['발생연도'] = df['발생연도'].astype(int)
    
    # 공통 암종만 필터링
    df = df[df['암종'].isin(TARGET_CANCERS)]
    df = df[df['연령군'] == '연령전체'] 

    return df

# (2) 사망률 데이터 로드 및 이름 매핑
@st.cache_data
def load_death_data():
    filename = '국가별_연도별_암종별_사망률.csv'
    if not os.path.exists(filename):
        return None

    try:
        df = pd.read_csv(filename, encoding='euc-kr')
    except:
        df = pd.read_csv(filename, encoding='utf-8')

    if '국가' in df.columns:
        df = df[df['국가'].str.contains('한국|대한민국', na=False)]

    # [핵심 수정] 사망률 데이터의 암종 이름을 조발생률 데이터와 맞춤
    rename_map = {
        '기관·기관지·폐암': '폐암',
        '대장·직장·항문암': '대장암',
        '간 및 간내 담관암': '간암', # 데이터에 따라 이름이 다를 수 있어 추가
        '위의 악성 신생물': '위암',
        '유방의 악성 신생물': '유방암',
        # 필요한 경우 매핑 추가
    }
    # replace는 부분 일치가 아니라 완전 일치일 때 동작하므로, 
    # 데이터의 정확한 명칭을 확인해야 하지만, 일반적인 매핑 적용
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

    # 공통 암종만 필터링
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
st.markdown("드롭다운을 변경해도 **X축(연도)**과 **Y축(암종)**은 고정됩니다.")

data_option = st.selectbox(
    "확인할 지표를 선택하세요:",
    ["조발생률 (Incidence Rate)", "사망률 (Death Rate)"]
)

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
    st.error("데이터 파일을 불러올 수 없습니다.")
    st.stop()

# -----------------------------------------------------------
# 5. 히트맵 그리기 함수 (Y축 고정)
# -----------------------------------------------------------
def draw_heatmap(data, title, cmap):
    # 피벗 테이블 생성
    df_pivot = data.pivot_table(index='암종', columns='발생연도', values=value_col)
    
    # NaN 값 0으로 채우기
    df_pivot = df_pivot.fillna(0)
    
    # [핵심 수정] Y축 순서를 TARGET_CANCERS 순서로 강제 고정 (데이터에 없는 암종은 제외)
    # 데이터에 존재하는 암종만 추려서 순서대로 정렬
    existing_cancers = [c for c in TARGET_CANCERS if c in df_pivot.index]
    df_pivot = df_pivot.reindex(existing_cancers)

    # 그래프 그리기
    fig, ax = plt.subplots(figsize=(8, 10))
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
        st.warning("데이터가 없습니다.")

with col2:
    st.subheader(f"👩 여성 {value_col}")
    if not df_female.empty:
        fig_female = draw_heatmap(df_female, f"여성 {data_option.split()[0]} 추이", "Reds")
        st.pyplot(fig_female)
    else:
        st.warning("데이터가 없습니다.")

st.caption("데이터 출처: 국립암센터 암발생 통계 정보, 국가별 암종별 사망률 통계")