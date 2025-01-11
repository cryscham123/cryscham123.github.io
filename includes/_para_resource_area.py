from IPython.display import HTML

if posts:
    html_content = """
    <div class="title-list">
    """

    for post in filter(target_func, posts):
        html_content += f"""
        <a href="{post['path']}" class="title-item">
            <span>{post['title']}</span>
        </a>
        """

    html_content += "</div>"
    display(HTML(html_content))
else:
    display(HTML("<p>No posts found.</p>"))

