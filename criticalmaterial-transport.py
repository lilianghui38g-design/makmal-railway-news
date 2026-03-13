import streamlit as st
import requests
from bs4 import BeautifulSoup
import feedparser
import pandas as pd
from datetime import datetime, timedelta
import time
import hashlib
from urllib.parse import urlparse

# 页面配置
st.set_page_config(
    page_title="欧美-中亚关键矿产与物流运输监控",
    page_icon="🌍",
    layout="wide"
)

# 标题
st.title("🌍 欧美-中亚关键矿产与物流运输实时监控")
st.markdown("监控来源：中亚/美国/欧洲媒体 | 相关公司/机构 | 国际/中亚智库")

# 侧边栏配置
with st.sidebar:
    st.header("⚙️ 监控设置")
    
    # 关键词设置（核心主题）
    default_keywords = """critical minerals
rare earth
lithium
cobalt
copper
supply chain
logistics
transport corridor
Middle Corridor
Trans-Caspian
investment
infrastructure
strategic partnership
关键矿产
稀土
锂
钴
供应链
物流
运输走廊
中间走廊
投资
基础设施
战略伙伴"""
    
    keywords_text = st.text_area("输入关键词（每行一个）", default_keywords, height=200)
    keywords = [k.strip() for k in keywords_text.split('\n') if k.strip()]
    
    # 时间范围
    days_back = st.slider("回溯天数", 1, 30, 7)
    
    # 信源分类筛选
    st.subheader("信源分类")
    show_categories = {
        "中亚媒体": st.checkbox("中亚媒体", True),
        "美国媒体": st.checkbox("美国媒体", True),
        "欧洲媒体": st.checkbox("欧洲媒体", True),
        "公司/机构": st.checkbox("公司/机构", True),
        "智库": st.checkbox("智库", True)
    }
    
    # 刷新按钮
    if st.button("🔄 手动刷新"):
        st.cache_data.clear()
        st.rerun()
    
    st.info("数据每6小时自动更新，也可手动刷新")

# 定义信源（详细清单）
@st.cache_data(ttl=21600)  # 缓存6小时
def load_sources():
    """定义所有监控信源"""
    sources = {
        "中亚媒体": {
            "icon": "🌏",
            "urls": [
                # 吉尔吉斯
                {"name": "卡巴尔通讯社 (Kabar)", "rss": "https://kabar.kg/rss/", "type": "rss"},
                {"name": "24.kg", "rss": "https://24.kg/rss/", "type": "rss"},
                {"name": "AKIpress", "rss": "https://akipress.com/rss/", "type": "rss"},
                # 哈萨克斯坦
                {"name": "Tengrinews", "rss": "https://tengrinews.kz/rss/", "type": "rss"},
                {"name": "Inform.kz", "rss": "https://www.inform.kz/rss/", "type": "rss"},
                # 乌兹别克斯坦
                {"name": "UzA", "rss": "https://uza.uz/rss", "type": "rss"},
                {"name": "Gazeta.uz", "rss": "https://gazeta.uz/rss", "type": "rss"},
                # 塔吉克斯坦
                {"name": "Avesta.tj", "rss": "http://avesta.tj/rss", "type": "rss"}
            ]
        },
        "美国媒体": {
            "icon": "🇺🇸",
            "urls": [
                {"name": "Yahoo News", "rss": "https://www.yahoo.com/news/rss", "type": "rss"},
                {"name": "CNN", "rss": "http://rss.cnn.com/rss/cnn_topstories.rss", "type": "rss"},
                {"name": "Fox News", "rss": "https://moxie.foxnews.com/google-publisher/world.xml", "type": "rss"},
                {"name": "纽约时报", "rss": "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml", "type": "rss"},
                {"name": "华尔街日报", "rss": "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml", "type": "rss"},
                {"name": "华盛顿邮报", "rss": "http://feeds.washingtonpost.com/rss/world", "type": "rss"}
            ]
        },
        "欧洲媒体": {
            "icon": "🇪🇺",
            "urls": [
                {"name": "BBC News", "rss": "http://feeds.bbci.co.uk/news/world/rss.xml", "type": "rss"},
                {"name": "Reuters", "rss": "https://feeds.reuters.com/reuters/businessNews", "type": "rss"},
                {"name": "EUobserver", "rss": "https://euobserver.com/rss", "type": "rss"},
                {"name": "Politico Europe", "rss": "https://www.politico.eu/feed/", "type": "rss"},
                {"name": "法国世界报", "rss": "https://www.lemonde.fr/en/economy/rss_full.xml", "type": "rss"},
                {"name": "德国之声", "rss": "https://rss.dw.com/rdf/rss-en-all", "type": "rss"}
            ]
        },
        "公司/机构": {
            "icon": "🏢",
            "urls": [
                # 矿业公司
                {"name": "力拓", "url": "https://www.riotinto.com/news", "type": "web", "check_url": "https://www.riotinto.com/news"},
                {"name": "嘉能可", "url": "https://www.glencore.com/media", "type": "web", "check_url": "https://www.glencore.com/media"},
                # 物流公司
                {"name": "马士基", "rss": "https://www.maersk.com/rss", "type": "rss"},
                {"name": "德铁", "url": "https://www.deutschebahn.com/en/presse", "type": "web", "check_url": "https://www.deutschebahn.com/en/presse"},
                # 国际金融机构
                {"name": "EBRD", "rss": "https://www.ebrd.com/news/rss.xml", "type": "rss"},
                {"name": "世界银行", "rss": "https://www.worldbank.org/en/news/rss", "type": "rss"},
                {"name": "亚洲开发银行", "rss": "https://www.adb.org/rss", "type": "rss"}
            ]
        },
        "智库": {
            "icon": "📚",
            "urls": [
                # 国际智库
                {"name": "CSIS", "rss": "https://www.csis.org/rss.xml", "type": "rss"},
                {"name": "Carnegie", "rss": "https://carnegieendowment.org/rss/", "type": "rss"},
                {"name": "RAND", "rss": "https://www.rand.org/topics/rss.xml", "type": "rss"},
                {"name": "Chatham House", "rss": "https://www.chathamhouse.org/rss", "type": "rss"},
                {"name": "Atlantic Council", "rss": "https://www.atlanticcouncil.org/feed/", "type": "rss"},
                # 中亚智库
                {"name": "中亚区域经济合作学院", "url": "https://www.carecinstitute.org/publications", "type": "web", "check_url": "https://www.carecinstitute.org/publications"},
                {"name": "哈萨克斯坦战略研究所", "url": "https://kisi.kz/en/publications", "type": "web", "check_url": "https://kisi.kz/en/publications"}
            ]
        }
    }
    return sources

# RSS解析函数
def parse_rss(feed_url, source_name, keywords, days_back):
    articles = []
    try:
        feed = feedparser.parse(feed_url)
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        for entry in feed.entries[:50]:
            # 解析发布时间
            if hasattr(entry, 'published_parsed'):
                pub_date = datetime(*entry.published_parsed[:6])
            elif hasattr(entry, 'updated_parsed'):
                pub_date = datetime(*entry.updated_parsed[:6])
            else:
                pub_date = datetime.now()
            
            if pub_date < cutoff_date:
                continue
            
            title = entry.get('title', '')
            summary = entry.get('summary', '')
            full_text = (title + " " + summary).lower()
            
            matched = [kw for kw in keywords if kw.lower() in full_text]
            if matched:
                articles.append({
                    'title': title,
                    'url': entry.get('link', ''),
                    'source': source_name,
                    'source_type': 'RSS',
                    'published': pub_date,
                    'matched_keywords': ', '.join(matched),
                    'snippet': summary[:200] + '...' if summary else title
                })
    except Exception as e:
        st.error(f"解析 {feed_url} 出错: {e}")
    return articles

# 网页爬取函数（用于无RSS的网站）
def check_website(url, source_name, keywords):
    articles = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for link in soup.find_all('a', href=True):
            title = link.get_text(strip=True)
            href = link['href']
            
            if len(title) < 10:
                continue
            
            # 构建绝对URL
            if href.startswith('/'):
                full_url = urlparse(url).scheme + "://" + urlparse(url).netloc + href
            elif href.startswith('http'):
                full_url = href
            else:
                continue
            
            matched = [kw for kw in keywords if kw.lower() in title.lower()]
            if matched:
                articles.append({
                    'title': title,
                    'url': full_url,
                    'source': source_name,
                    'source_type': '网页',
                    'published': datetime.now(),
                    'matched_keywords': ', '.join(matched),
                    'snippet': title
                })
    except Exception as e:
        st.error(f"检查 {url} 出错: {e}")
    return articles[:20]

# 主抓取函数
@st.cache_data(ttl=21600)
def fetch_all_news(keywords, days_back, show_categories):
    all_articles = []
    sources = load_sources()
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_sources = sum(len(category['urls']) for cat, category in sources.items() if show_categories.get(cat, False))
    current = 0
    
    for category_name, category_data in sources.items():
        if not show_categories.get(category_name, False):
            continue
        
        for source in category_data['urls']:
            status_text.text(f"正在检查: {source['name']}...")
            
            if source['type'] == 'rss' and 'rss' in source:
                articles = parse_rss(source['rss'], source['name'], keywords, days_back)
                all_articles.extend(articles)
            elif source['type'] == 'web' and 'check_url' in source:
                articles = check_website(source['check_url'], source['name'], keywords)
                all_articles.extend(articles)
            
            current += 1
            progress_bar.progress(current / total_sources)
            time.sleep(0.5)
    
    progress_bar.empty()
    status_text.empty()
    
    # 去重
    seen = set()
    unique_articles = []
    for art in all_articles:
        art_id = hashlib.md5((art['url'] + art['title']).encode()).hexdigest()
        if art_id not in seen:
            seen.add(art_id)
            unique_articles.append(art)
    
    unique_articles.sort(key=lambda x: x['published'], reverse=True)
    return unique_articles

# 主界面
def main():
    if 'last_update' not in st.session_state:
        st.session_state.last_update = datetime.now()
    
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        st.info(f"📅 最后更新: {st.session_state.last_update.strftime('%Y-%m-%d %H:%M:%S')}")
    with col3:
        if st.button("🔄 立即更新"):
            st.cache_data.clear()
            st.session_state.last_update = datetime.now()
            st.rerun()
    
    # 获取新闻数据
    with st.spinner("正在抓取最新报道..."):
        articles = fetch_all_news(keywords, days_back, show_categories)
    
    st.subheader(f"📊 共找到 {len(articles)} 篇相关报道")
    
    if articles:
        df = pd.DataFrame(articles)
        df['published'] = pd.to_datetime(df['published'])
        
        # 统计图表
        col1, col2 = st.columns(2)
        with col1:
            source_counts = df['source'].value_counts().head(10)
            st.bar_chart(source_counts)
        with col2:
            df['date'] = df['published'].dt.date
            date_counts = df['date'].value_counts().sort_index()
            st.line_chart(date_counts)
        
        # 按来源分类显示
        for category_name, category_data in load_sources().items():
            if not show_categories.get(category_name, False):
                continue
            cat_articles = [a for a in articles if a['source'] in [s['name'] for s in category_data['urls']]]
            if cat_articles:
                with st.expander(f"{category_data['icon']} {category_name} ({len(cat_articles)}篇)", expanded=False):
                    for art in cat_articles[:10]:  # 每类最多显示10篇
                        st.markdown(f"**[{art['title']}]({art['url']})**  \n"
                                  f"来源：{art['source']} | {art['published'].strftime('%Y-%m-%d %H:%M')}  \n"
                                  f"匹配关键词：`{art['matched_keywords']}`  \n"
                                  f"摘要：{art['snippet']}")
                        st.markdown("---")
        
        # 完整列表（可搜索）
        with st.expander("📋 查看全部报道（可搜索）"):
            st.dataframe(df[['title', 'source', 'published', 'matched_keywords', 'url']])
    else:
        st.warning("暂无相关报道，请调整关键词或稍后再试")

if __name__ == "__main__":
    main()
