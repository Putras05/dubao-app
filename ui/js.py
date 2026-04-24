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

    var _debounce;
    new MutationObserver(function() {{
        clearTimeout(_debounce);
        _debounce = setTimeout(applyAll, 80);
    }}).observe(doc.body, {{ childList: true, subtree: true }});
}})();
</script>
""", height=0, scrolling=False)


def hide_streamlit_badges_js() -> None:
    """Ẩn Streamlit Cloud badges ('Created by X' avatar + 'Hosted with Streamlit' origami
    + Manage app button) — CSS không bắt được vì Streamlit Cloud render chúng BẰNG JS
    sau khi app load. Dùng MutationObserver quét liên tục parent DOM."""
    _components.html("""
<script>
(function() {
    var doc = window.parent.document;

    function hideBadges() {
        // 1. Ẩn ALL link trỏ tới streamlit.io / share.streamlit.io (trừ docs)
        doc.querySelectorAll('a[href*="streamlit.io"]').forEach(function(el) {
            if (!el.href.includes('docs.streamlit.io')) {
                el.style.setProperty('display', 'none', 'important');
                // Ẩn luôn parent 2-3 cấp để bỏ hết avatar + text xung quanh
                var p = el.parentElement;
                for (var i = 0; i < 3 && p && p.tagName !== 'BODY'; i++) {
                    if (p.textContent && (
                        p.textContent.includes('Hosted with Streamlit') ||
                        p.textContent.includes('Created by') ||
                        p.textContent.includes('Manage app')
                    )) {
                        p.style.setProperty('display', 'none', 'important');
                    }
                    p = p.parentElement;
                }
            }
        });

        // 2. Ẩn theo selector pattern
        var selectors = [
            '[data-testid="stToolbar"]',
            '[data-testid="stDecoration"]',
            '[data-testid="stAppDeployButton"]',
            '[data-testid="stStatusWidget"]',
            '[data-testid="stHeader"]',
            '[data-testid*="manage-app"]',
            '[data-testid*="viewer"]',
            '[class*="viewerBadge"]',
            '[class*="ViewerBadge"]',
            '[class*="profileContainer"]',
            '[class*="_profileContainer"]',
            '.stDeployButton',
            'button[kind="header"]',
            'button[data-testid="baseButton-header"]',
            '#MainMenu'
        ];
        selectors.forEach(function(sel) {
            doc.querySelectorAll(sel).forEach(function(el) {
                el.style.setProperty('display',    'none', 'important');
                el.style.setProperty('visibility', 'hidden', 'important');
            });
        });

        // 3. Text-content match — ẩn element chứa ĐÚNG text "Created by X" / "Hosted with"
        doc.querySelectorAll('div, span, a').forEach(function(el) {
            if (el._checked) return;
            var txt = (el.textContent || '').trim();
            if (txt.length > 100) return;  // skip container lớn
            if (txt === 'Hosted with Streamlit' ||
                txt.startsWith('Created by ') ||
                txt === 'Manage app' ||
                txt === 'Fork this app') {
                // Ẩn luôn parent container (chứa cả avatar/icon)
                var p = el;
                for (var i = 0; i < 4 && p && p.tagName !== 'BODY'; i++) {
                    p.style.setProperty('display', 'none', 'important');
                    p._checked = true;
                    if (p.parentElement && p.parentElement.children.length <= 3) {
                        p = p.parentElement;
                    } else break;
                }
            }
        });
    }

    // Chạy ngay + retry nhiều lần (phòng badges load trễ)
    [10, 50, 150, 400, 900, 2000, 5000].forEach(function(ms) {
        setTimeout(hideBadges, ms);
    });

    // Observer bắt DOM thay đổi
    new MutationObserver(function() {
        hideBadges();
    }).observe(doc.body, { childList: true, subtree: true });
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
    new MutationObserver(forceSidebarOpen).observe(doc.body, {childList:true, subtree:true});
})();
</script>
""", height=0, scrolling=False)
