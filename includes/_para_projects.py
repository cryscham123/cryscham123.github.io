if posts:
    html_content = """
    <script>
    document.addEventListener('DOMContentLoaded', function() {
        document.querySelectorAll('.days-left').forEach(element => {
            const endDate = element.getAttribute('data-end-date');
            if (!endDate || endDate === "None") {
                element.textContent = 'No end date';
                element.className = 'days-left days-left-nodate';
                return;
            }

            const end = new Date(endDate);
            const now = new Date();
            const diffTime = end - now;
            const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

            if (isNaN(diffDays)) {
                element.textContent = 'Invalid date';
                element.className = 'days-left days-left-invalid';
            } else if (diffDays > 0) {
                element.textContent = `${diffDays} days left`;
                element.className = 'days-left days-left-remaining';
            } else {
                element.textContent = 'Overdue';
                element.className = 'days-left days-left-overdue';
            }
        });
    });
    </script>
    <div class="project-cards">
    """

    for post in filter(target_func, posts):
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
                    <span class="days-left" data-end-date="{post.get('end_date', '')}">Calculating...</span>
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
    display(HTML("<p>No posts found.</p>"))
