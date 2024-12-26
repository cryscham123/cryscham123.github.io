import os
import yaml
from IPython.display import HTML
from datetime import datetime

def find_posts(posts_dir):
    target = []

    for root, _, files in os.walk(posts_dir):
        for file in files:
            if file.startswith("index") and file.endswith(".qmd"):
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    try:
                        lines = f.readlines()
                        if lines[0].strip() == "---":
                            yaml_end = lines[1:].index("---\n") + 1
                            metadata = yaml.safe_load("".join(lines[1:yaml_end]))
                            if target_func(metadata):
                                target.append({
                                    "title": metadata.get("title", "Untitled"),
                                    "date": metadata.get("start_date", "Unknown"),
                                    "end_date": metadata.get("end_date"),
                                    "status": metadata.get("status"),
                                    "tags": metadata.get("tags", []),
                                    "description": metadata.get("description", ""),
                                    "path": file_path
                                })

                    except Exception as e:
                        print(f"Error reading {file_path}: {e}")

    return target

def sort_post(posts):
    status_priority = {
        'before-start': 0,
        'on-going': 1,
        'failed': 2,
        'completed': 3
    }
    def get_days_remaining(post):
        end_date = post.get('end_date')
        if not end_date:
            return float('inf')
        try:
            end = datetime.strptime(str(end_date), "%Y-%m-%d")
            return (end - datetime.now()).days
        except:
            return float('inf')
    posts.sort(key=lambda x: (
        status_priority.get(x.get('status', 'before-start'), 999),
        get_days_remaining(x)
    ))

    return posts

target_directory = "posts"

posts = sort_post(find_posts(target_directory))

def calculate_days_left(end_date):
    if not end_date:
        return ('No end date', 'days-left-nodate')
    try:
        end = datetime.strptime(str(end_date), "%Y-%m-%d")
        days_left = (end - datetime.now()).days
        if days_left > 0:
            return (f"{days_left} days left", 'days-left-remaining')
        else:
            return ('Overdue', 'days-left-overdue')
    except:
        return ('Invalid date', 'days-left-invalid')

if posts:
    html_content = """
    <div class="project-cards">
    """
    for post in posts:
        days_left, days_left_class = calculate_days_left(post.get('end_date'))
        tags = post.get('tags', [])
        if isinstance(tags, str):
            tags = [tags]
        html_content += f"""
        <a href="{post['path']}" style="text-decoration: none;">
            <div class="project-card">
                <div class="project-title">
                    <span>{post['title']}</span>
                    <span class="status-badge status-{post['status']}">{post['status']}</span>
                </div>
                <div class="project-dates">
                    Started: {post.get('date', 'Unknown')}
                    <br>
                    <span class="days-left {days_left_class}">{days_left}</span>
                </div>
                <div class="project-tags">
                    {' '.join(f'<span class="category-tag">{cat}</span>' for cat in tags)}
                </div>
                <div class="project-description">{post.get('description', 'No description available')}</div>
            </div>
        </a>
        """
    
    html_content += "</div>"
    display(HTML(html_content))
else:
    display(HTML("<p>No ongoing posts found.</p>"))
