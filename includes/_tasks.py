import os
import yaml
from IPython.display import HTML

def find_qmd_by_title(directory, target_title):
    for root, _, files in os.walk(directory):
        for file in files:
            if file == index.qmd:
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if content.startswith('---'):
                            _, front_matter, _ = content.split('---', 2)
                            metadata = yaml.safe_load(front_matter)
                            if metadata.get('title') == target_title:
                                return file_path, metadata.get('status', 'on-going')
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
                    continue
    return None, None

def generate_tasks_html(tasks, base_dir="posts"):
    html_content = """
    <style>
    .tasks-list {
        list-style-type: none;
        padding-left: 0;
    }
    .task-item {
        margin: 4px 0;
        padding: 4px 0;
    }
    .task-main {
        display: flex;
        align-items: center;
    }
    .task-detail {
        padding: 4px 0 0 0;
        opacity: 0.7;
    }
    .task-checkbox {
        margin-right: 8px;
        width: 16px;
        height: 16px;
        cursor: default;
    }
    .task-checkbox.failed:checked {
        accent-color: #cf222e;
    }
    .task-link {
        text-decoration: none;
        flex-grow: 1;
    }
    .task-name {
        font-size: 1em;
    }
    .task-name.clickable {
        color: #0969da;
        cursor: pointer;
    }
    .task-name.completed {
        text-decoration: line-through;
    }
    .task-name.failed {
        color: #cf222e;
        text-decoration: line-through;
    }
    .task-name.non-clickable {
        color: #57606a;
    }
    .task-detail {
        margin-left: 24px;
        font-size: 0.9em;
        color: #57606a;
        font-style: italic;
    }
    </style>
    <ul class="tasks-list">
    """
    for task in tasks:
        name = task.get('name', '')
        directory = task.get('directory', '')
        href = task.get('link', '')
        checked = 'checked' if task.get('status', '') == 'completed' else ''
        checkbox_class = task.get('status', '')
        name_class = "clickable" if href != '' or directory != '' else "non-clickable"
        name_class += ' ' + task.get('status', '')
        if directory:
            for root, _, files in os.walk('../../'):
                for file in files:
                    if file == "index.qmd" and os.path.basename(root) == directory:
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                if content.startswith('---'):
                                    _, front_matter, _ = content.split('---', 2)
                                    metadata = yaml.safe_load(front_matter)
                                    status = metadata.get('status', '')
                                    href += os.path.relpath(root, '.') + "/"
                                    if status == 'completed':
                                        checked = "checked"
                                        checkbox_class = "completed"
                                        name_class += " completed"
                                    elif status == 'failed':
                                        checked = "checked"
                                        checkbox_class = "failed"
                                        name_class += " failed"
                        except:
                            pass
        if href != '':
            html_content += f"""
            <li class="task-item">
                <input type="checkbox" class="task-checkbox {checkbox_class}" {checked} disabled>
                <a href="{href}" class="task-link">
                    <span class="task-name {name_class}">{name}</span>
                </a>
                {f'<div class="task-detail">{task.get("detail", "")}</div>' if task.get("detail") else ""}
            </li>
            """
        else:
            html_content += f"""
            <li class="task-item">
                <div class="task-main">
                    <input type="checkbox" class="task-checkbox {checkbox_class}" {checked} disabled>
                    <span class="task-name {name_class}">{name}</span>
                </div>
                {f'<div class="task-detail">{task.get("detail", "")}</div>' if task.get("detail") else ""}
            </li>

            """
    html_content += "</ul>"
    return html_content

def get_yaml_metadata(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        if content.startswith('---'):
            _, fm, _ = content.split('---', 2)
            return yaml.safe_load(fm)
    return {}

meta = get_yaml_metadata("index.qmd")

# tasks 데이터로부터 HTML 생성 및 표시
if 'tasks' in meta:
    display(HTML(generate_tasks_html(meta['tasks'])))
else:
    display(HTML("<p>No tasks defined.</p>"))
