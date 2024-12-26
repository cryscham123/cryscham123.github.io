import os
import yaml
from collections import defaultdict

def get_categories_stats(root_dir='posts'):
    # 카테고리별 통계와 문서 목록을 저장할 딕셔너리
    categories_stats = defaultdict(lambda: {
        'projects': 0, 
        'notes': 0,
        'project_list': [],
        'note_list': []
    })
    
    # 모든 .qmd 파일 순회
    for root, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith('.qmd'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if '---' in content:
                            _, fm, _ = content.split('---', 2)
                            metadata = yaml.safe_load(fm)
                            
                            categories = metadata.get('categories', [])
                            if isinstance(categories, str):
                                categories = [categories]
                            
                            is_project = file.startswith('index')

                            title = metadata.get('title', os.path.basename(file_path))
                            doc_categories = metadata.get('categories', [])
                            if isinstance(doc_categories, str):
                                doc_categories = [doc_categories]
                            doc_info = {
                                'title': title,
                                'path': file_path,
                                'categories': ', '.join(doc_categories)
                            }

                            for category in categories:
                                if context == 'area' and category not in area:
                                    continue
                                if context == 'resource' and category in area:
                                    continue
                                if is_project:
                                    categories_stats[category]['projects'] += 1
                                    categories_stats[category]['project_list'].append(doc_info)
                                else:
                                    categories_stats[category]['notes'] += 1
                                    categories_stats[category]['note_list'].append(doc_info)
                            
                                    
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
    
    return categories_stats

# 카테고리 통계 가져오기
categories_stats = get_categories_stats()

# 페이지네이션 설정
ITEMS_PER_PAGE = 10
total_items = len(categories_stats)
total_pages = (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
sorted_categories = sorted(
    categories_stats.items(),
    key=lambda x: (x[1]['projects'] + x[1]['notes']),
    reverse=True
)

# HTML 생성
html_content = """
<script>
function changePage(page) {
    const rows = document.querySelectorAll('.category-row');
    const pagination = document.querySelector('.pagination');
    const startIdx = (page - 1) * """ + str(ITEMS_PER_PAGE) + """;
    const endIdx = startIdx + """ + str(ITEMS_PER_PAGE) + """;
    
    rows.forEach((row, idx) => {
        if (idx >= startIdx && idx < endIdx) {
            row.style.display = 'table-row';
        } else {
            row.style.display = 'none';
        }
    });
    
    const buttons = pagination.querySelectorAll('button');
    buttons.forEach(button => {
        if (button.textContent == page) {
            button.classList.add('active');
        } else {
            button.classList.remove('active');
        }
    });
}

function showModal(categoryId) {
    const modal = document.getElementById('modal-' + categoryId);
    modal.style.display = 'block';
    document.body.style.overflow = 'hidden';
}

function closeModal(categoryId) {
    const modal = document.getElementById('modal-' + categoryId);
    modal.style.display = 'none';
    document.body.style.overflow = 'auto';
}

// ESC 키로 모달 닫기
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            modal.style.display = 'none';
        });
        document.body.style.overflow = 'auto';
    }
});
</script>

<table class="category-table">
    <thead>
        <tr>
            <th>Category</th>
            <th>Projects</th>
            <th>Notes</th>
            <th>Total</th>
        </tr>
    </thead>
    <tbody>
"""

# 카테고리별 행 생성
for idx, (category, counts) in enumerate(sorted_categories):
    total = counts['projects'] + counts['notes']
    display_style = 'table-row' if idx < ITEMS_PER_PAGE else 'none'
    
    html_content += f"""
        <tr class="category-row" style="display: {display_style}" onclick="showModal('{idx}')">
            <td>{category}</td>
            <td>{counts['projects']}</td>
            <td>{counts['notes']}</td>
            <td>{total}</td>
        </tr>
    """
    
    # 모달 콘텐츠 생성
    html_content += f"""
    <div id="modal-{idx}" class="modal">
        <div class="modal-content">
            <span class="close-button" onclick="closeModal('{idx}')">&times;</span>
            <h3>{category}</h3>
            <div class="document-section">
                <h4>만드는 중. 자꾸 에러가 나요. esc 누르면 나가짐.</h4>
                <!--<table class="modal-table">-->
                <!--    <thead>-->
                <!--        <tr>-->
                <!--            <th>Title</th>-->
                <!--            <th>Categories</th>-->
                <!--        </tr>-->
                <!--    </thead>-->
                <!--    <tbody>-->
                <!--        {''.join(f"""-->
                <!--        <tr>-->
                <!--            <td><a href="{doc['path']}">{doc['title']}</a></td>-->
                <!--            <td>{doc['categories']}</td>-->
                <!--        </tr>-->
                <!--        """ for doc in counts['project_list'])}-->
                <!--    </tbody>-->
                <!--</table>-->
                <!---->
                <!--<h4>Notes ({counts['notes']})</h4>-->
                <!--<table class="modal-table">-->
                <!--    <thead>-->
                <!--        <tr>-->
                <!--            <th>Title</th>-->
                <!--            <th>Categories</th>-->
                <!--        </tr>-->
                <!--    </thead>-->
                <!--    <tbody>-->
                <!--        {''.join(f"""-->
                <!--        <tr>-->
                <!--            <td><a href="{doc['path']}">{doc['title']}</a></td>-->
                <!--            <td>{doc['categories']}</td>-->
                <!--        </tr>-->
                <!--        """ for doc in counts['note_list'])}-->
                <!--    </tbody>-->
                <!--</table>-->
            </div>
        </div>
    </div>
    """

html_content += """
    </tbody>
</table>
<div class="pagination">
"""

# 페이지네이션 버튼 생성
for page in range(1, total_pages + 1):
    active_class = 'active' if page == 1 else ''
    html_content += f"""
    <button onclick="changePage({page})" class="{active_class}">{page}</button>
    """

html_content += """
</div>
"""

from IPython.display import HTML
display(HTML(html_content))
