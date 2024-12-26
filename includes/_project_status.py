from datetime import datetime
import pandas as pd
import yaml
from IPython.display import HTML

def get_yaml_metadata(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        if content.startswith('---'):
            _, fm, _ = content.split('---', 2)
            return yaml.safe_load(fm)
    return {}

meta = get_yaml_metadata(target)

# 날짜 정보 가져오기 및 처리
start_date_str = meta.get('start_date')
end_date_str = meta.get('end_date')
today = datetime.now()

# 시작일과 종료일이 모두 있는 경우에만 진행률 계산
if start_date_str and end_date_str:
    try:
        start_date = datetime.strptime(str(start_date_str), '%Y-%m-%d')
        end_date = datetime.strptime(str(end_date_str), '%Y-%m-%d')
        total_days = (end_date - start_date).days
        days_passed = (today - start_date).days if today > start_date else 0
        days_left = (end_date - today).days if today < end_date else 0
        progress = min(max((days_passed / total_days * 100), 0), 100) if total_days > 0 else 0
    except ValueError:
        start_date = end_date = None
        total_days = days_passed = days_left = progress = 0
else:
    start_date = end_date = None
    total_days = days_passed = days_left = progress = 0

# 상태별 색상
status_colors = {
    'before-start': '#f1c40f',
    'on-going': '#2ecc71',
    'completed': '#495057',
    'failed': '#e74c3c'
}

html_content = f"""
<style>
.project-info {{
    background: #f8f9fa;
    border-radius: 8px;
    padding: 1.5rem;
    margin-bottom: 2rem;
}}

.date-info {{
    display: flex;
    justify-content: space-between;
    margin-bottom: 1rem;
}}

.progress-container {{
    background-color: #e9ecef;
    border-radius: 4px;
    padding: 3px;
    margin: 1rem 0;
}}

.progress-bar {{
    background-color: {status_colors[meta['status']]};
    width: {progress}%;
    height: 20px;
    border-radius: 2px;
    transition: width 0.5s ease-in-out;
}}

.status-badge {{
    display: inline-block;
    padding: 0.25rem 0.75rem;
    border-radius: 4px;
    color: white;
    background-color: {status_colors[meta['status']]};
    margin-bottom: 1rem;
}}

.categories-container {{
    margin-top: 1rem;
}}

.category-tag {{
    display: inline-block;
    padding: 0.25rem 0.75rem;
    background-color: #e9ecef;
    border-radius: 4px;
    margin-right: 0.5rem;
    margin-bottom: 0.5rem;
    font-size: 0.9rem;
    color: #495057;
}}
</style>

<div class="project-info">
    <div class="status-badge">{meta['status'].upper()}</div>
    
    <div class="date-info">
        <div>시작일: {meta.get('start_date', '미정')}</div>
        <div>종료일: {meta.get('end_date', '미정')}</div>
    </div>
    
    {f"""
    <div class="progress-container">
        <div class="progress-bar"></div>
    </div>
    
    <div>진행률: {progress:.1f}% ({days_passed}일 경과 / {days_left}일 남음)</div>
    """ if start_date and end_date else '<div>일정이 설정되지 않았습니다.</div>'}
    
    <div class="categories-container">
        {''.join([f'<span class="category-tag">{cat}</span>' for cat in meta['categories']])}
    </div>
</div>
"""

display(HTML(html_content))
