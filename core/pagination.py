"""
core/pagination.py
===================
Laravel-style database pagination engine. Wraps query results, count metadata, 
and renders theme-matching HTML controls dynamically.
"""

from urllib.parse import urlencode


class Paginator:
    def __init__(self, items: list, total: int, per_page: int, current_page: int, path: str, query_params: dict):
        self.items = items
        self.total = total
        self.per_page = per_page
        self.current_page = max(1, current_page)
        self.path = path
        self.query_params = query_params or {}
        
        # Calculate last page
        self.last_page = max(1, (self.total + self.per_page - 1) // self.per_page)

    def has_pages(self) -> bool:
        return self.last_page > 1

    def has_more(self) -> bool:
        return self.current_page < self.last_page

    def has_previous(self) -> bool:
        return self.current_page > 1

    def url(self, page: int) -> str:
        # Rebuild and preserve other query parameters
        params = {}
        for k, v in self.query_params.items():
            if isinstance(v, list):
                params[k] = v[0] if v else ""
            else:
                params[k] = v
        params["page"] = page
        return f"{self.path}?{urlencode(params)}"

    def next_page_url(self) -> str:
        return self.url(self.current_page + 1) if self.has_more() else None

    def previous_page_url(self) -> str:
        return self.url(self.current_page - 1) if self.has_previous() else None

    def map(self, callback):
        """Map callback to hydrate raw items into Model objects if desired"""
        self.items = [callback(item) for item in self.items]
        return self

    def __iter__(self):
        return iter(self.items)

    def __len__(self) -> int:
        return len(self.items)

    def links(self) -> str:
        if not self.has_pages():
            return ""

        html_parts = [
            '<div class="pyflow-pagination" style="display: flex; justify-content: space-between; align-items: center; padding: 20px; border-top: 1px solid var(--bd);">'
        ]
        
        # Details text
        start_item = (self.current_page - 1) * self.per_page + 1
        end_item = min(self.current_page * self.per_page, self.total)
        html_parts.append(
            f'<div style="font-size: 13px; color: var(--tx-3);">'
            f'পেজ <strong>{self.current_page}</strong> / <strong>{self.last_page}</strong> '
            f'(মোট <strong>{self.total}</strong> টি রেকর্ডের মধ্যে <strong>{start_item}-{end_item}</strong> দেখানো হচ্ছে)'
            f'</div>'
        )

        # Pagination Buttons wrapper
        html_parts.append('<div style="display: flex; gap: 6px; align-items: center;">')

        # Previous page button
        if self.has_previous():
            html_parts.append(
                f'<a href="{self.previous_page_url()}" class="pm-btn pm-btn-outline" style="padding: 6px 12px; font-size: 13px; border-radius: 8px; text-decoration: none; border: 1.5px solid var(--bd, #ddd); color: var(--tx-main, #333); display: inline-flex; align-items: center; gap: 8px; background: var(--tb-btn-bg, transparent);">'
                f'<i class="fas fa-chevron-left" style="font-size: 10px;"></i> পূর্ববর্তী</a>'
            )
        else:
            html_parts.append(
                f'<span class="pm-btn pm-btn-outline" style="padding: 6px 12px; font-size: 13px; border-radius: 8px; opacity: 0.5; cursor: not-allowed; display: inline-flex; align-items: center; gap: 8px; border: 1.5px solid var(--bd, #ddd); background: var(--tb-btn-bg, transparent); color: var(--tx-3, #999);">'
                f'<i class="fas fa-chevron-left" style="font-size: 10px;"></i> পূর্ববর্তী</span>'
            )

        # Page numbers
        start_page = max(1, self.current_page - 2)
        end_page = min(self.last_page, self.current_page + 2)

        if start_page > 1:
            html_parts.append(
                f'<a href="{self.url(1)}" class="pm-btn pm-btn-outline" style="padding: 6px 12px; font-size: 13px; border-radius: 8px; text-decoration: none; border: 1.5px solid var(--bd, #ddd); color: var(--tx-main, #333); background: var(--tb-btn-bg, transparent);">1</a>'
            )
            if start_page > 2:
                html_parts.append('<span style="color: var(--tx-3, #999); padding: 0 4px;">...</span>')

        for p in range(start_page, end_page + 1):
            if p == self.current_page:
                html_parts.append(
                    f'<span class="pm-btn pm-btn-primary" style="padding: 6px 12px; font-size: 13px; border-radius: 8px; cursor: default; background: var(--pm-btn-primary-bg, #5a32a8); color: white; border: 1.5px solid var(--pm-btn-primary-bg, #5a32a8);">{p}</span>'
                )
            else:
                html_parts.append(
                    f'<a href="{self.url(p)}" class="pm-btn pm-btn-outline" style="padding: 6px 12px; font-size: 13px; border-radius: 8px; text-decoration: none; border: 1.5px solid var(--bd, #ddd); color: var(--tx-main, #333); background: var(--tb-btn-bg, transparent);">{p}</a>'
                )

        if end_page < self.last_page:
            if end_page < self.last_page - 1:
                html_parts.append('<span style="color: var(--tx-3, #999); padding: 0 4px;">...</span>')
            html_parts.append(
                f'<a href="{self.url(self.last_page)}" class="pm-btn pm-btn-outline" style="padding: 6px 12px; font-size: 13px; border-radius: 8px; text-decoration: none; border: 1.5px solid var(--bd, #ddd); color: var(--tx-main, #333); background: var(--tb-btn-bg, transparent);">{self.last_page}</a>'
            )

        # Next page button
        if self.has_more():
            html_parts.append(
                f'<a href="{self.next_page_url()}" class="pm-btn pm-btn-outline" style="padding: 6px 12px; font-size: 13px; border-radius: 8px; text-decoration: none; border: 1.5px solid var(--bd, #ddd); color: var(--tx-main, #333); display: inline-flex; align-items: center; gap: 8px; background: var(--tb-btn-bg, transparent);">'
                f'পরবর্তী <i class="fas fa-chevron-right" style="font-size: 10px;"></i></a>'
            )
        else:
            html_parts.append(
                f'<span class="pm-btn pm-btn-outline" style="padding: 6px 12px; font-size: 13px; border-radius: 8px; opacity: 0.5; cursor: not-allowed; display: inline-flex; align-items: center; gap: 8px; border: 1.5px solid var(--bd, #ddd); background: var(--tb-btn-bg, transparent); color: var(--tx-3, #999);">'
                f'পরবর্তী <i class="fas fa-chevron-right" style="font-size: 10px;"></i></span>'
            )

        html_parts.append('</div>')
        html_parts.append('</div>')

        return "".join(html_parts)
