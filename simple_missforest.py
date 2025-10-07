"""
간단한 MissForest 구현 - 함수 기반
- LightGBM 사용 (원본과 동일)
- 불필요한 validation 및 복잡한 기능 제거
- 함수로 바로 사용 가능
"""

import pandas as pd
import numpy as np
from lightgbm import LGBMClassifier, LGBMRegressor
from copy import deepcopy


def _identify_feature_types(X, categorical_features=None):
    """특성 타입 식별"""
    if categorical_features is not None:
        categorical = list(categorical_features)
    else:
        # 자동으로 범주형 특성 식별
        categorical = []
        for col in X.columns:
            if X[col].dtype == 'object' or X[col].dtype.name == 'category':
                categorical.append(col)
            elif X[col].dtype in ['int64', 'int32'] and X[col].nunique() <= 20:
                # 정수형이면서 고유값이 20개 이하면 범주형으로 간주
                categorical.append(col)
                
    numerical = [col for col in X.columns if col not in categorical]
    return categorical, numerical


def _compute_initial_imputations(X, categorical_features):
    """초기 대체값 계산"""
    initial_imputations = {}
    
    for col in X.columns:
        if col in categorical_features:
            # 범주형: 최빈값
            mode_vals = X[col].mode()
            if len(mode_vals) > 0:
                initial_imputations[col] = mode_vals.iloc[0]
            else:
                initial_imputations[col] = "unknown"
        else:
            # 수치형: 중앙값
            initial_imputations[col] = X[col].median()
            
    return initial_imputations


def _initial_impute(X, initial_imputations):
    """초기 대체 수행"""
    X_imputed = X.copy()
    for col in X.columns:
        X_imputed[col] = X_imputed[col].fillna(initial_imputations[col])
    return X_imputed


def _get_missing_indices(X):
    """결측치가 있는 인덱스들 반환"""
    missing_indices = {}
    for col in X.columns:
        missing_mask = X[col].isnull()
        if missing_mask.any():
            missing_indices[col] = X[missing_mask].index
    return missing_indices


def _calculate_difference(X_old, X_new, categorical_features):
    """두 데이터프레임 간 차이 계산 (조기 종료 판정용)"""
    if X_old is None:
        return float('inf')
        
    total_diff = 0
    n_features = 0
    
    for col in X_old.columns:
        if col not in categorical_features:
            # 수치형: 정규화된 RMSE
            old_vals = X_old[col].values
            new_vals = X_new[col].values
            if np.std(old_vals) > 0:
                rmse = np.sqrt(np.mean((old_vals - new_vals) ** 2))
                normalized_rmse = rmse / np.std(old_vals)
                total_diff += normalized_rmse
                n_features += 1
        else:
            # 범주형: 불일치 비율
            different_ratio = np.mean(X_old[col] != X_new[col])
            total_diff += different_ratio
            n_features += 1
            
    return total_diff / max(n_features, 1)


def missforest(X, categorical_features=None, max_iter=5, early_stopping=True, 
               verbose=True, random_state=None):
    """
    MissForest 알고리즘으로 결측치 대체
    
    Parameters
    ----------
    X : pd.DataFrame
        결측치가 있는 데이터
    categorical_features : list, optional
        범주형 특성 리스트. None이면 자동 식별
    max_iter : int, default=5
        최대 반복 횟수
    early_stopping : bool, default=True
        조기 종료 여부 (차이가 거의 없으면 중단)
    verbose : bool, default=True
        진행 상황 출력 여부
    random_state : int, optional
        랜덤 시드
        
    Returns
    -------
    pd.DataFrame
        결측치가 대체된 데이터
    """
    if not isinstance(X, pd.DataFrame):
        X = pd.DataFrame(X)
        
    X = X.copy()
    
    # 기본 검증
    if X.empty:
        raise ValueError("빈 데이터프레임입니다.")
        
    if X.isnull().all(axis=None):
        raise ValueError("모든 값이 결측치입니다.")
        
    # 특성 타입 식별
    categorical_features, numerical_features = _identify_feature_types(X, categorical_features)
    
    if verbose:
        print(f"범주형 특성 ({len(categorical_features)}개): {categorical_features}")
        print(f"수치형 특성 ({len(numerical_features)}개): {numerical_features}")
        print(f"전체 결측치 개수: {X.isnull().sum().sum()}")
    
    # 결측치가 없으면 그대로 반환
    if X.isnull().sum().sum() == 0:
        if verbose:
            print("결측치가 없습니다.")
        return X
        
    # 결측치 비율에 따라 컬럼 순서 정렬 (적은 것부터)
    missing_rates = X.isnull().sum() / len(X)
    column_order = missing_rates.sort_values().index
    X = X[column_order].copy()
    
    # LightGBM 모델 설정
    lgbm_params = {'verbosity': -1, 'linear_tree': True}
    if random_state is not None:
        lgbm_params['random_state'] = random_state
    
    classifier = LGBMClassifier(**lgbm_params)
    regressor = LGBMRegressor(**lgbm_params)
    
    # 초기 대체
    initial_imputations = _compute_initial_imputations(X, categorical_features)
    X_imputed = _initial_impute(X, initial_imputations)
    
    # 결측치 위치 저장
    missing_indices = _get_missing_indices(X)
    
    if verbose:
        print(f"결측치가 있는 특성: {list(missing_indices.keys())}")
    
    X_prev = None
    
    # 반복적 대체
    for iteration in range(max_iter):
        if verbose:
            print(f"\n=== 반복 {iteration + 1}/{max_iter} ===")
            
        # 각 특성에 대해 모델 학습 및 예측
        for col in missing_indices:
            if col not in missing_indices or len(missing_indices[col]) == 0:
                continue
                
            # 모델 선택
            if col in categorical_features:
                estimator = deepcopy(classifier)
            else:
                estimator = deepcopy(regressor)
            
            # 훈련 데이터 준비 (해당 컬럼 제외한 나머지)
            X_train = X_imputed.drop(columns=[col])
            y_train = X_imputed[col]
            
            try:
                # 모델 학습
                estimator.fit(X_train, y_train)
                
                # 결측치 예측
                X_missing = X_imputed.loc[missing_indices[col]].drop(columns=[col])
                if len(X_missing) > 0:
                    predictions = estimator.predict(X_missing)
                    X_imputed.loc[missing_indices[col], col] = predictions
                    
                if verbose:
                    print(f"  {col}: {len(missing_indices[col])}개 대체 완료")
                    
            except Exception as e:
                if verbose:
                    print(f"  {col}: 오류 발생 - {e}")
                continue
        
        # 조기 종료 검사
        if early_stopping and X_prev is not None:
            diff = _calculate_difference(X_prev, X_imputed, categorical_features)
            if verbose:
                print(f"  변화량: {diff:.6f}")
                
            if diff < 1e-4:  # 충분히 작은 변화
                if verbose:
                    print(f"수렴하여 조기 종료!")
                break
        
        X_prev = X_imputed.copy()
    
    if verbose:
        final_missing = X_imputed.isnull().sum().sum()
        print(f"\n완료! 최종 결측치 개수: {final_missing}")
        
    return X_imputed


# 사용 예시 및 테스트
if __name__ == "__main__":
    # 테스트 데이터 생성
    np.random.seed(42)
    
    # 샘플 데이터
    n_samples = 1000
    data = {
        'age': np.random.normal(35, 12, n_samples),
        'income': np.random.normal(50000, 20000, n_samples),
        'score': np.random.normal(75, 15, n_samples),
        'education': np.random.choice(['고졸', '대졸', '석사', '박사'], n_samples),
        'city': np.random.choice(['서울', '부산', '대구', '인천', '광주'], n_samples),
        'gender': np.random.choice(['남', '여'], n_samples)
    }
    
    df = pd.DataFrame(data)
    
    # 인위적으로 결측치 생성 (약 15% 정도)
    np.random.seed(123)
    n_missing = int(0.15 * len(df))
    
    for col in df.columns:
        missing_idx = np.random.choice(df.index, size=n_missing//len(df.columns), replace=False)
        df.loc[missing_idx, col] = np.nan
    
    print("=== 원본 데이터 결측치 현황 ===")
    print(df.isnull().sum())
    print(f"전체 결측치 비율: {df.isnull().sum().sum() / (len(df) * len(df.columns)) * 100:.1f}%")
    
    print("\n" + "="*50)
    
    # MissForest 적용 - 함수로 바로 사용
    categorical_features = ['education', 'city', 'gender']
    df_imputed = missforest(
        df, 
        categorical_features=categorical_features,
        max_iter=5, 
        early_stopping=True, 
        verbose=True,
        random_state=42
    )
    
    print("\n=== 대체 후 결과 ===")
    print("결측치 개수:")
    print(df_imputed.isnull().sum())
    
    print("\n기본 통계:")
    print(df_imputed.describe())
    
    print("\n범주형 특성 분포 (education):")
    print(df_imputed['education'].value_counts())

