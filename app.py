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
# 0. [핵심] 분석할 공통 암종 리스트 (순서 고정)
# -----------------------------------------------------------
# 두 데이터 파일에서 공통적으로 추출 가능한 9개 주요 암종입니다.
COMMON_CANCERS = [
    "위암", "대장암", "폐암", "간암", "유방암", 
    "자궁경부암", "전립선암", "췌장암", "백혈병"
]
# 연도 범위 고정 (1999 ~ 2023)
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

# (1) 조발생률 데이터 로드
@st.cache_data
def load_incidence_data():
    filename = 'data_incidence.csv'
    if not os.path.exists(filename):
        return None

    try:
        df = pd.read_csv(filename, encoding='euc-kr')
    except:
        df = pd.read_csv(filename, encoding='utf-8')

    # 연도 전처리
    df = df[df['발생연도'].astype(str).str.isnumeric()]
    df['발생연도'] = df['발생연도'].astype(int)
    
    # 필요한 컬럼만 선택
    # 조발생률 데이터는 이미 이름이 깔끔하므로(위암, 간암 등) 바로 필터링합니다.
    df = df[df['암종'].isin(COMMON_CANCERS)]
    df = df[df['연령군'] == '연령전체'] 

    return df

# (2) 사망률 데이터 로드 (여기가 수정의 핵심입니다)
@st.cache_data
def load_death_data():
    filename = 'data_death.csv'
    if not os.path.exists(filename):
        return None

    try:
        df = pd.read_csv(filename, encoding='euc-kr')
    except:
        df = pd.read_csv(filename, encoding='utf-8')

    # 1. 국가 필터링 (한국)
    if '국가' in df.columns:
        df = df[df['국가'].str.contains('한국|대한민국', na=False)]

    # 2. [중요] 암종 이름 매핑 사전 정의
    # CSV 파일에 적힌 복잡한 이름을 우리가 원하는 단순한 이름으로 바꿉니다.
    mapping_dict = {
        '위의 악성 신생물': '위암',
        '대장·직장·항문암': '대장암',
        '기관·기관지·폐암': '폐암',
        '간 및 간내 담관암': '간암',
        '유방의 악성 신생물': '유방암',
        '자궁경부암': '자궁경부암',
        '전립선암': '전립선암',
        '췌장암': '췌장암',
        '백혈병': '백혈병',
        # 혹시 모를 변수 대응 (이미 짧은 이름인 경우)
        '위암': '위암', '대장암': '대장암', '폐암': '폐암', '간암': '간암',
        '유방암': '유방암'
    }

    # 3. 매핑 적용
    # map 함수를 사용하여 사전에 없는 암종은 NaN(결측치) 처리 후 제거합니다.
    df['암종_표준'] = df['항목'].map(mapping_dict)
    df = df.dropna(subset=['암종_표준']) # 사전에 정의되지 않은 기타 암들은 제거

    # 4. Wide -> Long 변환
    id_vars = ['성별', '암종_표준'] # 바뀐 이름('암종_표준')을 기준으로 사용
    year_cols = [c for c in df.columns if '년' in str(c) or str(c).strip().isdigit()]
    
    df_melted = df.melt(id_vars=id_vars, value_vars=year_cols, 
                        var_name='발생연도', value_name='사망률')
    
    # 5. 연도 전처리
    df_melted['발생연도'] = df_melted['발생연도'].astype(str).str.replace(' 년', '').str.strip()
    df_melted = df_melted[df_melted['발생연도'].str.isnumeric()]
    df_melted['발생연도'] = df_melted['발생연도'].astype(int)
    
    # 6. 컬럼명 정리
    df_melted = df_melted.rename(columns={'암종_표준': '암종'})
    df_melted['사망률'] = pd.to_numeric(df_melted['사망률'], errors='coerce').fillna(0)

    # 7. [중요] 데이터 집계 (Aggregation)
    # 이름을 바꾸면서 혹시라도 중복된 행이 생길 경우 수치를 합칩니다.
    df_final = df_melted.groupby(['발생연도', '성별', '암종'], as_index=False)['사망률'].sum()

    return df_final

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

# 드롭다운
data_option = st.selectbox(
    "확인할 지표를 선택하세요:",
    ["조발생률 (Incidence Rate)", "사망률 (Death Rate)"]
)

# 데이터 선택 로직
if data_option.startswith("조발생률") and df_inc is not None:
    target_df = df_inc
    value_col = '조발생률'
    # 성별 필터링
    df_male = target_df[target_df['성별'] == '남자']
    df_female = target_df[target_df['성별'] == '여자']
    
elif data_option.startswith("사망률") and df_death is not None:
    target_df = df_death
    value_col = '사망률'
    # 성별 필터링 (포함 검색)
    df_male = target_df[target_df['성별'].str.contains('남')]
    df_female = target_df[target_df['성별'].str.contains('여')]
    
else:
    st.error("데이터 파일을 불러올 수 없습니다. (파일명: data_incidence.csv, data_death.csv)")
    st.stop()

# -----------------------------------------------------------
# 5. 히트맵 그리기 함수 (강제 고정 방식)
# -----------------------------------------------------------
def draw_heatmap(data, title, cmap):
    # 피벗 테이블 생성
    df_pivot = data.pivot_table(index='암종', columns='발생연도', values=value_col)
    
    # [핵심] reindex를 통해 무조건 지정된 순서와 항목만 표시
    # 데이터가 없으면 fill_value=0 으로 채워서 흰색(또는 가장 연한 색)으로 표시
    df_pivot = df_pivot.reindex(index=COMMON_CANCERS, columns=TARGET_YEARS, fill_value=0)

    # 그래프 그리기
    fig, ax = plt.subplots(figsize=(10, 8)) 
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
    # 데이터가 비어있어도 프레임은 그려야 하므로 조건문 위치 조정
    fig_male = draw_heatmap(df_male, f"남성 {data_option.split()[0]} 추이", "Blues")
    st.pyplot(fig_male)

with col2:
    st.subheader(f"👩 여성 {value_col}")
    fig_female = draw_heatmap(df_female, f"여성 {data_option.split()[0]} 추이", "Reds")
    st.pyplot(fig_female)

st.caption("데이터 출처: 국립암센터 암발생 통계 정보, 국가별 암종별 사망률 통계")