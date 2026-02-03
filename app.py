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
# 1. 한글 폰트 설정
# -----------------------------------------------------------
def set_korean_font():
    # 1. 프로젝트 폴더 내 NanumGothic.ttf 확인
    font_path = 'NanumGothic.ttf'
    if os.path.exists(font_path):
        fm.fontManager.addfont(font_path)
        font_name = fm.FontProperties(fname=font_path).get_name()
        plt.rcParams['font.family'] = font_name
    else:
        # 2. 시스템 폰트 사용
        system_name = platform.system()
        if system_name == 'Darwin': # Mac
            plt.rcParams['font.family'] = 'AppleGothic'
        elif system_name == 'Windows': # Windows
            plt.rcParams['font.family'] = 'Malgun Gothic'
        else: # Linux
            plt.rcParams['font.family'] = 'NanumGothic'
            
    plt.rcParams['axes.unicode_minus'] = False

set_korean_font()

# -----------------------------------------------------------
# 2. 데이터 불러오기 및 전처리 함수
# -----------------------------------------------------------

# (1) 조발생률 데이터 로드 (기존 파일)
@st.cache_data
def load_incidence_data():
    filename = '국립암센터_암발생 통계 정보_20260120.csv'
    if not os.path.exists(filename):
        return None

    try:
        df = pd.read_csv(filename, encoding='euc-kr')
    except:
        df = pd.read_csv(filename, encoding='utf-8')

    # 필요한 데이터 필터링
    # 1999~2023년 데이터만, 암종에서 합계 항목 제외
    df = df[df['발생연도'].astype(str).str.isnumeric()]
    df['발생연도'] = df['발생연도'].astype(int)
    
    # 제외할 암종
    exclude_cancer = ['모든암', '기타 암', '모든 암']
    df = df[~df['암종'].isin(exclude_cancer)]
    df = df[df['연령군'] == '연령전체'] # 연령전체 기준

    return df

# (2) 사망률 데이터 로드 (새로운 파일)
@st.cache_data
def load_death_data():
    filename = '국가별_연도별_암종별_사망률.csv'
    if not os.path.exists(filename):
        return None

    try:
        df = pd.read_csv(filename, encoding='euc-kr')
    except:
        df = pd.read_csv(filename, encoding='utf-8')

    # 전처리: '대한민국' 데이터만 필터링 (파일에 국가 컬럼이 있다고 가정)
    if '국가' in df.columns:
        df = df[df['국가'].str.contains('한국|대한민국', na=False)]

    # 가로형(Wide) 데이터를 세로형(Long)으로 변환 (Melt)
    # 컬럼 중 '1999 년', '2000 년' 등의 형식을 숫자로 변환해야 함
    id_vars = ['성별', '항목'] # 고정할 컬럼 (암종은 '항목' 컬럼에 있다고 가정)
    
    # 연도 컬럼만 추출 (숫자로 시작하는 컬럼 등)
    year_cols = [c for c in df.columns if '년' in str(c) or str(c).strip().isdigit()]
    
    # Melt 수행
    df_melted = df.melt(id_vars=['성별', '항목'], value_vars=year_cols, 
                        var_name='발생연도', value_name='사망률')
    
    # '1999 년' -> 1999 로 변환
    df_melted['발생연도'] = df_melted['발생연도'].astype(str).str.replace(' 년', '').str.strip()
    df_melted = df_melted[df_melted['발생연도'].str.isnumeric()]
    df_melted['발생연도'] = df_melted['발생연도'].astype(int)
    
    # 컬럼명 통일 (기존 코드와 호환되게)
    df_melted = df_melted.rename(columns={'항목': '암종'})
    
    # 데이터 형변환
    df_melted['사망률'] = pd.to_numeric(df_melted['사망률'], errors='coerce').fillna(0)

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
st.markdown("연도별(X축) 암종별(Y축) 추이를 색상으로 비교합니다.")

# (1) 옵션 선택 (드롭다운)
data_option = st.selectbox(
    "확인할 지표를 선택하세요:",
    ["조발생률 (Incidence Rate)", "사망률 (Death Rate)"]
)

# (2) 데이터 준비
if data_option.startswith("조발생률") and df_inc is not None:
    target_df = df_inc
    value_col = '조발생률'
    # 남녀 데이터 분리
    df_male = target_df[target_df['성별'] == '남자']
    df_female = target_df[target_df['성별'] == '여자']
    
elif data_option.startswith("사망률") and df_death is not None:
    target_df = df_death
    value_col = '사망률'
    # 파일의 성별 표기 확인 필요 ('남자'/'여자' 또는 '남성'/'여성')
    # 일반적인 포함 검색으로 처리
    df_male = target_df[target_df['성별'].str.contains('남')]
    df_female = target_df[target_df['성별'].str.contains('여')]
    
else:
    st.error("데이터 파일을 불러올 수 없습니다.")
    st.stop()

# -----------------------------------------------------------
# 5. 히트맵 그리기 함수
# -----------------------------------------------------------
def draw_heatmap(data, title, cmap):
    # 피벗 테이블 생성 (Index: 암종, Col: 연도, Value: 값)
    df_pivot = data.pivot_table(index='암종', columns='발생연도', values=value_col)
    
    # NaN 값 0으로 채우기
    df_pivot = df_pivot.fillna(0)
    
    # 암종(Y축)을 발생률/사망률 합계 순으로 정렬 (상위가 위로 오게)
    top_cancers = df_pivot.sum(axis=1).sort_values(ascending=False).index
    df_pivot = df_pivot.loc[top_cancers]

    # 그래프 그리기
    fig, ax = plt.subplots(figsize=(8, 10)) # 세로로 긴 형태
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
        # 남성은 파란색 계열 (Blues)
        fig_male = draw_heatmap(df_male, f"남성 {data_option.split()[0]} 추이", "Blues")
        st.pyplot(fig_male)
    else:
        st.warning("남성 데이터가 없습니다.")

with col2:
    st.subheader(f"👩 여성 {value_col}")
    if not df_female.empty:
        # 여성은 붉은색 계열 (Reds)
        fig_female = draw_heatmap(df_female, f"여성 {data_option.split()[0]} 추이", "Reds")
        st.pyplot(fig_female)
    else:
        st.warning("여성 데이터가 없습니다.")

# 데이터 출처 표시
st.caption("데이터 출처: 국립암센터 암발생 통계 정보, 국가별 암종별 사망률 통계")

'''
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import platform
import os

# -----------------------------------------------------------
# 1. 한글 폰트 설정
# -----------------------------------------------------------
def set_korean_font():
    # 폰트 파일 경로 (app.py와 같은 폴더에 NanumGothic.ttf 가 있어야 함)
    font_path = 'NanumGothic.ttf' 
    
    # 폰트 파일이 실제로 있는지 확인
    if os.path.exists(font_path):
        # 폰트 매니저에 폰트 추가
        fm.fontManager.addfont(font_path)
        # 폰트 이름 가져오기
        font_name = fm.FontProperties(fname=font_path).get_name()
        # Matplotlib의 기본 폰트로 설정
        plt.rcParams['font.family'] = font_name
        plt.rcParams['axes.unicode_minus'] = False # 마이너스 깨짐 방지
    else:
        # 폰트 파일이 없을 경우 에러 메시지 출력 대신 기본 설정 유지
        st.error("폰트 파일을 찾을 수 없습니다. NanumGothic.ttf 파일을 프로젝트 폴더에 넣어주세요.")

set_korean_font()

# -----------------------------------------------------------
# 2. 데이터 불러오기 및 전처리
# -----------------------------------------------------------
@st.cache_data
def load_data():
    filename = '국립암센터_암발생 통계 정보_20260120.csv'
    
    if not os.path.exists(filename):
        st.error(f"데이터 파일({filename})이 없습니다. 같은 폴더에 있는지 확인해주세요.")
        return pd.DataFrame()

    try:
        df = pd.read_csv(filename, encoding='euc-kr')
    except UnicodeDecodeError:
        df = pd.read_csv(filename, encoding='utf-8')

    # '1999-2023' 같은 구간 데이터 제외하고 정수형 연도만 남기기
    df = df[df['발생연도'].astype(str).str.isnumeric()]
    df['발생연도'] = df['발생연도'].astype(int)
    
    return df

df = load_data()

# -----------------------------------------------------------
# 3. Streamlit 앱 레이아웃
# -----------------------------------------------------------
st.title('📊 암 발생 데이터 인터랙티브 분석')

# (1) 영상 표시 섹션
st.header("1. 연도별 암 발생률 변화 (Bar Chart Race)")

# 파일명 (확장자 확인 필요: gif 권장)
video_file = 'cancer_race_fixed.mp4'

if os.path.exists(video_file):
    # 확장자에 따라 표시 방식 자동 선택
    if video_file.endswith('.gif'):
        st.image(video_file, caption='연도별 암 발생 순위 변화', use_container_width=True)
    else:
        st.video(video_file)
        st.caption('연도별 암 발생 순위 변화')
else:
    st.info(f"생성된 영상 파일({video_file})이 폴더에 있다면 이곳에 표시됩니다.")

st.markdown("---")

# (2) 인터랙티브 그래프 섹션
st.header("2. 데이터 상세 분석")
st.write("궁금한 변수를 선택하여 그래프를 그려보세요.")

if not df.empty:
    # --- 옵션 선택 영역 ---
    # 1행: X축, Y축 선택
    col1, col2 = st.columns(2)
    with col1:
        x_option = st.selectbox('X축 (분석 기준)', ['발생연도', '성별', '암종', '연령군'])
    with col2:
        y_option = st.selectbox('Y축 (데이터 값)', ['발생자수', '조발생률'])
    
    # 2행: 암종 필터링 (새로 추가된 기능)
    # 암종 리스트 생성 ('모든암'을 맨 앞으로)
    cancer_types = df['암종'].unique().tolist()
    if '모든암' in cancer_types:
        cancer_types.remove('모든암')
        cancer_types.sort()
        cancer_types.insert(0, '모든암')
    
    # X축이 '암종'일 때는 필터링이 필요 없으므로 비활성화(disabled=True)
    is_disabled = (x_option == '암종')
    
    selected_cancer = st.selectbox(
        '분석할 암종을 선택하세요 (X축이 암종일 경우 비활성화)', 
        cancer_types, 
        disabled=is_disabled
    )

    # -----------------------------------------------------------
    # 4. 그래프 그리기 로직 (업데이트됨)
    # -----------------------------------------------------------
    fig, ax = plt.subplots(figsize=(10, 6))
    current_year = df['발생연도'].max()
    
    # 필터링 공통 변수
    # 기존 코드의 '모든암' 대신 'selected_cancer' 변수를 사용합니다.
    
    # 4-1. X축: 발생연도 (시계열) -> 특정 암종의 연도별 변화
    if x_option == '발생연도':
        filtered_df = df[
            (df['성별'] == '남녀전체') & 
            (df['암종'] == selected_cancer) &  # [변경] 선택된 암종
            (df['연령군'] == '연령전체')
        ]
        ax.plot(filtered_df['발생연도'], filtered_df[y_option], marker='o', linewidth=2)
        ax.set_title(f"연도별 {y_option} 추이 ({selected_cancer})", fontsize=16)
        ax.grid(True, linestyle='--', alpha=0.5)

    # 4-2. X축: 성별 (막대) -> 특정 암종의 성별 비교
    elif x_option == '성별':
        filtered_df = df[
            (df['발생연도'] == current_year) & 
            (df['암종'] == selected_cancer) &  # [변경] 선택된 암종
            (df['연령군'] == '연령전체') & 
            (df['성별'] != '남녀전체')
        ]
        ax.bar(filtered_df['성별'], filtered_df[y_option], color=['skyblue', 'pink'], alpha=0.8)
        ax.set_title(f"{current_year}년 성별 {y_option} 비교 ({selected_cancer})", fontsize=16)

    # 4-3. X축: 암종 (가로 막대 Top 10) -> 암종 간 비교 (단일 필터링 무시)
    elif x_option == '암종':
        # 여기서는 selected_cancer를 쓰지 않고, 여러 암종을 비교합니다.
        filtered_df = df[
            (df['발생연도'] == current_year) & 
            (df['성별'] == '남녀전체') & 
            (df['연령군'] == '연령전체') & 
            (df['암종'] != '모든암') & (df['암종'] != '기타 암')
        ].sort_values(by=y_option, ascending=False).head(10)
        
        ax.barh(filtered_df['암종'], filtered_df[y_option], color='salmon', alpha=0.8)
        ax.invert_yaxis()
        ax.set_title(f"{current_year}년 암종별 {y_option} Top 10 (전체 암종 비교)", fontsize=16)

    # 4-4. X축: 연령군 (막대) -> 특정 암종의 연령별 분포
    elif x_option == '연령군':
        filtered_df = df[
            (df['발생연도'] == current_year) & 
            (df['성별'] == '남녀전체') & 
            (df['암종'] == selected_cancer) &  # [변경] 선택된 암종
            (df['연령군'] != '연령전체')
        ]
        ax.bar(filtered_df['연령군'], filtered_df[y_option], color='lightgreen', alpha=0.8)
        ax.set_title(f"{current_year}년 연령군별 {y_option} 분포 ({selected_cancer})", fontsize=16)
        plt.xticks(rotation=45)

    ax.set_xlabel(x_option)
    ax.set_ylabel(y_option)
    st.pyplot(fig)
    
    with st.expander("그래프 데이터 보기"):
        st.dataframe(filtered_df[['발생연도', '성별', '암종', '연령군', y_option]])

else:
    st.warning("데이터를 불러오지 못했습니다.")

'''