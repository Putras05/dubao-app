"""Academic references database cho chatbot — APA 7th, song ngữ VI/EN."""

REFERENCES = {
    'box_jenkins_1976': {
        'apa': 'Box, G. E. P., & Jenkins, G. M. (1976). *Time Series Analysis: Forecasting and Control*. San Francisco: Holden-Day.',
        'topic': ['ar', 'autoregressive', 'arima', 'time_series'],
        'note_vi': 'Tài liệu kinh điển về mô hình AR, MA, ARIMA.',
        'note_en': 'Classical reference for AR, MA, ARIMA models.',
    },
    'hamilton_1994': {
        'apa': 'Hamilton, J. D. (1994). *Time Series Analysis*. Princeton, NJ: Princeton University Press.',
        'topic': ['ar', 'time_series', 'econometrics'],
        'note_vi': 'Giáo trình cao học về time series analysis.',
        'note_en': 'Graduate-level time series textbook.',
    },
    'hyndman_2021': {
        'apa': 'Hyndman, R. J., & Athanasopoulos, G. (2021). *Forecasting: Principles and Practice* (3rd ed.). Melbourne: OTexts. https://otexts.com/fpp3/',
        'topic': ['mape', 'metrics', 'forecasting', 'evaluation'],
        'note_vi': 'Sách mở trực tuyến, chuẩn đánh giá dự báo.',
        'note_en': 'Open online textbook, forecast evaluation standard.',
    },
    'wooldridge_2019': {
        'apa': 'Wooldridge, J. M. (2019). *Introductory Econometrics: A Modern Approach* (7th ed.). Boston: Cengage Learning.',
        'topic': ['mlr', 'multiple_regression', 'ols', 'econometrics'],
        'note_vi': 'Giáo trình kinh tế lượng căn bản về MLR, OLS.',
        'note_en': 'Standard undergraduate econometrics textbook.',
    },
    'greene_2018': {
        'apa': 'Greene, W. H. (2018). *Econometric Analysis* (8th ed.). New York: Pearson.',
        'topic': ['mlr', 'econometrics', 'distributed_lag'],
        'note_vi': 'Tham khảo nâng cao về kinh tế lượng và Distributed Lag.',
        'note_en': 'Advanced econometrics reference.',
    },
    'breiman_1984': {
        'apa': 'Breiman, L., Friedman, J. H., Olshen, R. A., & Stone, C. J. (1984). *Classification and Regression Trees*. Belmont, CA: Wadsworth.',
        'topic': ['cart', 'decision_tree', 'machine_learning'],
        'note_vi': 'Công trình gốc giới thiệu thuật toán CART.',
        'note_en': 'Original work introducing CART algorithm.',
    },
    'hastie_2009': {
        'apa': 'Hastie, T., Tibshirani, R., & Friedman, J. (2009). *The Elements of Statistical Learning* (2nd ed.). New York: Springer.',
        'topic': ['cart', 'decision_tree', 'machine_learning', 'overfitting'],
        'note_vi': 'Tham khảo chính về thống kê học máy.',
        'note_en': 'Main statistical learning reference.',
    },
    'hosoda_1969': {
        'apa': 'Hosoda, G. (1969). *Ichimoku Kinko Hyo* [一目均衡表]. Tokyo: Keizai Henshuukai. (English: Patel, M. (2010). *Trading with Ichimoku Clouds*. Wiley.)',
        'topic': ['ichimoku', 'technical_analysis', 'kumo', 'tenkan', 'kijun', 'chikou'],
        'note_vi': 'Tác phẩm gốc tiếng Nhật giới thiệu Ichimoku Kinko Hyo.',
        'note_en': 'Original Japanese work on Ichimoku Kinko Hyo.',
    },
    'elliott_2007': {
        'apa': 'Elliott, N. (2007). *Ichimoku Charts: An Introduction to Ichimoku Kinko Clouds*. Petersfield: Harriman House.',
        'topic': ['ichimoku', 'technical_analysis'],
        'note_vi': 'Giới thiệu Ichimoku bằng tiếng Anh, hệ thống và dễ hiểu.',
        'note_en': 'Systematic English introduction to Ichimoku.',
    },
    'murphy_1999': {
        'apa': 'Murphy, J. J. (1999). *Technical Analysis of the Financial Markets*. New York: NY Institute of Finance.',
        'topic': ['technical_analysis', 'rsi', 'moving_average'],
        'note_vi': 'Bách khoa về phân tích kỹ thuật.',
        'note_en': 'Encyclopedic technical analysis reference.',
    },
    'fama_1970': {
        'apa': 'Fama, E. F. (1970). Efficient Capital Markets: A Review of Theory and Empirical Work. *The Journal of Finance*, 25(2), 383-417.',
        'topic': ['efficient_market', 'market_efficiency', 'emh'],
        'note_vi': 'Bài báo gốc về Giả thuyết Thị trường Hiệu quả (EMH).',
        'note_en': 'Seminal paper on Efficient Market Hypothesis.',
    },
    'vnstock_2024': {
        'apa': 'Vnstock Team. (2024). *vnstock: Python library for Vietnamese stock market data*. https://github.com/thinh-vu/vnstock',
        'topic': ['vnstock', 'hose', 'data'],
        'note_vi': 'Thư viện Python nguồn mở cho dữ liệu HOSE, HNX.',
        'note_en': 'Open-source Python library for HOSE, HNX data.',
    },
}


def get_references_by_topic(topic: str, lang: str = 'VI') -> str:
    topic_lower = topic.lower().replace(' ', '_')
    matched = [r for r in REFERENCES.values() if topic_lower in r['topic']]
    if not matched:
        return ''
    header = '### Tài liệu tham khảo' if lang == 'VI' else '### References'
    lines = [header, '']
    for i, ref in enumerate(matched, 1):
        lines.append(f'[{i}] {ref["apa"]}')
        note = ref.get(f'note_{lang.lower()}', '')
        if note:
            lines.append(f'    *{note}*')
        lines.append('')
    return '\n'.join(lines)


def get_all_references(lang: str = 'VI') -> str:
    header = '### Danh mục tài liệu tham khảo' if lang == 'VI' else '### Complete Bibliography'
    lines = [header, '']
    for i, ref in enumerate(REFERENCES.values(), 1):
        lines.append(f'[{i}] {ref["apa"]}')
        lines.append('')
    return '\n'.join(lines)


def detect_citation_request(query: str):
    import re
    q = query.lower()
    citation_kws = [
        r'(tài liệu|tham khảo|nguồn|reference|citation|sách|paper|bibliography)',
        r'(ở đâu|where|which book|cuốn sách nào|công trình nào)',
        r'(cited from|trích dẫn|dẫn nguồn)',
    ]
    is_citation = any(re.search(k, q) for k in citation_kws)
    if not is_citation:
        return False, None

    topic_kws = {
        'ar':                ['ar ', 'autoregressive', 'tự hồi quy'],
        'mlr':               ['mlr', 'multiple regression', 'hồi quy bội'],
        'cart':              ['cart', 'decision tree', 'cây quyết định'],
        'ichimoku':          ['ichimoku', 'kinko', 'kumo', 'tenkan', 'kijun'],
        'mape':              ['mape', 'rmse', 'mae', 'metric', 'đánh giá'],
        'technical_analysis':['phân tích kỹ thuật', 'technical analysis'],
        'efficient_market':  ['efficient market', 'thị trường hiệu quả', 'emh'],
    }
    for topic, kws in topic_kws.items():
        if any(kw in q for kw in kws):
            return True, topic
    return True, None
