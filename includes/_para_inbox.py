import os
import yaml
from IPython.display import HTML

def find_unclassified_posts(root_dir='posts'):
    unclassified = []
    for root, _, files in os.walk(root_dir):
        for file in files:
            if not file.startswith("index") and file.endswith(".qmd"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if '---' in content:
                            _, fm, _ = content.split('---', 2)
                            metadata = yaml.safe_load(fm)
                            # projects나 area_resource가 없는 파일만 선택
                            if not metadata.get('projects') and not metadata.get('area_resource'):
                                unclassified.append({
                                    'title': metadata.get('title', 'Untitled'),
                                    'date': metadata.get('date', 'No date'),
                                    'description': metadata.get('description', 'No description'),
                                    'path': file_path
                                })
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
    return sorted(unclassified, key=lambda x: str(x['date']), reverse=True)

unclassified = find_unclassified_posts()

# HTML 테이블 생성
html_table = f'<h3 class="content-title">분류되지 않은 노트들 ({len(unclassified)})</h3>'
if unclassified:
    html_table += f"""
    <table class="table">
        <thead>
            <tr>
                <th>Title</th>
                <th>Date</th>
                <th>Description</th>
            </tr>
        </thead>
        <tbody>
    """
    for post in unclassified:
        html_table += f"""
            <tr>
                <td><a href="{post['path']}">{post['title']}</a></td>
                <td>{post['date']}</td>
                <td>{post['description']}</td>
            </tr>
        """
    html_table += """
        </tbody>
    </table>
    """
else:
    html_table += f"""
        <p style="margin-top: 1em;">분류되지 않은 노트가 없습니다.</p>
    """
display(HTML(html_table))
