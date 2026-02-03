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
# 두 데이터셋을 매핑하여 아래 이름으로 통일합니다.
# 순서는 한국인 다빈도 암 순서를 고려하여 정렬했습니다.
COMMON_CANCERS = [
    "위암", "대장암", "폐암", "간암", "유방암", 
    "자궁경부암", "전립선암", "췌장암", "백혈병", 
    "방광암", "난소암"
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

# (1) 조발생률 데이터 로드 및 매핑
@st.cache_data
def load_incidence_data():
    filename = 'data_incidence.csv'
    if not os.path.exists(filename):
        return None

    try:
        df = pd.read_csv(filename, encoding='euc-kr')
    except:
        df = pd.read_csv(filename, encoding='utf-8')

    # 연도 숫자 변환
    df = df[df['발생연도'].astype(str).str.isnumeric()]
    df['발생연도'] = df['발생연도'].astype(int)
    
    # [수정] 조발생률 데이터의 '부위명'을 '표준 암종명'으로 변경
    # 실제 데이터 확인 결과: '위', '간', '폐', '대장' 등으로 되어 있음
    mapping_inc = {
        '위': '위암',
        '대장': '대장암',
        '폐': '폐암',
        '간': '간암',
        '유방': '유방암',
        '자궁경부': '자궁경부암',
        '전립선': '전립선암',
        '췌장': '췌장암',
        '백혈병': '백혈병',   # 그대로
        '방광': '방광암',
        '난소': '난소암',
        # 혹시 모를 예외 처리
        '갑상선': '갑상선암' 
    }
    
    # 매핑 적용 (사전에 없는 값은 NaN이 됨)
    df['암종_표준'] = df['암종'].map(mapping_inc)
    
    # 매핑된 암종만 남기고 제거
    df = df.dropna(subset=['암종_표준'])
    
    # 필요한 데이터만 필터링 (연령전체)
    df = df[df['연령군'] == '연령전체'] 
    
    return df

# (2) 사망률 데이터 로드 및 매핑
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

    # 2. [수정] 사망률 데이터의 '긴 이름'을 '표준 암종명'으로 변경
    # 실제 데이터 확인 결과: '위암', '대장·직장·항문암', '기관·기관지·폐암' 등
    mapping_death = {
        '위암': '위암',
        '대장·직장·항문암': '대장암',
        '기관·기관지·폐암': '폐암',
        '간암': '간암',
        '여성 유방암': '유방암', # 사망률 데이터엔 '여성 유방암'으로 표기됨
        '자궁경부암': '자궁경부암',
        '전립선암': '전립선암',
        '췌장암': '췌장암',
        '백혈병': '백혈병',
        '방광암': '방광암',
        '난소암': '난소암'
    }

    # 매핑 적용
    df['암종_표준'] = df['항목'].map(mapping_death)
    df = df.dropna(subset=['암종_표준']) # 매핑 안된 항목 제거

    # 3. Wide -> Long 변환
    id_vars = ['성별', '암종_표준'] # 표준 이름 사용
    year_cols = [c for c in df.columns if '년' in str(c) or str(c).strip().isdigit()]
    
    df_melted = df.melt(id_vars=id_vars, value_vars=year_cols, 
                        var_name='발생연도', value_name='사망률')
    
    # 연도 전처리
    df_melted['발생연도'] = df_melted['발생연도'].astype(str).str.replace(' 년', '').str.strip()
    df_melted = df_melted[df_melted['발생연도'].str.isnumeric()]
    df_melted['발생연도'] = df_melted['발생연도'].astype(int)
    
    # 컬럼명 정리
    df_melted = df_melted.rename(columns={'암종_표준': '암종'}) # 이제 '암종' 컬럼은 표준 이름을 가짐
    df_melted['사망률'] = pd.to_numeric(df_melted['사망률'], errors='coerce').fillna(0)

    # 4. 데이터 집계 (중복 방지)
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
    # 조발생률 데이터의 '암종_표준' 컬럼이 위에서 '암종' 컬럼을 대체하지 않았으므로, 
    # '암종_표준' 컬럼을 사용하거나 load함수에서 이름을 바꿨어야 함. 
    # -> 위 load_incidence_data에서 '암종_표준'을 만들었으므로 이를 기준으로 사용해야 함.
    # 안전하게 여기서 '암종' 컬럼을 '암종_표준'으로 교체
    target_df['암종'] = target_df['암종_표준'] 
    
    df_male = target_df[target_df['성별'] == '남자']
    df_female = target_df[target_df['성별'] == '여자']
    
elif data_option.startswith("사망률") and df_death is not None:
    target_df = df_death
    value_col = '사망률'
    # 사망률 데이터는 이미 load 함수에서 '암종' 컬럼으로 정리해서 리턴함
    df_male = target_df[target_df['성별'].str.contains('남')]
    df_female = target_df[target_df['성별'].str.contains('여')]
    
else:
    st.error("데이터 파일을 불러올 수 없습니다.")
    st.stop()

# -----------------------------------------------------------
# 5. 히트맵 그리기 함수 (강제 고정 방식)
# -----------------------------------------------------------
def draw_heatmap(data, title, cmap):
    # 피벗 테이블 생성
    df_pivot = data.pivot_table(index='암종', columns='발생연도', values=value_col)
    
    # [핵심] COMMON_CANCERS 순서로 인덱스 강제 재설정 (데이터 없으면 0으로 채움)
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
    fig_male = draw_heatmap(df_male, f"남성 {data_option.split()[0]} 추이", "Blues")
    st.pyplot(fig_male)

with col2:
    st.subheader(f"👩 여성 {value_col}")
    fig_female = draw_heatmap(df_female, f"여성 {data_option.split()[0]} 추이", "Reds")
    st.pyplot(fig_female)

st.caption("데이터 출처: 국립암센터 암발생 통계 정보, 국가별 암종별 사망률 통계")