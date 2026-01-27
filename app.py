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
    system_name = platform.system()
    if system_name == 'Darwin': # Mac
        plt.rcParams['font.family'] = 'AppleGothic'
    elif system_name == 'Windows': # Windows
        plt.rcParams['font.family'] = 'Malgun Gothic'
    else: # Linux (Streamlit Cloud 등)
        plt.rcParams['font.family'] = 'NanumGothic'
    plt.rcParams['axes.unicode_minus'] = False

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