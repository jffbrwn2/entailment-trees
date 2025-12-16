---
layout: default
title: Home
---

# AI Simulations

Testing neural recording device feasibility from first principles.

---

## Posts

{% for post in site.posts %}
- [{{ post.title }}]({{ post.url | relative_url }})
  <small>{{ post.date | date: "%B %-d, %Y" }}</small>
{% endfor %}

{% if site.posts.size == 0 %}
*No posts yet.*
{% endif %}
