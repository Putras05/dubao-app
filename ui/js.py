import streamlit.components.v1 as _components


def inject_theme_js(T: dict) -> None:
    """Inject JS via components.html (iframe → window.parent) to force-apply theme colors."""
    bg  = T['bg_card']
    bge = T['bg_elevated']
    fg  = T['text_primary']
    brd = T['border']
    acc = T['accent']
    suc = T['success']
    _components.html(f"""
<script>
(function() {{
    var BG  = '{bg}';
    var BGE = '{bge}';
    var FG  = '{fg}';
    var BRD = '1px solid {brd}';
    var ACC = '{acc}';
    var SUC = '{suc}';
    var doc = window.parent.document;

    function styleEl(el, bg, fg, brd, radius) {{
        el.style.setProperty('background-color', bg,  'important');
        el.style.setProperty('color',            fg,  'important');
        el.style.setProperty('border',           brd, 'important');
        el.style.setProperty('border-radius',    radius, 'important');
        el.style.setProperty('font-weight',      '600', 'important');
        el.querySelectorAll('p, span').forEach(function(c) {{
            c.style.setProperty('color',      fg,          'important');
            c.style.setProperty('background', 'transparent','important');
        }});
    }}

    function fixSidebarWidgets() {{
        var sb = doc.querySelector('[data-testid="stSidebar"]');
        if (!sb) return;

        /* Selectbox — set tinted background on the visible select container */
        sb.querySelectorAll('[data-testid="stSelectbox"] [data-baseweb="select"] > div:first-child').forEach(function(el) {{
            el.style.setProperty('background',       'rgba(255,255,255,0.08)', 'important');
            el.style.setProperty('background-color', 'rgba(255,255,255,0.08)', 'important');
            el.style.setProperty('border',           '1px solid rgba(255,255,255,0.15)', 'important');
            el.style.setProperty('border-radius',    '8px', 'important');
        }});
        /* Selectbox inner elements — transparent + white text */
        sb.querySelectorAll('[data-testid="stSelectbox"] [data-baseweb="select"] > div:first-child *').forEach(function(el) {{
            if (el.tagName !== 'SVG' && el.tagName !== 'svg' && el.tagName !== 'PATH' && el.tagName !== 'path')
                el.style.setProperty('color', '#FFFFFF', 'important');
            el.style.setProperty('background',       'transparent', 'important');
            el.style.setProperty('background-color', 'transparent', 'important');
        }});
        /* SVG arrow in selectbox */
        sb.querySelectorAll('[data-testid="stSelectbox"] svg').forEach(function(el) {{
            el.style.setProperty('fill', 'rgba(191,219,254,0.8)', 'important');
        }});

        /* NumberInput container */
        sb.querySelectorAll('[data-testid="stNumberInput"] > div').forEach(function(el) {{
            el.style.setProperty('background',       'rgba(255,255,255,0.04)', 'important');
            el.style.setProperty('background-color', 'rgba(255,255,255,0.04)', 'important');
            el.style.setProperty('border',           '1px solid rgba(255,255,255,0.10)', 'important');
            el.style.setProperty('border-radius',    '10px', 'important');
            el.style.setProperty('overflow',         'hidden', 'important');
        }});
        /* NumberInput input text */
        sb.querySelectorAll('[data-testid="stNumberInput"] input').forEach(function(el) {{
            el.style.setProperty('background',       'transparent', 'important');
            el.style.setProperty('background-color', 'transparent', 'important');
            el.style.setProperty('color',            '#FFFFFF', 'important');
        }});
        /* NumberInput +/- buttons */
        sb.querySelectorAll('[data-testid="stNumberInput"] button').forEach(function(el) {{
            el.style.setProperty('background',       'rgba(255,255,255,0.04)', 'important');
            el.style.setProperty('background-color', 'rgba(255,255,255,0.04)', 'important');
            el.style.setProperty('color',            'rgba(191,219,254,0.8)', 'important');
            el.style.setProperty('border-left',      '1px solid rgba(255,255,255,0.08)', 'important');
        }});

        /* DateInput container */
        sb.querySelectorAll('[data-testid="stDateInput"] [data-baseweb="input"]').forEach(function(el) {{
            el.style.setProperty('background',       'rgba(255,255,255,0.08)', 'important');
            el.style.setProperty('background-color', 'rgba(255,255,255,0.08)', 'important');
            el.style.setProperty('border',           '1px solid rgba(255,255,255,0.15)', 'important');
            el.style.setProperty('border-radius',    '8px', 'important');
        }});
        sb.querySelectorAll('[data-testid="stDateInput"] input').forEach(function(el) {{
            el.style.setProperty('background',       'transparent', 'important');
            el.style.setProperty('background-color', 'transparent', 'important');
            el.style.setProperty('color',            '#FFFFFF', 'important');
        }});
    }}

    function applyAll() {{
        var root = doc.querySelector('[data-testid="stMain"]') ||
                   doc.querySelector('.main') || doc.body;
        if (!root) return;

        var RBG = 'linear-gradient(135deg,#0D1F4A 0%,#1B3D8C 60%,#2756C0 100%)';
        function styleRefreshBtn(btn) {{
            btn.style.setProperty('background',       RBG,   'important');
            btn.style.setProperty('background-image', RBG,   'important');
            btn.style.setProperty('color',            '#FFF','important');
            btn.style.setProperty('border',           'none','important');
            btn.style.setProperty('border-radius',    '10px','important');
            btn.style.setProperty('font-size',        '22px','important');
            btn.style.setProperty('min-height',       '60px','important');
            btn.style.setProperty('box-shadow',       '0 2px 10px rgba(27,61,140,0.4)','important');
            btn.querySelectorAll('p,span,div').forEach(function(c) {{
                c.style.setProperty('color',            '#FFF',        'important');
                c.style.setProperty('background',       'transparent', 'important');
                c.style.setProperty('background-image', 'none',        'important');
            }});
            if (!btn._hoverRefresh) {{
                btn._hoverRefresh = true;
                btn.addEventListener('mouseenter', function() {{
                    btn.style.setProperty('filter','brightness(1.2)','important');
                    btn.style.setProperty('transform','rotate(180deg)','important');
                }});
                btn.addEventListener('mouseleave', function() {{
                    btn.style.setProperty('filter','none','important');
                    btn.style.setProperty('transform','rotate(0deg)','important');
                }});
            }}
        }}
        doc.querySelectorAll('.refresh-header-btn button').forEach(styleRefreshBtn);
        root.querySelectorAll('.stButton > button').forEach(function(btn) {{
            var txt = btn.textContent.trim();
            if (txt === '↺' || txt === '⟳' || txt === '🔄') {{
                styleRefreshBtn(btn); return;
            }}

            if (btn.closest('[data-testid="stSidebar"]')) return;
            if (btn.closest('.stDownloadButton')) return;
            if (btn.closest('[data-baseweb="tab-list"]')) return;
            styleEl(btn, BG, FG, BRD, '20px');
            if (!btn._evt) {{
                btn._evt = true;
                btn.addEventListener('mouseenter', function() {{
                    btn.style.setProperty('background-color', ACC, 'important');
                    btn.style.setProperty('color', '#fff', 'important');
                    btn.style.setProperty('border-color', ACC, 'important');
                    btn.querySelectorAll('p,span').forEach(function(c) {{
                        c.style.setProperty('color', '#fff', 'important');
                    }});
                }});
                btn.addEventListener('mouseleave', function() {{
                    btn.style.setProperty('background-color', BG, 'important');
                    btn.style.setProperty('color', FG, 'important');
                    btn.style.setProperty('border-color', '{brd}', 'important');
                    btn.querySelectorAll('p,span').forEach(function(c) {{
                        c.style.setProperty('color', FG, 'important');
                    }});
                }});
            }}
        }});

        root.querySelectorAll('[data-baseweb="input"]').forEach(function(el) {{
            if (el.closest('[data-testid="stSidebar"]')) return;
            el.style.setProperty('background-color', BG, 'important');
            el.style.setProperty('border', BRD, 'important');
            el.style.setProperty('border-radius', '20px', 'important');
            el.style.setProperty('min-height', '40px', 'important');
            el.querySelectorAll('input').forEach(function(inp) {{
                inp.style.setProperty('color',       FG,            'important');
                inp.style.setProperty('background',  'transparent', 'important');
                inp.style.setProperty('font-weight', '600',         'important');
                inp.style.setProperty('font-size',   '13px',        'important');
            }});
        }});

        root.querySelectorAll('[data-baseweb="select"] > div').forEach(function(el) {{
            if (el.closest('[data-testid="stSidebar"]')) return;
            el.style.setProperty('background-color', BG, 'important');
            el.style.setProperty('border-color', brd, 'important');
            el.querySelectorAll('*').forEach(function(c) {{
                if (c.tagName !== 'INPUT')
                    c.style.setProperty('background', 'transparent', 'important');
                c.style.setProperty('color', FG, 'important');
            }});
        }});

        fixSidebarWidgets();

        doc.querySelectorAll('[data-testid="stSidebar"] iframe').forEach(function(iframe) {{
            try {{
                var idoc = iframe.contentDocument || iframe.contentWindow.document;
                if (idoc && idoc.body) {{
                    idoc.body.style.setProperty('background', 'transparent', 'important');
                    idoc.body.style.setProperty('background-color', 'transparent', 'important');
                    idoc.documentElement.style.setProperty('background', 'transparent', 'important');
                    idoc.documentElement.style.setProperty('background-color', 'transparent', 'important');
                }}
            }} catch(e) {{}}
        }});
        doc.querySelectorAll('[data-testid="stSidebar"] [data-testid="stCustomComponentV1"],' +
                             '[data-testid="stSidebar"] .stComponentContainer').forEach(function(el) {{
            el.style.setProperty('background', 'transparent', 'important');
            el.style.setProperty('border', 'none', 'important');
            el.style.setProperty('box-shadow', 'none', 'important');
        }});

        root.querySelectorAll('.stDownloadButton > button').forEach(function(btn) {{
            styleEl(btn, BG, FG, BRD, '10px');
            if (!btn._dlEvt) {{
                btn._dlEvt = true;
                btn.addEventListener('mouseenter', function() {{
                    btn.style.setProperty('background-color', SUC, 'important');
                    btn.style.setProperty('color', '#fff', 'important');
                    btn.querySelectorAll('p,span').forEach(function(c) {{
                        c.style.setProperty('color', '#fff', 'important');
                    }});
                }});
                btn.addEventListener('mouseleave', function() {{
                    btn.style.setProperty('background-color', BG, 'important');
                    btn.style.setProperty('color', FG, 'important');
                    btn.querySelectorAll('p,span').forEach(function(c) {{
                        c.style.setProperty('color', FG, 'important');
                    }});
                }});
            }}
        }});

        doc.querySelectorAll('[data-testid="stDataFrame"]').forEach(function(el) {{
            el.style.setProperty('background',       BG, 'important');
            el.style.setProperty('background-color', BG, 'important');
        }});
    }}

    [50, 150, 400, 900, 2000].forEach(function(ms) {{ setTimeout(applyAll, ms); }});
    [100, 300, 700, 1500].forEach(function(ms) {{ setTimeout(fixSidebarWidgets, ms); }});

    // Debounce 350ms (was 80ms) — Plotly mutations rất nhiều khi pan/zoom,
    // 80ms khiến cả applyAll() chạy liên tục gây jank chart.
    var _debounce;
    new MutationObserver(function() {{
        clearTimeout(_debounce);
        _debounce = setTimeout(applyAll, 350);
    }}).observe(doc.body, {{ childList: true, subtree: true }});
}})();
</script>
""", height=0, scrolling=False)


def hide_streamlit_badges_js() -> None:
    """Ẩn Streamlit Cloud badges — LIGHTWEIGHT version (không làm quá tải app).
    Chỉ chạy initial burst + MutationObserver (event-driven, không polling)."""
    _components.html("""
<script>
(function() {
    var doc;
    try { doc = window.parent.document; } catch(e) { return; }

    // Inject CSS 1 lần vào parent <head>
    if (!doc._badgeCssInjected) {
        try {
            var style = doc.createElement('style');
            style.id = '__hide_streamlit_badges__';
            style.textContent = `
                [class*="viewerBadge"], [class*="ViewerBadge"],
                [class*="profileContainer"], [class*="_profileContainer"],
                [data-testid="stToolbar"], [data-testid="stDecoration"],
                [data-testid="stAppDeployButton"], [data-testid="stStatusWidget"],
                [data-testid*="manage-app"], [data-testid*="viewer"],
                .stDeployButton, .stAppDeployButton,
                button[kind="header"], button[data-testid="baseButton-header"],
                #MainMenu {
                    display: none !important;
                    visibility: hidden !important;
                }
                a[href*="streamlit.io"]:not([href*="docs.streamlit.io"]) {
                    display: none !important;
                }
            `;
            (doc.head || doc.documentElement).appendChild(style);
            doc._badgeCssInjected = true;
        } catch(e) {}
    }

    function hideBadges() {
        if (!doc.querySelectorAll) return;
        // Chỉ target selector cụ thể (không scan toàn bộ div/span — quá tốn CPU)
        var sels = [
            '[class*="viewerBadge"]','[class*="ViewerBadge"]',
            '[class*="profileContainer"]','[data-testid*="viewer"]',
            '[data-testid*="manage-app"]','[data-testid="stToolbar"]',
            '[data-testid="stDecoration"]','[data-testid="stAppDeployButton"]',
            '[data-testid="stStatusWidget"]','.stDeployButton'
        ];
        sels.forEach(function(sel) {
            doc.querySelectorAll(sel).forEach(function(el) {
                if (!el._hidden) {
                    el.style.setProperty('display', 'none', 'important');
                    el._hidden = true;
                }
            });
        });
        // Hide streamlit.io links (không phải docs)
        doc.querySelectorAll('a[href*="streamlit.io"]').forEach(function(el) {
            if (el._hidden) return;
            if (!el.href.includes('docs.streamlit.io')) {
                el.style.setProperty('display', 'none', 'important');
                el._hidden = true;
            }
        });
    }

    // Initial burst — chỉ vài lần đầu, KHÔNG setInterval permanent
    [50, 300, 1000, 3000].forEach(function(ms) { setTimeout(hideBadges, ms); });

    // MutationObserver — event-driven, chỉ fire khi DOM thay đổi (ít tốn CPU)
    try {
        var _deb;
        new MutationObserver(function() {
            clearTimeout(_deb);
            _deb = setTimeout(hideBadges, 100);
        }).observe(doc.body, { childList: true, subtree: true });
    } catch(e) {}
})();
</script>
""", height=0, scrolling=False)


def force_sidebar_open_js() -> None:
    _components.html("""
<script>
(function() {
    var doc = window.parent.document;
    function forceSidebarOpen() {
        var sb = doc.querySelector('[data-testid="stSidebar"]');
        if (sb) {
            sb.setAttribute('aria-expanded', 'true');
            sb.style.setProperty('display',     'block',        'important');
            sb.style.setProperty('visibility',  'visible',      'important');
            sb.style.setProperty('transform',   'translateX(0)','important');
            sb.style.setProperty('margin-left', '0',            'important');
            sb.style.setProperty('width',       '280px',        'important');
            sb.style.setProperty('min-width',   '280px',        'important');
        }
        var hides = [
            '[data-testid="collapsedControl"]',
            '[data-testid="stSidebarCollapsedControl"]',
            '[data-testid="stSidebarHeader"]',
            '[data-testid="stSidebarCollapseButton"]',
            'button[data-testid="baseButton-headerNoPadding"]'
        ];
        hides.forEach(function(sel) {
            doc.querySelectorAll(sel).forEach(function(el) {
                el.style.setProperty('display', 'none', 'important');
            });
        });
    }
    [50, 200, 500, 1200, 2500].forEach(function(ms) { setTimeout(forceSidebarOpen, ms); });
    // Bỏ MutationObserver — initial burst đủ, observer chạy mỗi Plotly DOM
    // mutation gây jank rất nặng khi tương tác chart.
})();
</script>
""", height=0, scrolling=False)
