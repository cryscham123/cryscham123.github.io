import yaml
from IPython.display import HTML

def get_yaml_metadata(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        if content.startswith('---'):
            _, fm, _ = content.split('---', 2)
            return yaml.safe_load(fm)
    return {}

meta = get_yaml_metadata("index.qmd")

start_date_str = meta.get('start_date')
end_date_str = meta.get('end_date')

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
    border-bottom: 1px solid #e9ecef;
    margin-bottom: 1rem;
    padding-bottom: 1rem;
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
    width: 0%;
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
    <div class="status-badge">{meta.get('status', 'completed').upper()}</div>
    
    <div class="date-info">
        <div>시작일: {meta.get('start_date', '미정')}</div>
        <div>종료일: {meta.get('end_date', '미정')}</div>
    </div>
    <div id="progress-section">
        <div class="progress-container">
            <div class="progress-bar" style="width: 0%"></div>
        </div>
        <div class="progress-text">계산 중...</div>
    </div>
    <script>
    document.addEventListener('DOMContentLoaded', function() {{
        const startDate = '{start_date_str}';
        const endDate = '{end_date_str}';
        const progressBar = document.querySelector('.progress-bar');
        const progressText = document.querySelector('.progress-text');
        const progressSection = document.getElementById('progress-section');
        
        if (startDate && endDate) {{
            try {{
                const start = new Date(startDate);
                const end = new Date(endDate);
                const today = new Date();
                const totalDays = Math.floor((end - start) / (1000 * 60 * 60 * 24));
                const daysPassed = Math.max(Math.floor((today - start) / (1000 * 60 * 60 * 24)), 0);
                const daysLeft = Math.max(Math.floor((end - today) / (1000 * 60 * 60 * 24)), 0);
                let progress = 0;
                if (totalDays > 0) {{
                    progress = Math.min(Math.max((daysPassed / totalDays * 100), 0), 100);
                }}
                progressBar.style.width = `${{progress}}%`;
                progressText.textContent = `진행률: ${{progress.toFixed(1)}}% (${{daysPassed}}일 경과 / ${{daysLeft}}일 남음)`;
            }} catch (e) {{
                progressSection.innerHTML = '<div>날짜 형식이 올바르지 않습니다.</div>';
            }}
        }} else {{
            progressSection.innerHTML = '<div>일정이 설정되지 않았습니다.</div>';
        }}
    }});
    </script>
    <div class="categories-container">
        {''.join([f'<span class="category-tag">{cat}</span>' for cat in meta.get('tags', [])])}
    </div>
</div>
"""

display(HTML(html_content))
