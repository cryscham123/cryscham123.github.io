import os
import yaml
from IPython.display import HTML

def find_posts(posts_dir):
    target = []

    for root, _, files in os.walk(posts_dir):
        for file in files:
            if file == "index.qmd":
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    try:
                        lines = f.readlines()
                        if lines[0].strip() == "---":
                            yaml_end = lines[1:].index("---\n") + 1
                            metadata = yaml.safe_load("".join(lines[1:yaml_end]))
                            target.append({
                                "title": metadata.get("title", "Untitled"),
                                "date": metadata.get("start_date", "Unknown"),
                                "end_date": metadata.get("end_date"),
                                "status": metadata.get("status"),
                                "tags": metadata.get("tags", []),
                                "description": metadata.get("description", ""),
                                "path": os.path.relpath(root, file) + "/"
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
    posts.sort(key=lambda x: (
        status_priority.get(x.get('status', 'before-start'), 999),
        str(x.get('end_date', '9999-12-31'))  # end_date가 없는 경우 가장 마지막으로
    ))
    return posts

posts = sort_post(find_posts(target_directory))
